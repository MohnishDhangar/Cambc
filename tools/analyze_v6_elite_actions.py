#!/usr/bin/env python3
"""Analyze recorded inputs for distinct elite-match replays, without replaying gameplay.

This counts *attempted* actions attributed to Team A/B by the alternating
champion turn schedule; never infers successful actions, winners, scores, deaths,
or unobserved strategy from this action stream.
"""
from __future__ import annotations
import csv, json, re, struct, statistics, zipfile
from collections import Counter, defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PREP=ROOT/"match-data/v5/prepared-high-elo"
SOURCE=ROOT/"match-data/v5/high-elo-teams"
OUT=ROOT/"match-data/analysis/v6-elite-research"
LEN={0:4,1:8,2:9,3:17,4:0,5:8,6:8,7:0,8:8,9:9,10:8,11:4}
ACTIONS=["priority","move","attack","cast","recall","tribute","buy_item",
         "cancel_channel","buy_consumable","use_consumable","ward","sell"]
def indexed_sources():
    paths={}
    for p in SOURCE.rglob("*.zip"):
        m=re.match(r"[0-9]+-([0-9a-f-]{36})[.]zip$",p.name)
        if m:paths[m.group(1)]=p
    for p in SOURCE.rglob("replay.repl26a"):
        m=re.match(r"[0-9]+-([0-9a-f-]{36})$",p.parent.name)
        if m:paths[m.group(1)]=p
    return paths

def load_game(p:Path):
    if p.suffix!=".zip":
        return p.read_bytes(),(p.parent/("team-"+("a" if "/position-A/" in str(p) else "b")+".stdout")).read_bytes()
    with zipfile.ZipFile(p) as z:
        raw=z.read("replay.repl26a")
        s=[n for n in z.namelist() if n.endswith(".stdout")]
        out=z.read(s[0]) if len(s)==1 else b""
    return raw,out

def decoded_records(raw, map_bytes):
    p=14+map_bytes
    expected=struct.unpack_from("<I",raw,p)[0];p+=4
    for i in range(expected):
        start=p
        kind=raw[p];p+=1
        sub=None
        if kind==0:
            sub=raw[p];p+=1
            if sub not in LEN:raise ValueError(f"Unexpected action {sub} at record {i}")
            payload=raw[p:p+LEN[sub]];p+=LEN[sub]
        elif kind==3:payload=raw[p:p+1];p+=1
        elif kind==4:
            payload=raw[p:p+6];p+=6
            if payload[0]!=1 or payload[5]!=255:raise ValueError("Invalid draft record")
        elif kind==5:payload=b""
        else:raise ValueError(f"Unexpected record kind {kind}")
        yield kind,sub,payload
    if p!=len(raw):raise ValueError(f"Input stream ended at {p}, expected {len(raw)}")

def analyze_game(raw, mapbytes,stdout):
    stats={team:Counter() for team in ("A","B")}
    early={team:Counter() for team in ("A","B")}
    draft={team:[] for team in ("A","B")}
    events=list(decoded_records(raw,mapbytes))
    n_draft=sum(x[0]==4 for x in events)
    if n_draft not in (6,8,10):raise ValueError(f"Unexpected draft count {n_draft}")
    n=n_draft//2
    picks=0;draft_end=False;turns=0
    active=Counter()
    for kind,sub,payload in events:
        if kind==4:
            if draft_end:raise ValueError("Draft decision after draft ended")
            t="A" if picks%2==0 else "B"
            draft[t].append(payload[1])
            picks+=1
            continue
        if not draft_end:
            if kind!=3:raise ValueError("Non-draft input before draft complete")
            if picks==n_draft:draft_end=True
            continue
        round_i=(turns//(2*n))+1
        slot=turns%(2*n)
        # Team initiative alternates across rounds; within each round
        # champions of the two teams alternate.
        side="A" if (slot%2 == ((round_i-1)%2)) else "B"
        st=stats[side]
        op=early[side] if round_i<=200 else None
        if kind==0:
            name=ACTIONS[sub]
            st[name]+=1
            active[name]+=1
            if op is not None:op[name]+=1
            if sub==2:
                target={1:"champion",2:"camp",3:"lock"}.get(payload[0],"other")
                st["attack_"+target]+=1
                if op is not None:op["attack_"+target]+=1
            if sub==3:
                target_kind=payload[4]
                st["cast_champion_target" if target_kind==1 else "cast_other_target"]+=1
            if sub==9:st["consumable_type_"+str(payload[0])]+=1
        elif kind==3:
            st["turns"]+=1
            if round_i<=200:early[side]["turns"]+=1
            if not active:st["turns_no_commands"]+=1
            if active.get("move"):st["turns_with_move"]+=1
            if active.get("attack") or active.get("cast"):st["turns_with_combat_command"]+=1
            if payload and payload[0]==1:st["turns_fuel_exhausted"]+=1
            if payload and payload[0] not in (0,1):st["other_turn_status_"+str(payload[0])]+=1
            active.clear()
            turns+=1
        elif kind==5:
            st["record_kind_5"]+=1
        else:raise ValueError(f"Kind {kind} after draft")
    if any(len(draft[t])!=n for t in ("A","B")):raise ValueError("Draft team count mismatch")
    if active:raise ValueError("Unclosed champion turn")
    return {"draft":draft,"champions_per_team":n,"turns":turns,
            "team":{x:dict(stats[x]) for x in ("A","B")},
            "first200":{x:dict(early[x]) for x in ("A","B")},
            "stdout_v4_marker":b"Bot1 strategy v4" in stdout,
            "stdout_v5_marker":b"Bot1 strategy v5" in stdout,
            "bot_error_messages":len(re.findall(rb"bot error",stdout,re.I)),
            "fuel_spill_messages":len(re.findall(rb"fuel spill at",stdout,re.I))}

def mean(values):
    return round(statistics.mean(values),3) if values else None
def main():
    paths=indexed_sources()
    with (PREP/"matches.csv").open() as fh:allrows=list(csv.DictReader(fh))
    unique={}
    for row in allrows:
        unique.setdefault(row["replay_sha256"],row)
    if len(unique)!=179 or len(allrows)!=500:raise ValueError("Unexpected collection inventory")
    results=[];fail=[]
    for sha,row in unique.items():
        try:
            raw,stdout=load_game(paths[row["match_id"]])
            s=analyze_game(raw,(ROOT/"maps"/(row["map_name"]+".map26a")).stat().st_size,stdout)
            s.update(match_id=row["match_id"],replay_sha256=sha,map=row["map_name"],
                     opponent=row["opponent"],our_side=row["our_side"],
                     opponent_elo=int(row["opponent_elo"]),
                     match_group=row["match_group_id"],folder_result=row["folder_outcome"])
            results.append(s)
        except Exception as exc:fail.append({"match_id":row["match_id"],"error":str(exc)})
    OUT.mkdir(parents=True,exist_ok=True)
    if fail:
        (OUT/"errors.json").write_text(json.dumps(fail,indent=2)+"\n")
        raise ValueError(f"Action-stream analysis failed for {len(fail)} replays: {fail[:3]}")
    (OUT/"attempted-actions-per-match.jsonl").write_text(
        "".join(json.dumps(r,separators=(",",":"))+"\n" for r in results))
    fields=["match_id","replay_sha256","opponent","our_side","map","champions_per_team",
            "our_draft","opponent_draft","our_turns","their_turns","our_movement",
            "their_movement","our_attacks_on_champions","their_attacks_on_champions",
            "our_attacks_on_camps","their_attacks_on_camps","our_spell_casts",
            "their_spell_casts","our_recall_attempts","their_recall_attempts",
            "our_tribute_attempts","their_tribute_attempts","our_buy_attempts",
            "their_buy_attempts","our_fuel_exhaustion_turns","their_fuel_exhaustion_turns"]
    with (OUT/"attempted-actions.csv").open("w",newline="") as fd:
        writer=csv.DictWriter(fd,fieldnames=fields);writer.writeheader()
        for r in results:
            us=r["team"][r["our_side"]]
            other=r["team"]["B" if r["our_side"]=="A" else "A"]
            u=r["our_side"];v="B" if u=="A" else "A"
            d={"match_id":r["match_id"],"replay_sha256":r["replay_sha256"],
               "opponent":r["opponent"],"our_side":u,"map":r["map"],
               "champions_per_team":r["champions_per_team"],
               "our_draft":"|".join(map(str,r["draft"][u])),
               "opponent_draft":"|".join(map(str,r["draft"][v])),
               "our_turns":us.get("turns",0),"their_turns":other.get("turns",0)}
            for field,name in [("movement","move"),("attacks_on_champions","attack_champion"),
                ("attacks_on_camps","attack_camp"),("spell_casts","cast"),("recall_attempts","recall"),
                ("tribute_attempts","tribute"),("buy_attempts","buy_item"),("fuel_exhaustion_turns","turns_fuel_exhausted")]:
                d["our_"+field]=us.get(name,0);d["their_"+field]=other.get(name,0)
            writer.writerow(d)
    summary={"n_unique":len(results),"n_source_rows":len(allrows),"n_invalid":len(fail),
             "stdout_v4_markers":sum(r["stdout_v4_marker"] for r in results),
             "stdout_v5_markers":sum(r["stdout_v5_marker"] for r in results),
             "by_opponent":{},"by_map":{},"all":{}}
    mapgroups=defaultdict(list);teamgroups=defaultdict(list)
    for r in results:
        mapgroups[r["map"]].append(r);teamgroups[r["opponent"]].append(r)
    def group_metrics(group):
        arr=defaultdict(list);drafts=Counter();oppdrafts=Counter()
        for r in group:
            ours=r["team"][r["our_side"]]
            theirs=r["team"]["A" if r["our_side"]=="B" else "B"]
            for key in ["move","attack","attack_champion","attack_camp","attack_lock",
                        "cast","buy_item","recall","tribute","ward","turns",
                        "turns_no_commands","turns_with_combat_command","turns_fuel_exhausted"]:
                arr["ours_"+key].append(ours.get(key,0))
                arr["opponent_"+key].append(theirs.get(key,0))
            drafts.update(r["draft"][r["our_side"]])
            oppdrafts.update(r["draft"]["A" if r["our_side"]=="B" else "B"])
        return {"unique_replays":len(group),"our_side_A":sum(r["our_side"]=="A" for r in group),
                "our_side_B":sum(r["our_side"]=="B" for r in group),
                "mean_attempted_counts_per_match":{k:mean(v) for k,v in arr.items()},
                "our_draft_picks":dict(sorted(drafts.items())),
                "opponent_draft_picks":dict(sorted(oppdrafts.items())),
                "our_error_logs":sum(r["bot_error_messages"] for r in group),
                "our_fuel_spill_messages":sum(r["fuel_spill_messages"] for r in group)}
    summary["all"]=group_metrics(results)
    summary["by_opponent"]={k:group_metrics(v) for k,v in sorted(teamgroups.items())}
    summary["by_map"]={k:group_metrics(v) for k,v in sorted(mapgroups.items())}
    (OUT/"attempted-actions-summary.json").write_text(json.dumps(summary,indent=2)+"\n")
    print(json.dumps({"n_unique":len(results),"n_errors":len(fail),"all":summary["all"],
                      "by_opponent":{k:{kk:vv for kk,vv in x.items() if kk not in ("mean_attempted_counts_per_match",)}
                                     for k,x in summary["by_opponent"].items()}},indent=2))
if __name__=="__main__":main()
