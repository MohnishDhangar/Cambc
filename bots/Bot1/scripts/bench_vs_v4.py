#!/usr/bin/env python3
"""Reproducible old-engine compatibility/regression tests of v5 against frozen v4.

Not an estimate of performance under the Week 2 patch. The shipped map files
and locally released client are pre-patch. Each map is run with both team sides.
"""
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "results" / "v5-v4"
OUT.mkdir(parents=True, exist_ok=True)
MAPS = ["packs", "lanes", "elkring", "interlock", "expanse",
        "rows", "corners", "monolith", "collision"]
CLI = os.environ.get("CAMBC_CLI", "cambc")
ENV = {**os.environ, "CAMBC_OFFLINE": "1", "CAMBC_NO_UPDATE_CHECK": "1"}
results = []

def run_one(map_name, side):
    folder = OUT / map_name / side
    folder.mkdir(parents=True, exist_ok=True)
    bot_a, bot_b = ("Bot1", "BaselineV4") if side == "A" else ("BaselineV4", "Bot1")
    stats = folder / "stats.json"
    args = [CLI, "run", bot_a, bot_b, "--release", "--map",
            str(ROOT / "maps" / (map_name+".map26a")),
            "--out-dir", str(folder), "--statistics", str(stats), "--json"]
    proc = subprocess.run(args, cwd=ROOT, env=ENV, capture_output=True, text=True, timeout=150)
    (folder / "runner.log").write_text(proc.stdout + "\n" + proc.stderr)
    if proc.returncode or not stats.exists():
        return {"map":map_name,"side":side,"error":f"code {proc.returncode}: {(proc.stdout+proc.stderr)[-1300:]}"}
    game = json.loads(stats.read_text())
    ch = game.get("champions", [])
    def total(team, metric):
        return sum(int(x.get("metrics",{}).get(metric,0)) for x in ch if x.get("team")==team)
    us = "team"+side
    them = "team"+("B" if side=="A" else "A")
    faults = game.get("diagnostics",{}).get("botFaults",{})
    return {"map":map_name,"side":side,"win":game["match"]["outcome"]==us,
            "rounds":game["match"]["roundsStarted"],
            "v5_gems":total(us,"submittedGems"),"v4_gems":total(them,"submittedGems"),
            "v5_gold":total(us,"earnedGold"),"v4_gold":total(them,"earnedGold"),
            "v5_deaths":total(us,"deaths"),"v4_deaths":total(them,"deaths"),
            "v5_faults":faults.get(us,0),"v4_faults":faults.get(them,0)}
for name in MAPS:
    for side in ("A","B"):
        row=run_one(name,side)
        results.append(row)
        print(json.dumps(row),flush=True)
        (OUT/"results.json").write_text(json.dumps(results,indent=2)+"\n")
good=[x for x in results if "error" not in x]
final={"games":len(results),"completed":len(good),
       "v5_wins":sum(x["win"] for x in good),
       "v5_faults":sum(x["v5_faults"] for x in good),
       "mean_gem_margin":sum(x["v5_gems"]-x["v4_gems"] for x in good)/len(good) if good else None,
       "results":results}
(OUT/"summary.json").write_text(json.dumps(final,indent=2)+"\n")
print("FINAL",json.dumps({k:v for k,v in final.items() if k!="results"}))
sys.exit(1 if len(good)!=len(results) or final["v5_faults"] else 0)
