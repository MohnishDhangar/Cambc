#!/usr/bin/env python3
"""Run Bot6 on TRAINING maps only, both sides, against frozen baselines.

Matches are diagnostic for correct legal play; win rate is not used as the
foundation release gate. Caller must build all referenced bots first.
"""
import argparse, json, os, subprocess, time, zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
MANIFEST=ROOT/"match-data/analysis/v6-elite-research/v6-map-split.json"
def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--client",default="cambc")
    parser.add_argument("--opponents",nargs="+",default=["starter-cpp"])
    parser.add_argument("--maps",nargs="+",default=["00ambush","00contest","01gold-rush"])
    parser.add_argument("--output",default="replays/v6-first-smoke")
    args=parser.parse_args()
    spec=json.loads(MANIFEST.read_text())
    allowed=set(spec["training_map_names"])
    reserved=set(spec["reserved_map_names"])
    if not set(args.maps)<=allowed or set(args.maps)&reserved:
        raise SystemExit("REFUSING: test map intersects sealed holdout or is not a training map")
    out=ROOT/args.output
    out.mkdir(parents=True,exist_ok=True)
    env={**os.environ,"CAMBC_NO_UPDATE_CHECK":"1","CAMBC_OFFLINE":"1"}
    records=[]
    for enemy in args.opponents:
        for name in args.maps:
            for side in ("A","B"):
                label=f"{name}-{enemy}-{side}"
                folder=out/label
                folder.mkdir(exist_ok=True)
                bots=["Bot6",enemy] if side=="A" else [enemy,"Bot6"]
                cmd=[args.client,"run",*bots,"--release","--map",
                     str(ROOT/"maps"/(name+".map26a")),
                     "--out-dir",str(folder),"--statistics",str(folder/"stats.json"),"--json"]
                start=time.monotonic()
                try:
                    p=subprocess.run(cmd,cwd=ROOT,env=env,capture_output=True,text=True,timeout=300)
                    error=None
                except subprocess.TimeoutExpired:
                    p=None;error="timed out after 300 seconds"
                log=(p.stdout+"\n"+p.stderr) if p else str(error)
                (folder/"runner.log").write_text(log)
                record={"map":name,"opponent":enemy,"side":side,"seconds":round(time.monotonic()-start,2),
                        "returncode":p.returncode if p else None}
                if p is None or p.returncode or not (folder/"stats.json").exists():
                    record["error"]=log[-1500:]
                else:
                    data=json.loads((folder/"stats.json").read_text())
                    us="team"+side
                    theirs="team"+("B" if side=="A" else "A")
                    record["rounds"]=data["match"]["roundsStarted"]
                    record["winner"]=data["match"].get("outcome")
                    record["win"]=data["match"]["outcome"]==us
                    record["gem_score"]=sum(int(x["metrics"]["submittedGems"]) for x in data["champions"] if x["team"]==us)
                    record["enemy_gems"]=sum(int(x["metrics"]["submittedGems"]) for x in data["champions"] if x["team"]==theirs)
                    record["faults"]=data.get("diagnostics",{}).get("botFaults",{}).get(us,0)
                    packages=list(folder.glob("*.repl26a"))
                    if packages:
                        with zipfile.ZipFile(packages[0]) as z:
                            stream=z.read("team-"+side.lower()+".stdout").replace(b"\0",b"").decode(errors="replace")
                        record["errors"]=[x[:150] for x in stream.splitlines()
                                          if "v6 error" in x.lower() or "bot error" in x.lower()
                                          or "fuel spill at" in x.lower()]
                        record["logs"]=len(stream.splitlines())
                        (folder/"bot6.stdout").write_text(stream)
                    else:record["errors"]=["No replay log found"]
                records.append(record)
                (out/"summary.json").write_text(json.dumps(records,indent=2)+"\n")
                print(json.dumps(record),flush=True)
    errors=[x for x in records if x.get("error") or x.get("faults") or x.get("errors")]
    print(f"completed={len(records)-len(errors)}/{len(records)} wins={sum(x.get('win',False) for x in records)}",flush=True)
    if errors:raise SystemExit(1)
if __name__=="__main__":main()
