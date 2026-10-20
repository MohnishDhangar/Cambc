#!/usr/bin/env python3
"""Audit reported Bot1-v4 replay outcome mismatches without editing source replays.

Uses the existing verified v4-study/metrics.json. Output labels are grounded in
the engine's outcome field, not a naïve comparison of tributed gem totals.
No assumption about Team A identity is made without checking stdout.
"""
import collections
import csv
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPORT = HERE / "v4-study" / "metrics.json"
DEST = HERE / "v4-study" / "reconciliation"
DEST.mkdir(parents=True, exist_ok=True)
data = json.loads(REPORT.read_text())
games = data["games"]

# Engine outcomes must be mapped via games with a non-tied score and completed
# result; print mapping rather than assuming enum 1/2 or 0/1.
outcome_cross = collections.Counter()
outcome_ties = collections.Counter()
by_category = collections.Counter()
for g in games:
    scores=g["score"]
    key=(str(g.get("outcome")), "A" if scores[0]>scores[1] else "B" if scores[1]>scores[0] else "tie")
    outcome_cross[key]+=1
    if scores[0]==scores[1]:
        outcome_ties[(g["category"],str(g.get("outcome")))] +=1
    label=g["category"].split("/")[-1]
    naïve = "wins" if scores[0]>scores[1] else "losses"
    by_category[(g["category"], "agreement" if label==naïve else "mismatch", "tie" if scores[0]==scores[1] else "not_tie")]+=1

print("TOTAL",len(games))
print("OUTCOME_CROSS_TAB",dict(sorted(((str(k),v) for k,v in outcome_cross.items()))))
print("TIES",dict(sorted(((str(k),v) for k,v in outcome_ties.items()))))
print("CATEGORY_VS_NAIVE",dict(sorted(((str(k),v) for k,v in by_category.items()))))

# Determine semantic outcome value only when the unique result matches
# every decisive score result. Unresolvable games remain flagged.
outcome_winner = {}
for outcome in {str(g.get("outcome")) for g in games}:
    leaders={("A" if g["score"][0]>g["score"][1] else "B")
             for g in games if str(g.get("outcome"))==outcome and g["score"][0]!=g["score"][1]}
    if len(leaders)==1:
        outcome_winner[outcome] = next(iter(leaders))
print("ENGINE_OUTCOME_INFERRED_MAPPING",outcome_winner)
print("ENGINE_OUTCOME_MAP_IS_COMPLETE",len(outcome_winner)>=2)
rows=[]
counts=collections.Counter()
for g in games:
    folder=g["category"].split("/")[-1]
    scores=g["score"]
    engine=outcome_winner.get(str(g.get("outcome")))
    score_winner = "A" if scores[0]>scores[1] else "B" if scores[1]>scores[0] else "tie"
    # Engine outcome wins for ties too if mapping verified. Team A
    # identity is pending per-file stdout verification.
    result = "wins" if engine=="A" else "losses" if engine=="B" else "unknown"
    status=("unresolved" if result=="unknown" else
            "agreement" if folder==result else
            "wrong_folder")
    counts[(g["category"],status)]+=1
    rows.append(dict(
       path=g["path"],sha256=g["sha256"],category=g["category"],opponent_group=g["group"],
       folder_label=folder,engine_outcome=g.get("outcome"),score_A=scores[0],score_B=scores[1],
       score_leader=score_winner,inferred_engine_winner=engine or "",
       corrected_result_assuming_team_A_is_Bot1=result,status=status,
       map_hash=g["mapHash"],round=g["round"]
    ))
csv_path=DEST/"manifest-provisional.csv"
with csv_path.open("w",newline="") as f:
    writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
summary=dict(total=len(rows),outcomesByScore=[dict(outcome=x[0][0],scoreLeader=x[0][1],games=x[1]) for x in sorted(outcome_cross.items())],
              resolution=dict(outcome_winner=outcome_winner,classificationCounts={str(k):v for k,v in sorted(counts.items())}),
              mismatches=[r for r in rows if r["status"]!="agreement"])
(DEST/"summary-provisional.json").write_text(json.dumps(summary,indent=2)+"\n")
print("AFTER_ENGINE_OUTCOME",dict(sorted(((str(k),v) for k,v in counts.items()))))
print("CORRECTIONS_NEEDED",sum(r["status"]=="wrong_folder" for r in rows))
print("UNRESOLVED",sum(r["status"]=="unresolved" for r in rows))
print("MISMATCH_SAMPLE",json.dumps(summary["mismatches"][:8],indent=1))
print("OUTPUT",csv_path)
