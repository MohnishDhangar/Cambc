#!/usr/bin/env python3
"""Deterministic two-stage team-composition search; NEVER touch four sealed maps.

Stage 1: 20 candidate three-champion draft cores on six training maps, both sides.
Stage 2: five best plus reference/control on the other 11 training maps.
All bots use one fixed tactical executor and economy macro, banking immediately.
"""
from __future__ import annotations
import concurrent.futures, csv, hashlib, json, math, os, re, subprocess, zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
MANIFEST=ROOT/"match-data/analysis/v6-elite-research/v6-map-split.json"
OUT=ROOT/"match-data/analysis/v6-roster-search"
FALLBACK=("tavi","varg","vendetta","ryth","vesper_vale","marcella",
          "ren","stellar","prism","willow","cassi_and_issac","heart_of_ruin")
ROSTERS={
 "00":("tavi","varg","vendetta"),
 "01":("stellar","prism","tavi"),
 "02":("heart_of_ruin","vesper_vale","tavi"),
 "03":("stellar","prism","vesper_vale"),
 "04":("stellar","prism","varg"),
 "05":("stellar","prism","heart_of_ruin"),
 "06":("stellar","prism","marcella"),
 "07":("stellar","prism","vendetta"),
 "08":("stellar","tavi","vesper_vale"),
 "09":("prism","tavi","vesper_vale"),
 "10":("stellar","tavi","varg"),
 "11":("heart_of_ruin","vesper_vale","prism"),
 "12":("heart_of_ruin","vesper_vale","stellar"),
 "13":("heart_of_ruin","tavi","prism"),
 "14":("heart_of_ruin","varg","stellar"),
 "15":("heart_of_ruin","marcella","tavi"),
 "16":("vesper_vale","marcella","varg"),
 "17":("varg","tavi","marcella"),
 "18":("vesper_vale","varg","tavi"),
 "19":("willow","stellar","prism"),
 "20":("cassi_and_issac","prism","tavi"),
 "21":("vesper_vale","varg","vendetta"),
}

def wilson(w,n,z=1.96):
    if not n:return [0,1]
    p=w/n
    den=1+z*z/n
    h=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/den
    mid=(p+z*z/(2*n))/den
    return [round(mid-h,3),round(mid+h,3)]

def build_variants():
    src=ROOT/"bots/Bot6/src"
    for ident,head in ROSTERS.items():
        bot="Bot6R"+ident
        dest=ROOT/"bots"/bot/"src"
        dest.mkdir(parents=True,exist_ok=True)
        order=list(head)
        for p in FALLBACK:
            if p not in order:order.append(p)
        assert len(order)==len(FALLBACK) and len(set(order))==len(order)
        picks=",".join("C::"+x for x in order[:11])
        for sf in src.iterdir():
            if sf.suffix not in (".cpp",".h"): continue
            code=sf.read_text()
            if sf.name=="bot.cpp":
                assert "#ifndef V6_BANK_THRESHOLD" in code
                code="#define V6_BANK_THRESHOLD 0\n#define V6_MACRO_MODE 1\n"+code
            if sf.name=="draft.cpp":
                anchor="    for (auto choice : order) {"
                assert code.count(anchor)==1
                code=code.replace(anchor,"    if (!objective) order = {"+picks+"};\n"+anchor,1)
            (dest/sf.name).write_text(code)
        yield bot

def score(rows):
    if not rows:return None
    n=len(rows);w=sum(x.get("win",0) for x in rows)
    return {"n":n,"wins":w,"rate":round(w/n,4),"wilson95":wilson(w,n),
            "mean_margin":round(sum(x.get("margin",0) for x in rows)/n,1),
            "A_wins":sum(x.get("win",0) for x in rows if x["side"]=="A"),
            "B_wins":sum(x.get("win",0) for x in rows if x["side"]=="B"),
            "faults":sum(x.get("faults",0) for x in rows),
            "caught_errors":sum(x.get("caught_errors",0) for x in rows),
            "fuel_spill_messages":sum(x.get("fuel_spills",0) for x in rows),
            "failed_matches":sum(bool(x.get("error")) for x in rows)}

def main():
    spec=json.loads(MANIFEST.read_text())
    training=spec["training_map_names"];sealed=set(spec["reserved_map_names"])
    assert len(training)==17 and len(sealed)==4 and not (set(training)&sealed)
    first=training[:6]; second=training[6:]
    OUT.mkdir(parents=True,exist_ok=True)
    env={**os.environ,"CAMBC_NO_UPDATE_CHECK":"1","CAMBC_OFFLINE":"1"}
    variants=list(build_variants())
    for bot in variants:
        r=subprocess.run(["cambc","build",bot,"--release"],cwd=ROOT,env=env,
                         capture_output=True,text=True,timeout=220)
        if r.returncode:raise RuntimeError("Failed to compile "+bot+"\n"+(r.stdout+r.stderr)[-1400:])
    def game(q):
        phase,bot,mp,side=q
        path=OUT/"games"/(bot+"_"+mp+"_"+side)
        path.mkdir(parents=True,exist_ok=True)
        bots=[bot,"Bot4Frozen"] if side=="A" else ["Bot4Frozen",bot]
        cmd=["cambc","run",*bots,"--release","--map",str(ROOT/"maps"/(mp+".map26a")),
             "--out-dir",str(path),"--statistics",str(path/"statistics.json"),"--json"]
        key={"phase":phase,"candidate":bot,"map":mp,"side":side}
        try:
            p=subprocess.run(cmd,cwd=ROOT,env=env,capture_output=True,text=True,timeout=260)
        except subprocess.TimeoutExpired:
            return {**key,"error":"timeout"}
        if p.returncode or not (path/"statistics.json").exists():
            return {**key,"error":(p.stdout+p.stderr)[-700:]}
        j=json.loads((path/"statistics.json").read_text())
        us="team"+side;other="team"+("B" if side=="A" else "A")
        gems=lambda t:sum(int(x["metrics"]["submittedGems"]) for x in j["champions"] if x["team"]==t)
        ours=gems(us);theirs=gems(other)
        logs=[]
        packages=list(path.glob("*.repl26a"))
        if packages:
            with zipfile.ZipFile(packages[0]) as archive:
                candidate="team-"+side.lower()+".stdout"
                logs=archive.read(candidate).replace(b"\0",b"").decode(errors="replace").splitlines()
        else:
            return {**key,"error":"No match replay bundle"}
        return {**key,"win":int(j["match"]["outcome"]==us),"margin":ours-theirs,
            "gems":ours,"enemy_gems":theirs,
            "faults":int(j.get("diagnostics",{}).get("botFaults",{}).get(us,0)),
            "caught_errors":sum("bot error" in s.lower() or "v6 error" in s.lower() for s in logs),
            "fuel_spills":sum("fuel spill at" in s.lower() for s in logs),
            "error":""}
    def play(phase, bots, maps):
        tasks=[(phase,b,m,sd) for b in bots for m in maps for sd in "AB"]
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as p:
            return list(p.map(game,tasks))
    first_games=play("screen",variants,first)
    by={bot:[x for x in first_games if x["candidate"]==bot] for bot in variants}
    ranks=sorted(variants,key=lambda k:(score(by[k])["wins"],score(by[k])["mean_margin"]),reverse=True)
    selected=list(dict.fromkeys(ranks[:5]+["Bot6R00","Bot6R01","Bot6R02"]))
    second_games=play("validation",selected,second)
    rows=first_games+second_games
    cols=["phase","candidate","map","side","win","margin","gems",
          "enemy_gems","faults","caught_errors","fuel_spills","error"]
    with (OUT/"games.csv").open("w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=cols);w.writeheader();w.writerows(rows)
    report={"rules":"all 17 development maps, 4 sealed excluded; both sides; unchanged v4 opponent",
            "client":"CAMBC 3.0.1","first_maps":first,"remaining_maps":second,
            "executor_sha256":hashlib.sha256((ROOT/"bots/Bot6/src/bot.cpp").read_bytes()).hexdigest(),
            "fixed_macro_mode":1,"fixed_bank_threshold":0,
            "selection":"top five by wins then gem margin on first 6 maps; forced 3 controls",
            "screened_candidates":len(variants),"first_stage_games":len(first_games),
            "validated_candidates":selected,"validation_games":len(second_games),
            "results":{key:{"core_draft":ROSTERS[key[-2:]],"screen":score(by[key]),
                            "validation":score([x for x in second_games if x["candidate"]==key]),
                            "combined":score([x for x in rows if x["candidate"]==key]) if key in selected else None}
                       for key in variants}}
    (OUT/"summary.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps({k:v for k,v in report.items() if k!="results"},indent=2),flush=True)
    print(json.dumps({k:report["results"][k] for k in selected},indent=2),flush=True)
    if any(r.get("error") or r.get("faults") or r.get("caught_errors") for r in rows):
        raise SystemExit("Some candidate matches had caught exceptions or engine faults; see report")
if __name__=="__main__":main()
