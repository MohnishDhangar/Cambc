#!/usr/bin/env python3
"""Compare current pinned Bot1 executor source with archived frozen-v4 ZIP.

This is a *read-only* comparison: Bot1 and Bot4Frozen are never edited.
The reference source code in Bot1 may differ from the archived release.
"""
import csv, json, os, subprocess, concurrent.futures, zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"match-data/analysis/v6-executor-audit"
SPLIT=ROOT/"match-data/analysis/v6-elite-research/v6-map-split.json"
def main():
    allowed=json.loads(SPLIT.read_text())
    maps=allowed["training_map_names"]
    if len(maps)!=17 or set(maps)&set(allowed["reserved_map_names"]):raise ValueError("Holdout contamination")
    OUT.mkdir(parents=True,exist_ok=True)
    env={**os.environ,"CAMBC_NO_UPDATE_CHECK":"1","CAMBC_OFFLINE":"1"}
    for name in ["Bot1","Bot4Frozen"]:
        p=subprocess.run(["cambc","build",name,"--release"],cwd=ROOT,env=env,
                         capture_output=True,text=True,timeout=220)
        if p.returncode:raise RuntimeError(name+":"+p.stderr[-1000:])
    def game(q):
        mapname,side=q
        folder=OUT/"games"/f"{mapname}-{side}";folder.mkdir(parents=True,exist_ok=True)
        bots=["Bot1","Bot4Frozen"] if side=="A" else ["Bot4Frozen","Bot1"]
        p=subprocess.run(["cambc","run",*bots,"--release","--map",str(ROOT/"maps"/(mapname+".map26a")),
             "--out-dir",str(folder),"--statistics",str(folder/"statistics.json"),"--json"],
             cwd=ROOT,env=env,capture_output=True,text=True,timeout=250)
        if p.returncode:return {"map":mapname,"side":side,"error":p.stderr[-700:]}
        j=json.loads((folder/"statistics.json").read_text())
        us="team"+side
        enemy="team"+("B" if side=="A" else "A")
        score=lambda sd:sum(int(x["metrics"]["submittedGems"]) for x in j["champions"] if x["team"]==sd)
        own=score(us);other=score(enemy)
        logs=[]
        packages=list(folder.glob("*.repl26a"))
        if packages:
            with zipfile.ZipFile(packages[0]) as z:
                logs=z.read("team-"+side.lower()+".stdout").replace(b"\0",b"").decode(errors="replace").splitlines()
        err=[x[:140] for x in logs if "bot error" in x.lower() or "fuel spill at" in x.lower()]
        return {"map":mapname,"side":side,"win":int(j["match"]["outcome"]==us),
                "gems":own,"enemy_gems":other,"margin":own-other,
                "faults":j.get("diagnostics",{}).get("botFaults",{}).get(us,0),
                "error_logs":err}
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        games=list(pool.map(game,[(mp,side) for mp in maps for side in "AB"]))
    clean=all(not x.get("error") and not x.get("faults") and not x.get("error_logs") for x in games)
    info={"n":len(games),"wins":sum(x.get("win",0) for x in games),
          "avg_gem_margin":sum(x.get("margin",0) for x in games)/len(games),
          "clean":clean,"results":games}
    (OUT/"summary.json").write_text(json.dumps(info,indent=2)+"\n")
    print(json.dumps({k:v for k,v in info.items() if k!="results"},indent=2))
    if not clean:
        print(json.dumps([x for x in games if x.get("error") or x.get("faults") or x.get("error_logs")][:12],indent=2))
if __name__=="__main__":main()
