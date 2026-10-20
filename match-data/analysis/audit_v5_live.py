#!/usr/bin/env python3
"""Audit 2026a v5 field replays without assuming directory labels are actual results.

Pure Python, needs no CAMBC client or replay engine. Parses existing logs and
reports *provisional* classifications only. Never modifies source match files.
"""
from pathlib import Path
from collections import Counter,defaultdict
import csv,hashlib,json,re,statistics

ROOT=Path("match-data/v5/similar-elo-teams")
OUT=Path("match-data/analysis/v5-field-audit")
OUT.mkdir(parents=True,exist_ok=True)
folders=sorted(p.parent for p in ROOT.rglob("replay.repl26a"))
rows=[]
for folder in folders:
    replay=folder/"replay.repl26a"
    logs=sorted(folder.glob("team-*.stdout"))
    side=logs[0].name.split(".")[0][-1] if len(logs)==1 else "unknown"
    text=logs[0].read_bytes().replace(b"\x00",b"").decode("utf-8",errors="replace") if len(logs)==1 else ""
    match_id=folder.name
    result=folder.parent.parent.name
    category=folder.relative_to(ROOT).parts[0]
    blob=replay.read_bytes()
    spills=re.findall(r"fuel spill at ([^\n]+?) from (\d+) to (\d+)",text)
    failures=re.findall(r"bot error[^\n]*",text,flags=re.I)
    prefix=text[:min(800,len(text))]
    markers=len(re.findall(r"Bot1 strategy v5 Week2 \(SDK 2\.2\.5\)",text))
    rows.append(dict(
        replay_path=str(replay), folder_label=result,opponent_group=folder.parent.name,
        game=match_id, recorded_team_side=side, v5_log_identity="yes" if markers else "no",
        markers=markers, replay_sha256=hashlib.sha256(blob).hexdigest(),replay_bytes=len(blob),
        replay_header=blob[:16].hex(), replay_engine_header=blob[8:14].hex() if len(blob)>14 else "",
        stdout_bytes=logs[0].stat().st_size if logs else 0,
        fuel_bytes=sum(x.stat().st_size for x in folder.glob("team-*.fuel")),
        stdout_spill_messages=len(spills),
        earliest_spill_round=int(spills[0][1]) if spills else "",
        first_spill_action=spills[0][0] if spills else "",
        bot_error_lines=len(failures),
        sample_error=failures[0][:150] if failures else "",
        draft_picks="|".join(re.findall(r"draft (\d+)",prefix)),
    ))
assert len(rows)==55,f"Expected 55 matches, got {len(rows)}"
assert len({r["replay_sha256"] for r in rows})==len(rows),"Duplicate replay bytes"
with (OUT/"match-audit.csv").open("w",newline="") as fd:
    writer=csv.DictWriter(fd,fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)

by_label=Counter(r["folder_label"] for r in rows)
by_side=Counter(r["recorded_team_side"] for r in rows)
by_side_label=Counter((r["folder_label"],r["recorded_team_side"]) for r in rows)
by_engine=Counter(r["replay_engine_header"] for r in rows)
error_rows=[r for r in rows if r["bot_error_lines"]]
spill_rows=[r for r in rows if r["stdout_spill_messages"]]
spills_by=Counter(r["first_spill_action"] for r in spill_rows)
per_group=defaultdict(list)
for r in rows:
    per_group[(r["folder_label"],r["opponent_group"])].append(r)
summary={
    "total":len(rows),"by_folder_label":dict(by_label),
    "by_team_side":dict(by_side),
    "by_folder_label_and_side":{str(k):v for k,v in sorted(by_side_label.items())},
    "replay_engine_headers":dict(by_engine),
    "all_v5_markers_present":all(r["v5_log_identity"]=="yes" for r in rows),
    "replay_sha256_unique":len({r["replay_sha256"] for r in rows}),
    "bot_error_matches":len(error_rows),
    "bot_error_lines":sum(r["bot_error_lines"] for r in rows),
    "sample_bot_errors":[{"replay":r["replay_path"],"error":r["sample_error"]} for r in error_rows[:15]],
    "spilling_matches":len(spill_rows),
    "total_stdout_spill_messages":sum(r["stdout_spill_messages"] for r in rows),
    "spilling_matches_by_label":dict(Counter(r["folder_label"] for r in spill_rows)),
    "spill_first_actions":dict(spills_by),
    "heaviest_spill_games":[{"replay":r["replay_path"],"spills":r["stdout_spill_messages"],
                             "first_round":r["earliest_spill_round"]} for r in
                             sorted(spill_rows,key=lambda r:-r["stdout_spill_messages"])[:10]],
    "by_group":[{"folder_label":k[0],"group":k[1],"matches":len(q),"spill_matches":sum(int(r["stdout_spill_messages"]>0) for r in q),
                 "stdout_error_matches":sum(int(r["bot_error_lines"]>0) for r in q)} for k,q in sorted(per_group.items())]
}
(OUT/"summary.json").write_text(json.dumps(summary,indent=2)+"\n")
lines=[
"# v5 live replay audit — initial evidence", "",
"Source: `match-data/v5/similar-elo-teams` on GitHub main, archived on 20 Oct 2026.", "",
f"- Complete replay folders: **{len(rows)}**, with **{len({r['replay_sha256'] for r in rows})} unique replay hashes**.",
f"- Folder labels: **{by_label.get('losses',0)} losses**, **{by_label.get('wins',0)} wins**. **Not engine-verified:** previous v4 labels were wrong in some matches.",
f"- Recorded v5 team side: **{by_side.get('a',0)} Team A**, **{by_side.get('b',0)} Team B**; a cross-tab is below.",
f"- Bot stdout identity markers: **{sum(r['v5_log_identity']=='yes' for r in rows)}/{len(rows)}**.",
f"- Replay engine header bytes: `{dict(by_engine)}` (header alone does not validate game scores or outcomes).",
f"- 'fuel spill at' stdout messages: **{summary['total_stdout_spill_messages']}** across **{len(spill_rows)}** matches.",
f"- 'bot error' stdout lines: **{summary['bot_error_lines']}** across **{len(error_rows)}** matches.",
"",
"## Folder category and observed side", "",
"| Folder result | Bot team A | Bot team B |", "|---|---:|---:|"]
for label in ("wins","losses"):
    lines.append(f"| {label} | {by_side_label.get((label,'a'),0)} | {by_side_label.get((label,'b'),0)} |")
lines += ["","## Qualification","","Folder results are provisional until reconciled with official server winner or matching replay decoder. Each match uses whichever of `team-a.stdout` or `team-b.stdout` is present, to avoid assuming Bot1 is always Team A. A printed `fuel spill at` message is a bot diagnostic; **it is not by itself proof of an engine-reported fault**. Inspect full replay and fuel trace to determine any performance impact.","",
"## Most diagnostic logs", "",
"| Labeled result | Match | Spill messages | First spill round |","|---|---|---:|---:|"]
for r in sorted(spill_rows,key=lambda a:-a["stdout_spill_messages"])[:12]:
    lines.append(f"| {r['folder_label']} | `{r['opponent_group']}/{r['game']}` | {r['stdout_spill_messages']} | {r['earliest_spill_round']} |")
lines += ["", "## Follow-up","", "1. Verify 55 outcomes from the official result or engine timeline, as was necessary for v4.","2. Analyze replays at champion-turn resolution for draft balance, score checkpoints, camp selection and coordination.","3. Validate fuel diagnostic significance before changing bot code.","4. Stratify by map and opponent group; wins/losses are selected data, not an unbiased win-rate estimate.",""]
(OUT/"REPORT.md").write_text("\n".join(lines))
print(json.dumps({k:v for k,v in summary.items() if k not in ("by_group","heaviest_spill_games","sample_bot_errors")},indent=2))
print("HEAVY",json.dumps(summary["heaviest_spill_games"][:5]))
