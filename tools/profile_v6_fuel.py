#!/usr/bin/env python3
"""Action-level fuel profile: exact v6.6 against frozen v4, training maps only."""
import collections
import csv
import hashlib
import json
import os
import re
import subprocess
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "match-data/analysis/v6-fuel-profile"
MANIFEST = ROOT / "match-data/analysis/v6-elite-research/v6-map-split.json"
MAPS = ("01big-world", "01concentrated-wealth", "00contest")
EXPECTED_CPP = "321480f1f3bc4548f448f554b787c686bed8b86403d35e9208a76d2aa3a2eac3"
V4_ARCHIVE = "b296e83d43e8b16709e655ee4470a526e9e84160ee02fbad0e8c483661e1a062"
ENV = {**os.environ, "CAMBC_OFFLINE": "1", "CAMBC_NO_UPDATE_CHECK": "1"}
SPILL = re.compile(r"fuel spill at (.*?) from (\d+) to (\d+)")
def command(cmd, timeout=300):
    return subprocess.run(cmd, cwd=ROOT, env=ENV, capture_output=True, text=True, timeout=timeout)
def main():
    spec = json.loads(MANIFEST.read_text())
    assert spec["reserved_map_names"] == ["00lanes","01corridors","01hooks","01islands"]
    assert set(MAPS) <= set(spec["training_map_names"])
    cpp = ROOT / "bots/Bot6/src/bot.cpp"
    assert hashlib.sha256(cpp.read_bytes()).hexdigest() == EXPECTED_CPP
    archive = ROOT / "bots/Bot1/Bot1-v4.zip"
    assert hashlib.sha256(archive.read_bytes()).hexdigest() == V4_ARCHIVE
    with zipfile.ZipFile(archive) as z:
        names = [n for n in z.namelist() if n.endswith((".h", ".cpp"))]
        assert len(names) == 6
        for name in names:
            dest = ROOT / "bots/Bot4Frozen/src" / Path(name).name
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(z.read(name))
    for bot in ("Bot4Frozen", "Bot6"):
        p = command(["cambc", "build", bot, "--release"], 260)
        if p.returncode: raise RuntimeError("Compile failed: " + bot + " " + (p.stdout+p.stderr)[-1200:])
    OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    totals = collections.Counter()
    for mp in MAPS:
        for side in ("A", "B"):
            folder = OUT / "replays" / (mp+"-"+side)
            folder.mkdir(parents=True, exist_ok=True)
            bots = ["Bot6", "Bot4Frozen"] if side=="A" else ["Bot4Frozen", "Bot6"]
            p = command(["cambc","run",*bots,"--release","--map",str(ROOT/"maps"/(mp+".map26a")),
                         "--out-dir",str(folder),"--statistics",str(folder/"stats.json"),"--json"])
            if p.returncode: raise RuntimeError(mp+side+" run failed: "+(p.stdout+p.stderr)[-1200:])
            stats = json.loads((folder/"stats.json").read_text())
            zips = list(folder.glob("*.repl26a"))
            assert len(zips)==1
            with zipfile.ZipFile(zips[0]) as z:
                data = z.read("team-"+side.lower()+".stdout").replace(b"\x00",b"").decode(errors="replace")
            action_count = collections.Counter()
            samples = collections.defaultdict(list)
            errors = []
            for line in data.splitlines():
                m = SPILL.search(line)
                if m:
                    name = m.group(1).strip()
                    action_count[name]+=1
                    if len(samples[name]) < 3: samples[name].append(line[:220])
                if "bot error" in line.lower(): errors.append(line[:220])
            team = "team"+side
            gems = sum(int(c["metrics"]["submittedGems"]) for c in stats["champions"] if c["team"]==team)
            faults = stats.get("diagnostics",{}).get("botFaults",{}).get(team,0)
            for name, count in action_count.items():
                totals[name] += count
                rows.append(dict(map=mp,side=side,action=name,count=count,samples=" | ".join(samples[name])))
            print(mp,side,"spills",sum(action_count.values()),"by_action",dict(action_count),flush=True)
            folder.joinpath("v6-errors.txt").write_text("\n".join(errors)+"\n")
    with (OUT/"actions.csv").open("w",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=("map","side","action","count","samples"))
        writer.writeheader()
        writer.writerows(rows)
    result = {"engine":"CAMBC 3.0.1","base_v66_commit":"4d38b1b5b9697783d555e76797e1adc78e36637a",
              "v66_bot_cpp_sha256":EXPECTED_CPP,"frozen_v4_archive_sha256":V4_ARCHIVE,
              "maps":list(MAPS),"sealed_maps_excluded":spec["reserved_map_names"],
              "total_spills":sum(totals.values()),"by_action":totals,
              "per_game":{mp+"-"+side:{row["action"]:row["count"] for row in rows if row["map"]==mp and row["side"]==side} for mp in MAPS for side in "AB"}}
    (OUT/"profile.json").write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(result,indent=2),flush=True)
if __name__=="__main__": main()
