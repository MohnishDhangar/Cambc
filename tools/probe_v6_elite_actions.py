#!/usr/bin/env python3
"""Read-only probe of action stream in official v1.0.0 CAMBC replays.

Uses the map serialization boundary verified in prepared-high-elo and checks the
entire input record against the recorded count. Does not claim match outcomes.
"""
import csv, json, struct, re, zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PREP=ROOT/"match-data/v5/prepared-high-elo"
SRC=ROOT/"match-data/v5/high-elo-teams"
MAPDIR=ROOT/"maps"
LENGTHS={0:4,1:8,2:9,3:17,4:0,5:8,6:8,7:0,8:8,9:9,10:8,11:4}
def read(data,map_file, limit=None):
    start=14+Path(map_file).stat().st_size
    expected=struct.unpack_from("<I",data,start)[0]
    p=start+4; n=0; subs={}; kinds={}; dump=[]
    while p<len(data) and (limit is None or n<limit):
        at=p; kind=data[p]; p+=1
        if kind==0:
            sub=data[p];p+=1
            if sub not in LENGTHS:raise ValueError(("sub",n,at,sub,data[at:at+30].hex()))
            p+=LENGTHS[sub];subs[sub]=subs.get(sub,0)+1
        elif kind==3:p+=1
        elif kind==4:
            if data[p]!=1 or data[p+5]!=255:raise ValueError(("draft",n,at,data[at:at+20].hex()))
            p+=6
        elif kind==5:pass
        else:raise ValueError(("kind",n,at,kind,data[at:at+30].hex()))
        kinds[kind]=kinds.get(kind,0)+1
        if len(dump)<16:dump.append({"kind":kind,"bytes":data[at:p].hex()})
        n+=1
    return {"recorded_count":expected,"parsed_count":n,"end_aligned":p==len(data),"actions":subs,"kinds":kinds,"first16":dump,"rest_bytes":len(data)-p}
def main():
    with (PREP/"matches.csv").open() as h:rows=list(csv.DictReader(h))
    split_file=ROOT/"match-data/analysis/v6-elite-research/v6-map-split.csv"
    if not split_file.exists(): raise RuntimeError("Run python3 tools/build_v6_map_split.py first")
    with split_file.open() as h:
        training_ids={r["match_id"] for r in csv.DictReader(h) if r["v6_split"]=="train"}
    seen=set();selected=[]
    for r in rows:
        if r["match_id"] not in training_ids: continue
        if r["map_name"] in {"01islands","01hooks","00lanes","01corridors"}: raise AssertionError("Holdout leakage")
        if r["replay_sha256"] not in seen:
            seen.add(r["replay_sha256"])
            selected.append(r)
    report=[]
    source={}
    for p in SRC.rglob("*.zip"):
        m=re.match(r"[0-9]+-([0-9a-f-]{36})[.]zip$",p.name)
        if m:source[m.group(1)]=p
    for p in SRC.rglob("replay.repl26a"):
        m=re.match(r"[0-9]+-([0-9a-f-]{36})$",p.parent.name)
        if m:source[m.group(1)]=p
    for r in selected:
        try:
            p=source[r["match_id"]]
            if p.suffix==".zip":
                with zipfile.ZipFile(p) as z:raw=z.read("replay.repl26a")
            else:raw=p.read_bytes()
            v=read(raw, MAPDIR/(r["map_name"]+".map26a"))
            v.update(id=r["match_id"],opponent=r["opponent"],side=r["our_side"],map=r["map_name"],valid=v["parsed_count"]==v["recorded_count"] and v["end_aligned"])
        except Exception as e:
            v={"id":r["match_id"],"error":str(e)}
        report.append(v)
    good=[r for r in report if r.get("valid")]
    assert len(report)==161,f"Unexpected training-only replay count {len(report)}"
    print(json.dumps({"total":len(report),"valid":len(good),"invalid_examples":[r for r in report if not r.get("valid")][:5],
                      "examples":good[:3]},indent=2)[:13000])
    out=ROOT/"match-data/analysis/v6-elite-research";out.mkdir(parents=True,exist_ok=True)
    (out/"probe.json").write_text(json.dumps(report,indent=2)+"\n")
    assert len(good)==len(report),f"Only {len(good)}/{len(report)} complete action streams"
if __name__=="__main__":main()
