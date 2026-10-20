#!/usr/bin/env python3
"""Screen Bot6 independent draft compositions against frozen V4 on TRAINING maps.

Each Bot6D{0..6} is the same Bot6 source except for ordinary-map draft priority. Out-of-fold heldout maps are rejected *before* build.
Eight training maps, both sides per variant; results guide further training-map screening.
"""
import argparse, concurrent.futures, csv, hashlib, json, math, os, shutil, subprocess
from collections import defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SPLIT=ROOT/"match-data/analysis/v6-elite-research/v6-map-split.json"
MODES={"0":"v4-draft","1":"vesper-varg-tavi","2":"heart-varg-tavi",
       "3":"heart-vesper-tavi","4":"marcella-varg-tavi",
       "5":"stellar-prism-tavi","6":"vesper-varg-vendetta"}
ORDERS={
 "1":"vesper_vale,varg,tavi,vendetta,ryth,marcella,ren,stellar,prism,willow,cassi_and_issac",
 "2":"heart_of_ruin,varg,tavi,vesper_vale,vendetta,ryth,marcella,ren,stellar,prism,willow",
 "3":"heart_of_ruin,vesper_vale,tavi,varg,vendetta,ryth,marcella,ren,stellar,prism,willow",
 "4":"marcella,varg,tavi,vesper_vale,vendetta,ryth,ren,stellar,prism,willow,cassi_and_issac",
 "5":"stellar,prism,tavi,varg,vesper_vale,vendetta,ryth,marcella,ren,willow,cassi_and_issac",
 "6":"vesper_vale,varg,vendetta,tavi,ryth,marcella,ren,stellar,prism,willow,cassi_and_issac",
}

def wilson(w,n,z=1.96):
    if not n:return (0,1)
    p=w/n
    a=1+z*z/n
    half=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/a
    mid=(p+z*z/(2*n))/a
    return [round(max(0.,mid-half),4),round(min(1.,mid+half),4)]

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--client",default="cambc")
    ap.add_argument("--output",default="match-data/analysis/v6-draft-search")
    ap.add_argument("--workers",type=int,default=3)
    args=ap.parse_args()
    manifest=json.loads(SPLIT.read_text())
    training=manifest["training_map_names"][:8]
    assert len(training)==8 and not (set(training)&set(manifest["reserved_map_names"]))
    out=ROOT/args.output
    out.mkdir(parents=True,exist_ok=True)
    source=ROOT/"bots/Bot6/src"
    variants={}
    for index,label in MODES.items():
        name="Bot6D"+index
        target=ROOT/"bots"/name/"src"
        target.mkdir(parents=True,exist_ok=True)
        for source_file in source.glob("*"):
            if source_file.is_file() and source_file.suffix in (".cpp",".h"):
                dest=target/source_file.name
                s=source_file.read_text()
                if source_file.name=="draft.cpp" and index!="0":
                    anchor="    for (auto choice : order) {"
                    assert s.count(anchor)==1
                    picks=["C::"+n for n in ORDERS[index].split(",")]
                    assert len(picks)==11 and len(set(picks))==11
                    # Preserve v4 siege draft on maps identified as objective-only.
                    s=s.replace(anchor,"    if (!objective) order = {" + ", ".join(picks) + "};\n" + anchor,1)
                dest.write_text(s)
        variants[name]=label
    env={**os.environ,"CAMBC_NO_UPDATE_CHECK":"1","CAMBC_OFFLINE":"1"}
    for bot in variants:
        p=subprocess.run([args.client,"build",bot,"--release"],cwd=ROOT,env=env,
                         capture_output=True,text=True,timeout=250)
        if p.returncode:raise RuntimeError(f"Build failed {bot}: {(p.stdout+p.stderr)[-1800:]}")
    results=[]
    jobs=[(bot,mp,side) for bot in variants for mp in training for side in "AB"]
    def game(q):
        name,mapname,side=q
        folder=out/"games"/(name+"_"+mapname+"_"+side)
        folder.mkdir(parents=True,exist_ok=True)
        bots=[name,"Bot4Frozen"] if side=="A" else ["Bot4Frozen",name]
        cmd=[args.client,"run",*bots,"--release","--map",str(ROOT/"maps"/(mapname+".map26a")),
             "--out-dir",str(folder),"--statistics",str(folder/"statistics.json"),"--json"]
        try:
            r=subprocess.run(cmd,cwd=ROOT,env=env,capture_output=True,text=True,timeout=300)
        except subprocess.TimeoutExpired:
            return {"mode":name,"map":mapname,"side":side,"error":"timeout"}
        if r.returncode or not (folder/"statistics.json").exists():
            return {"mode":name,"map":mapname,"side":side,"error":(r.stdout+r.stderr)[-500:]}
        s=json.loads((folder/"statistics.json").read_text())
        us="team"+side
        them="team"+("A" if side=="B" else "B")
        own=sum(int(x["metrics"]["submittedGems"]) for x in s["champions"] if x["team"]==us)
        enemy=sum(int(x["metrics"]["submittedGems"]) for x in s["champions"] if x["team"]==them)
        faults=s.get("diagnostics",{}).get("botFaults",{}).get(us,0)
        return {"mode":name,"map":mapname,"side":side,"win":int(s["match"]["outcome"]==us),
                "gems":own,"enemy_gems":enemy,"margin":own-enemy,"rounds":s["match"]["roundsStarted"],
                "faults":faults,"error":""}
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        for result in pool.map(game,jobs):
            results.append(result)
            if result.get("error") or result.get("faults"):
                print("ISSUE",json.dumps(result),flush=True)
    with (out/"games.csv").open("w",newline="") as fd:
        cols=["mode","map","side","win","gems","enemy_gems","margin","rounds","faults","error"]
        writer=csv.DictWriter(fd,fieldnames=cols)
        writer.writeheader()
        writer.writerows(results)
    report={"engine_client":"cambc 3.0.1 from pinned CI environment",
            "map_split":"first eight alphabetic training maps; four sealed maps never used",
            "frozen_opponent":"Bot4Frozen from frozen v4 archive",
            "candidate_source_sha256":hashlib.sha256((source/"bot.cpp").read_bytes()).hexdigest(),
            "draft_source_sha256":hashlib.sha256((source/"draft.cpp").read_bytes()).hexdigest(),
            "games":len(results),"modes":{}, "no_fatal_errors":all(not r.get("error") and not r.get("faults") for r in results)}
    for name,label in variants.items():
        games=[r for r in results if r["mode"]==name]
        wins=sum(r.get("win",0) for r in games)
        gm=[r["margin"] for r in games if "margin" in r]
        side={}
        for sd in "AB":
            subset=[r for r in games if r["side"]==sd]
            side[sd]={"wins":sum(r.get("win",0) for r in subset),"games":len(subset)}
        report["modes"][name]={"label":label,"wins":wins,"games":len(games),
                     "win_fraction":round(wins/len(games),4),
                     "wilson95":wilson(wins,len(games)),
                     "avg_gem_margin":round(sum(gm)/len(gm),2) if gm else None,
                     "side":side,
                     "faults":sum(r.get("faults",0) for r in games),
                     "errors":sum(bool(r.get("error")) for r in games)}
    (out/"summary.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report,indent=2),flush=True)
    if not report["no_fatal_errors"]:raise SystemExit("At least one game has an engine fault or harness error")
if __name__=="__main__":main()
