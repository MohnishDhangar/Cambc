#!/usr/bin/env python3
"""V6.23 one-variable navigation preflight ablation; CAMBC 3.0.1.

Compiles pinned v6.22 twice: unchanged and with exactly one fuel guard changed.
Both play archived v4 and each other on 17 permitted maps, both sides.
"""
import concurrent.futures
import csv
import hashlib
import json
import subprocess
import zipfile
from pathlib import Path
import benchmark_v6_22_raid as bench

ROOT = bench.ROOT
BASE = "13e96cb1c1e0e95c9ad14c49307b0d817852c9e3"
BASE_BOT_SHA = "e562b86a1ce88f5e7624de9381298f26b8f59b9ca892365d05af0133f0f02be9"
OUT = ROOT / "match-data/analysis/v6.23-navigation-fuel-preflight"
OLD = b"    if (fuel_remaining() < 18000) return false;\n    auto& me = self();"
NEW = b"    // Reserve enough fuel for a large-map distance-field search.\n    if (fuel_remaining() < 45000) return false;\n    auto& me = self();"
PAIRS = {
    "guard_vs_v4": ("Bot6Guard", "Bot4Frozen"),
    "base_vs_v4": ("Bot6Base", "Bot4Frozen"),
    "guard_vs_base": ("Bot6Guard", "Bot6Base"),
}
bench.OUT = OUT
bench.PAIRS = PAIRS

def prepare():
    split = json.loads(bench.SPLIT.read_text())
    maps, sealed = split["training_map_names"], split["reserved_map_names"]
    assert len(maps) == len(set(maps)) == 17
    assert sealed == ["00lanes", "01corridors", "01hooks", "01islands"]
    assert not set(maps) & set(sealed)
    archive = ROOT / "bots/Bot1/Bot1-v4.zip"
    assert bench.sha(archive.read_bytes()) == bench.V4_SHA
    with zipfile.ZipFile(archive) as z:
        files = [name for name in z.namelist() if name.endswith((".cpp", ".h"))]
        assert len(files) == 6
        for name in files:
            dst = ROOT / "bots/Bot4Frozen/src" / Path(name).name
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(z.read(name))
    hashes = {}
    for name in bench.FILES:
        data = subprocess.check_output(["git", "show", BASE + ":bots/Bot6/src/" + name], cwd=ROOT)
        if name == "bot.cpp":
            assert bench.sha(data) == BASE_BOT_SHA, "Pinned baseline source changed"
            assert data.count(OLD) == 1, "Navigation guard no longer unique"
            altered = data.replace(OLD, NEW, 1)
        else:
            altered = data
        hashes["base_" + name] = bench.sha(data)
        hashes["candidate_" + name] = bench.sha(altered)
        for bot, payload in (("Bot6Base", data), ("Bot6Guard", altered)):
            dest = ROOT / "bots" / bot / "src" / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(payload)
    assert hashes["candidate_bot.cpp"] != hashes["base_bot.cpp"]
    assert all(hashes["candidate_" + name] == hashes["base_" + name]
               for name in bench.FILES if name != "bot.cpp")
    for bot in ("Bot4Frozen", "Bot6Base", "Bot6Guard"):
        result = bench.command(["cambc", "build", bot, "--release"], timeout=260)
        if result.returncode:
            raise RuntimeError(bot + " build failed: " + (result.stdout + result.stderr)[-2000:])
        print("compiled", bot, flush=True)
    return maps, sealed, hashes

def main():
    maps, sealed, hashes = prepare()
    OUT.mkdir(parents=True, exist_ok=True)
    jobs = [(name, mp, side) for name in PAIRS for mp in maps for side in "AB"]
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        rows = list(pool.map(bench.play, jobs))
    fields = ("pairing", "map", "side", "win", "enemy_win", "gems", "enemy_gems",
              "margin", "faults", "exceptions", "fuel_spills", "rounds", "error")
    with (OUT / "games.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    index = {(r["pairing"], r["map"], r["side"]): r for r in rows}
    deltas = []
    for mp in maps:
        for side in "AB":
            a, b = index[("guard_vs_v4", mp, side)], index[("base_vs_v4", mp, side)]
            if "margin" in a and "margin" in b:
                deltas.append((a["win"] - b["win"], a["margin"] - b["margin"],
                               a["fuel_spills"] - b["fuel_spills"]))
    stats = {name: bench.stats_of([r for r in rows if r["pairing"] == name])
             for name in PAIRS}
    candidate = stats["guard_vs_v4"]
    training_gate = (candidate["games"] == 34 and candidate["wins"] >= 24
                     and candidate["mean_gem_margin"] > 0
                     and not candidate["faults"] and not candidate["exceptions"]
                     and not candidate["failed"])
    result = {
        "engine": "CAMBC 3.0.1", "base_commit": BASE,
        "frozen_v4_zip_sha256": bench.V4_SHA,
        "change": "navigate preflight fuel threshold 18000 -> 45000",
        "source_hashes": hashes, "training_maps": maps,
        "sealed_maps_excluded": sealed, "pairings": stats,
        "paired_vs_v4": {
            "complete_pairs": len(deltas),
            "net_wins": sum(d[0] for d in deltas),
            "mean_margin_delta": round(sum(d[1] for d in deltas) / max(1, len(deltas)), 2),
            "fuel_spill_delta": sum(d[2] for d in deltas),
        },
        "match_count": len(rows),
        "training_threshold_met": training_gate,
        "out_of_sample_confirmed": False,
        "promotable": False,
        "note": "All 17 maps are training maps. No sealed-map or independent-opponent confirmation.",
    }
    (OUT / "summary.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2), flush=True)
    if any(r.get("error") for r in rows):
        raise SystemExit("Incomplete matches; inspect individual games")
    if any(r.get("faults") or r.get("exceptions") for r in rows):
        raise SystemExit("Engine fault or exception; inspect individual games")

if __name__ == "__main__":
    main()
