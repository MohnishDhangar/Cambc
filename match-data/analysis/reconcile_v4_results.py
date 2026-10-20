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
identity_counts = collections.Counter()
identity_by_match = {}
for g in games:
    log = Path("match-data/v4") / g["path"] / "team-a.stdout"
    if not log.is_file():
        state = "missing"
    else:
        content=log.read_bytes().replace(b"\\x00", b"").decode(errors="replace")
        state = "verified" if content.startswith("Bot1 strategy v4 (SDK 2.2.5)") else "unverified"
    identity_counts[state] += 1
    identity_by_match[g["path"]] = state
print("TEAM_A_IDENTITY",dict(identity_counts))
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
       corrected_result_assuming_team_A_is_Bot1=result,team_a_identity=identity_by_match[g["path"]],status=status,
       map_hash=g["mapHash"],round=g["round"]
    ))
csv_path=DEST/"manifest.csv"
with csv_path.open("w",newline="") as f:
    writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
summary=dict(total=len(rows),teamAIdentity=dict(identity_counts),outcomesByScore=[dict(outcome=x[0][0],scoreLeader=x[0][1],games=x[1]) for x in sorted(outcome_cross.items())],
              resolution=dict(outcome_winner=outcome_winner,classificationCounts={str(k):v for k,v in sorted(counts.items())}),
              mismatches=[r for r in rows if r["status"]!="agreement"])
(DEST/"summary.json").write_text(json.dumps(summary,indent=2)+"\n")
print("AFTER_ENGINE_OUTCOME",dict(sorted(((str(k),v) for k,v in counts.items()))))
print("CORRECTIONS_NEEDED",sum(r["status"]=="wrong_folder" for r in rows))
print("UNRESOLVED",sum(r["status"]=="unresolved" for r in rows))
print("MISMATCH_SAMPLE",json.dumps(summary["mismatches"][:8],indent=1))
print("OUTPUT",csv_path)

# Rebuild performance summaries by the engine-corrected result, not directory.
from statistics import median
def safe_med(values):
    vals=[v for v in values if v is not None]
    return round(float(median(vals)), 2) if vals else None
corrected_groups=collections.defaultdict(list)
for game in games:
    leader=outcome_winner[str(game["outcome"])]
    outcome_label="wins" if leader=="A" else "losses"
    elo_tier=game["category"].split("/")[0]
    corrected_groups[f"{elo_tier}/{outcome_label}"].append(game)
corrected_stats={}
for label, sample in sorted(corrected_groups.items()):
    cp=[g for g in sample if "200" in g["teamA"]["checkpoint"] and "200" in g["teamB"]["checkpoint"]]
    corrected_stats[label]={
        "games":len(sample),
        "median_our_gems":safe_med(g["teamA"]["score"] for g in sample),
        "median_opponent_gems":safe_med(g["teamB"]["score"] for g in sample),
        "median_our_gold":safe_med(g["teamA"]["gold"] for g in sample),
        "median_opponent_gold":safe_med(g["teamB"]["gold"] for g in sample),
        "median_our_deaths":safe_med(g["teamA"]["deaths"] for g in sample),
        "median_opponent_deaths":safe_med(g["teamB"]["deaths"] for g in sample),
        "median_score_gap_at_200_opponent_minus_us":safe_med(
            g["teamB"]["checkpoint"]["200"]["score"]-g["teamA"]["checkpoint"]["200"]["score"] for g in cp),
        "matches_with_round200":len(cp),
    }
(DEST/"CORRECTED-OUTCOME-ANALYSIS.md").write_text(
    "# V4 corrected-category performance\\n\\n"
    "Using official replay-engine outcomes, not original wins/losses folder labels. "
    "All data use pre–Week 2 engine 0.0.3 and deliberately selected matches.\\n\\n"
    "| Verified category | Games | Median gems (v4–opponent) | Median gold (v4–opponent) | Median deaths (v4–opponent) | Opp. score lead at round 200 |\\n"
    "|---|---:|---|---|---|---:|\\n" +
    "".join(f"| {key} | {stat['games']} | {stat['median_our_gems']}–{stat['median_opponent_gems']} | "
            f"{stat['median_our_gold']}–{stat['median_opponent_gold']} | "
            f"{stat['median_our_deaths']}–{stat['median_opponent_deaths']} | "
            f"{stat['median_score_gap_at_200_opponent_minus_us']} |\\n"
            for key,stat in corrected_stats.items()) +
    "\\nThe round-200 column includes only games reaching that checkpoint. "
    "Interpret these as descriptive historical comparisons, not post-patch performance claims.\\n"
)
summary["correctedCategories"]=corrected_stats
(DEST/"summary.json").write_text(json.dumps(summary,indent=2)+"\\n")
print("CORRECTED_GROUP_SUMMARY",json.dumps(corrected_stats,sort_keys=True))


report = [
    "# Reconciled v4 match labels", "",
    "Generated from the existing 245 engine-0.0.3 replay reconstructions.",
    "No replay files were changed or moved.", "",
    f"- Analyzed matches: **{len(rows)}**",
    f"- Team A identity: **{identity_counts['verified']}** verified v4 stdout markers, "
    f"**{len(rows)-identity_counts['verified']}** unverified/missing.",
    f"- Original score-comparison discrepancies: **{sum(not x['classifiedCorrectly'] for x in games)}**.",
    f"- Engine-outcome folder discrepancies: **{sum(r['status']=='wrong_folder' for r in rows)}**.",
    f"- Replays needing manual outcome verification: **{sum(r['status']=='unresolved' or r['team_a_identity']!='verified' for r in rows)}**.",
    f"- True v4 engine wins in this selected dataset: **{sum(r['corrected_result_assuming_team_A_is_Bot1']=='wins' for r in rows)}**.",
    f"- True v4 engine losses in this selected dataset: **{sum(r['corrected_result_assuming_team_A_is_Bot1']=='losses' for r in rows)}**.",
    "",
    "## Method", "",
    "Engine outcome enum is inferred and checked against all decisive (non-tied) scores: 1 = Team A, 2 = Team B.",
    "When scores tie, engine outcome is authoritative; a tie is not necessarily a draw.",
    "Team A is verified against `team-a.stdout` within each match folder.",
    "The original `category` retains the opponent Elo tier, but analyses should use the corrected result column rather than the folder's wins/losses directory.",
    "Matched replays are anchored by their original `path` and SHA-256. This dataset is selected, not a random lobby sample.",
    "",
    "## Counts by folder", "",
    "| Original folder | Correct | Incorrect |", "|---|---:|---:|",
]
for category in sorted({r['category'] for r in rows}):
    subset=[r for r in rows if r['category']==category]
    report.append(f"| {category} | {sum(r['status']=='agreement' for r in subset)} | {sum(r['status']=='wrong_folder' for r in subset)} |")
report += ["", "A full per-match manifest is in [manifest-provisional.csv](manifest-provisional.csv)."]
(DEST/"RECONCILIATION.md").write_text("\n".join(report)+"\n")
if identity_counts["verified"] != len(rows):
    raise SystemExit("Not all Team A identities verified; do not finalize outcome labels.")
if len(rows) != 245 or len(outcome_winner) != 2:
    raise SystemExit("Unexpected dataset size or unresolved engine outcome mapping.")
