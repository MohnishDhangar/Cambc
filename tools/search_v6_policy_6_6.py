#!/usr/bin/env python3
"""Two-stage v6.6 policy sweep; the four sealed maps are never loaded.

Source and draft are identical in each candidate; only the macro mode and
banking threshold change. Pairs use the same map/opponent on opposite sides.
The last nine development maps are not used to choose top performers.
"""
import concurrent.futures,csv,hashlib,json,math,os,subprocess,zipfile
from collections import defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/"bots/Bot6/src"
OUT=ROOT/"match-data/analysis/v6.6-policy-search"
SPLIT=ROOT/"match-data/analysis/v6-elite-research/v6-map-split.json"
VARIANTS=[(m,b) for m in (0,1,2,3,4,5) for b in (0,8)]
HASH_V4="b296e83d43e8b16709e655ee4470a526e9e84160ee02fbad0e8c483661e1a062"
def wilson(w,n):
    if not n:return [0,1]
    z=1.96;p=w/n;d=1+z*z/n
    center=(p+z*z/(2*n))/d
    half=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/d
    return [round(center-half,3),round(center+half,3)]
def main():
    split=json.loads(SPLIT.read_text())
    maps=split["training_map_names"]
    assert len(maps)==17
    assert not set(maps)&set(split["reserved_map_names"])
    assert split["reserved_map_names"]==["00lanes","01corridors","01hooks","01islands"]
    training,validation=maps[:8],maps[8:]
    baseline=ROOT/"bots/Bot1/Bot1-v4.zip"
    assert hashlib.sha256(baseline.read_bytes()).hexdigest()==HASH_V4
    with zipfile.ZipFile(baseline) as z:
        for src in z.namelist():
            if src.endswith((".cpp",".h")):
                dst=ROOT/"bots/Bot4Frozen/src"/Path(src).name
                dst.parent.mkdir(parents=True,exist_ok=True)
                dst.write_bytes(z.read(src))
    env={**os.environ,"CAMBC_NO_UPDATE_CHECK":"1","CAMBC_OFFLINE":"1"}
    def build(bot):
        r=subprocess.run(["cambc","build",bot,"--release"],cwd=ROOT,env=env,capture_output=True,text=True,timeout=260)
        if r.returncode:raise RuntimeError(f"Build failure in {bot}: {(r.stdout+r.stderr)[-1000:]}")
    build("Bot4Frozen")
    candidates=[]
    base=(SOURCE/"bot.cpp").read_text()
    config="#define V6_MACRO_MODE 1\n#define V6_BANK_THRESHOLD 0\n"
    assert base.startswith(config),"Unexpected candidate source; pin controls before experiment"
    for mode,bank in VARIANTS:
        bot=f"Bot6P{mode}B{bank}"
        destination=ROOT/"bots"/bot/"src"
        destination.mkdir(parents=True,exist_ok=True)
        for src in SOURCE.iterdir():
            if src.suffix not in (".cpp",".h"):continue
            contents=src.read_text()
            if src.name=="bot.cpp":
                contents=contents.replace(config,
                    f"#define V6_MACRO_MODE {mode}\n#define V6_BANK_THRESHOLD {bank}\n",1)
            (destination/src.name).write_text(contents)
        build(bot)
        candidates.append(bot)
    def run(bot,mp,side,stage):
        folder=OUT/"replays"/(f"{bot}-{mp}-{side}")
        folder.mkdir(parents=True,exist_ok=True)
        team="team"+side
        opponent="team"+("B" if side=="A" else "A")
        bots=[bot,"Bot4Frozen"] if side=="A" else ["Bot4Frozen",bot]
        cmd=["cambc","run",*bots,"--release","--map",str(ROOT/"maps"/(mp+".map26a")),
             "--out-dir",str(folder),"--statistics",str(folder/"statistics.json"),"--json"]
        try:r=subprocess.run(cmd,cwd=ROOT,env=env,capture_output=True,text=True,timeout=300)
        except subprocess.TimeoutExpired:return {"bot":bot,"map":mp,"side":side,"stage":stage,"error":"timeout"}
        row={"bot":bot,"map":mp,"side":side,"stage":stage,"error":""}
        if r.returncode or not (folder/"statistics.json").is_file():
            row["error"]=(r.stdout+r.stderr)[-500:]
            return row
        j=json.loads((folder/"statistics.json").read_text())
        row.update(win=int(j["match"]["outcome"]==team),
             gems=sum(int(x["metrics"]["submittedGems"]) for x in j["champions"] if x["team"]==team),
             enemy_gems=sum(int(x["metrics"]["submittedGems"]) for x in j["champions"] if x["team"]==opponent),
             faults=j.get("diagnostics",{}).get("botFaults",{}).get(team,0))
        row["margin"]=row["gems"]-row["enemy_gems"]
        bundles=list(folder.glob("*.repl26a"))
        if not bundles:
            row["error"]="missing replay";return row
        with zipfile.ZipFile(bundles[0]) as z:
            lines=z.read("team-"+side.lower()+".stdout").replace(b"\0",b"").decode(errors="replace").splitlines()
        row["caught_errors"]=sum("bot error" in line.lower() or "v6 error" in line.lower() for line in lines)
        row["fuel_spills"]=sum("fuel spill at" in line.lower() for line in lines)
        return row
    OUT.mkdir(parents=True,exist_ok=True)
    def batch(bots,maps,stage):
        jobs=[(bot,mp,side,stage) for bot in bots for mp in maps for side in "AB"]
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
            return list(pool.map(lambda args:run(*args),jobs))
    screen=batch(candidates,training,"selection")
    def stats(rows):
        if not rows:return {}
        return {"games":len(rows),"wins":sum(x.get("win",0) for x in rows),
            "mean_margin":round(sum(x.get("margin",0) for x in rows)/len(rows),2),
            "faults":sum(x.get("faults",0) for x in rows),
            "errors":sum(x.get("caught_errors",0) or bool(x.get("error")) for x in rows),
            "fuel_spills":sum(x.get("fuel_spills",0) for x in rows),
            "A_wins":sum(x.get("win",0) for x in rows if x["side"]=="A"),
            "B_wins":sum(x.get("win",0) for x in rows if x["side"]=="B"),
            "wilson95":wilson(sum(x.get("win",0) for x in rows),len(rows))}
    grouped=defaultdict(list)
    for x in screen:grouped[x["bot"]].append(x)
    ranking=sorted(candidates,key=lambda c:(
        -int(stats(grouped[c])["errors"]==0 and stats(grouped[c])["faults"]==0),
        -stats(grouped[c])["wins"],-stats(grouped[c])["mean_margin"],c))
    selected=ranking[:4]
    validation_rows=batch(selected,validation,"validation")
    data=screen+validation_rows
    with (OUT/"games.csv").open("w",newline="") as f:
        keys=["bot","map","side","stage","win","gems","enemy_gems","margin","faults","caught_errors","fuel_spills","error"]
        wr=csv.DictWriter(f,fieldnames=keys);wr.writeheader();wr.writerows(data)
    result={"engine":"CAMBC 3.0.1","source_sha256":hashlib.sha256(base.encode()).hexdigest(),
        "draft_sha256":hashlib.sha256((SOURCE/"draft.cpp").read_bytes()).hexdigest(),
        "selection_maps":training,"validation_maps":validation,
        "sealed_maps_never_used":split["reserved_map_names"],
        "modes":{"0":"v4 utility","1":"economy","2":"tempo","3":"contest","4":"objective","5":"adaptive"},
        "bank_thresholds":[0,8],"ranked_after_selection":ranking,
        "validated":selected,"screened":len(screen),"validation_games":len(validation_rows),
        "results":{}}
    for c in candidates:
        a=[x for x in screen if x["bot"]==c]
        b=[x for x in validation_rows if x["bot"]==c]
        result["results"][c]={"selection":stats(a),"validation":stats(b) if b else None,
                              "combined":stats(a+b) if b else None}
    (OUT/"summary.json").write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps({"ranked":ranking,"validated":selected,
        "results":{c:result["results"][c] for c in selected}},indent=2),flush=True)
    if any(x.get("faults") or x.get("caught_errors") or x.get("error") for x in data):
        raise SystemExit("At least one game failed integrity checks")

if __name__=="__main__":main()
