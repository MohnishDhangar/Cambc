#!/usr/bin/env python3
"""Prespecified v6.9 distance-aware gem-banking experiment; four sealed maps are never accessed."""
import concurrent.futures
import csv
import hashlib
import json
import math
import os
import subprocess
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "match-data/analysis/v6.9-adaptive-bank"
SPLIT = ROOT / "match-data/analysis/v6-elite-research/v6-map-split.json"
BASE = "0ddd5338b94db824f9f53261a17f020490b7017f"
V4_SHA = "b296e83d43e8b16709e655ee4470a526e9e84160ee02fbad0e8c483661e1a062"
FILES = ("bot.cpp", "bot.h", "draft.cpp", "draft.h", "main.cpp", "random.h")
PAIRS = {
    "v69_vs_v4": ("Bot6BankV69", "Bot4Frozen"),
    "v68_vs_v4": ("Bot6V68", "Bot4Frozen"),
    "v69_vs_v68": ("Bot6BankV69", "Bot6V68"),
}
ENV = {**os.environ, "CAMBC_NO_UPDATE_CHECK": "1", "CAMBC_OFFLINE": "1"}

def sha(data):
    return hashlib.sha256(data).hexdigest()

def command(args, timeout=300):
    return subprocess.run(args, cwd=ROOT, env=ENV, capture_output=True,
                          text=True, timeout=timeout)

def prepare():
    split = json.loads(SPLIT.read_text())
    maps = split["training_map_names"]
    sealed = split["reserved_map_names"]
    assert sealed == ["00lanes", "01corridors", "01hooks", "01islands"]
    assert len(maps) == len(set(maps)) == 17 and not set(maps) & set(sealed)
    archive = ROOT / "bots/Bot1/Bot1-v4.zip"
    assert sha(archive.read_bytes()) == V4_SHA, "Frozen v4 archive changed"
    with zipfile.ZipFile(archive) as zipped:
        sources = [name for name in zipped.namelist() if name.endswith((".cpp", ".h"))]
        assert len(sources) == 6
        for name in sources:
            dest = ROOT / "bots/Bot4Frozen/src" / Path(name).name
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(zipped.read(name))
    src = ROOT / "bots/Bot6/src"
    bot = (src / "bot.cpp").read_text()
    assert "#define V6_EARLY_EXIT_PATH 1" in bot
    assert "#define V6_ADAPTIVE_BANK_DISTANCE 1" in bot
    assert bot.startswith("#define V6_MACRO_MODE 1\n#define V6_BANK_THRESHOLD 0\n")
    hashes = {"v69_bot_sha256": sha(bot.encode())}
    for name in FILES:
        old = subprocess.check_output(["git", "show", BASE + ":bots/Bot6/src/" + name], cwd=ROOT)
        present = (src / name).read_bytes()
        if name != "bot.cpp":
            assert old == present, "Non-bot source changed: " + name
        else:
            expected = old.decode().replace(
                "#define V6_EARLY_EXIT_PATH 1\n",
                "#define V6_EARLY_EXIT_PATH 1\n#define V6_ADAPTIVE_BANK_DISTANCE 1\n")
            expected = expected.replace(
                '    const bool should_bank = bag && (bag>=static_cast<unsigned>(threshold)',
                "#if V6_ADAPTIVE_BANK_DISTANCE\n    // Batch small rewards only when a distant altar makes repeated trips costly.\n    // Nearby altars, exposed carriers, and the late game retain immediate banking.\n    const int altar_walk = altar_distance.get(position);\n    if (bag && round < 1500 && altar_walk > 12 && altar_walk < distance_field::unreachable\n        && me.health() > me.max_health() * .72f && !carrier_threat)\n        threshold = 8;\n#endif\n    const bool should_bank = bag && (bag>=static_cast<unsigned>(threshold)")
            assert expected == bot, "v6.9 has non-prespecified strategy edits"
        hashes["v68_" + name] = sha(old)
        for candidate, payload in (("Bot6V68", old), ("Bot6BankV69", present)):
            dest = ROOT / "bots" / candidate / "src" / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(payload)
    for botname in ("Bot4Frozen", "Bot6V68", "Bot6BankV69"):
        result = command(["cambc", "build", botname, "--release"], timeout=260)
        if result.returncode:
            raise RuntimeError(botname + " compile failed: " + (result.stdout + result.stderr)[-2000:])
        print("compiled", botname, flush=True)
    return maps, sealed, hashes

def play(job):
    pairing, map_name, side = job
    candidate, opponent = PAIRS[pairing]
    bots = (candidate, opponent) if side == "A" else (opponent, candidate)
    me, other = "team" + side, "team" + ("B" if side == "A" else "A")
    folder = OUT / "replays" / (pairing + "-" + map_name + "-" + side)
    folder.mkdir(parents=True, exist_ok=True)
    args = ["cambc", "run", *bots, "--release", "--map",
            str(ROOT / "maps" / (map_name + ".map26a")),
            "--out-dir", str(folder), "--statistics",
            str(folder / "stats.json"), "--json"]
    row = {"pairing": pairing, "map": map_name, "side": side, "error": ""}
    try:
        proc = command(args)
        if proc.returncode:
            row["error"] = (proc.stdout + proc.stderr)[-700:]
            return row
        stats = json.loads((folder / "stats.json").read_text())
        count = lambda team: sum(int(c["metrics"]["submittedGems"])
                                 for c in stats["champions"] if c["team"] == team)
        row.update(win=int(stats["match"].get("outcome") == me),
                   enemy_win=int(stats["match"].get("outcome") == other),
                   gems=count(me), enemy_gems=count(other),
                   margin=count(me)-count(other),
                   faults=stats.get("diagnostics", {}).get("botFaults", {}).get(me, 0),
                   rounds=stats["match"].get("roundsStarted"))
        replays = list(folder.glob("*.repl26a"))
        if len(replays) != 1:
            row["error"] = "Expected one replay, got " + str(len(replays))
            return row
        with zipfile.ZipFile(replays[0]) as zipped:
            stdout = zipped.read("team-" + side.lower() + ".stdout")
        lines = stdout.replace(b"\0", b"").decode(errors="replace").splitlines()
        row["exceptions"] = sum("bot error" in line.lower() or "v6 error" in line.lower()
                                for line in lines)
        row["fuel_spills"] = sum("fuel spill at" in line.lower() for line in lines)
    except (subprocess.TimeoutExpired, OSError, KeyError, ValueError, zipfile.BadZipFile) as exc:
        row["error"] = str(exc)
    return row

def stats_of(rows):
    n = len(rows)
    wins = sum(r.get("win", 0) for r in rows)
    p, z = wins / n, 1.96
    denominator = 1 + z*z/n
    centre = (p + z*z/(2*n))/denominator
    radius = z*math.sqrt(p*(1-p)/n + z*z/(4*n*n))/denominator
    return {"games": n, "wins": wins,
            "wilson95": [round(centre-radius, 3), round(centre+radius, 3)],
            "mean_gem_margin": round(sum(r.get("margin", 0) for r in rows)/n, 2),
            "side_A_wins": sum(r.get("win", 0) for r in rows if r["side"] == "A"),
            "side_B_wins": sum(r.get("win", 0) for r in rows if r["side"] == "B"),
            "faults": sum(r.get("faults", 0) for r in rows),
            "exceptions": sum(r.get("exceptions", 0) for r in rows),
            "fuel_spills": sum(r.get("fuel_spills", 0) for r in rows),
            "failed": sum(bool(r.get("error")) for r in rows)}

def main():
    maps, sealed, hashes = prepare()
    OUT.mkdir(parents=True, exist_ok=True)
    jobs = [(name, mp, side) for name in PAIRS for mp in maps for side in "AB"]
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        rows = list(pool.map(play, jobs))
    fields = ("pairing", "map", "side", "win", "enemy_win", "gems", "enemy_gems",
              "margin", "faults", "exceptions", "fuel_spills", "rounds", "error")
    with (OUT / "games.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    index = {(r["pairing"], r["map"], r["side"]): r for r in rows}
    comparisons = []
    for mp in maps:
        for side in "AB":
            candidate = index[("v69_vs_v4", mp, side)]
            control = index[("v68_vs_v4", mp, side)]
            if "margin" in candidate and "margin" in control:
                comparisons.append((candidate["win"]-control["win"],
                                    candidate["margin"]-control["margin"]))
    result = {"engine": "CAMBC 3.0.1", "base_v68_commit": BASE,
              "frozen_v4_zip_sha256": V4_SHA, "source_hashes": hashes,
              "training_maps": maps, "sealed_maps_excluded": sealed,
              "pairings": {name: stats_of([r for r in rows if r["pairing"] == name])
                           for name in PAIRS},
              "paired_vs_v4": {"complete_pairs": len(comparisons),
                               "net_wins": sum(x[0] for x in comparisons),
                               "mean_margin_delta": round(sum(x[1] for x in comparisons) /
                                                          max(len(comparisons), 1), 2)},
              "match_count": len(rows)}
    result["promotion_gate"] = {
        "all_games_complete": not any(r.get("error") for r in rows),
        "candidate_zero_faults": all(not r.get("faults") and not r.get("exceptions") and not r.get("fuel_spills")
                                      for r in rows if r["pairing"].startswith("v69_")),
        "higher_win_count_vs_v4": result["pairings"]["v69_vs_v4"]["wins"] >
                                  result["pairings"]["v68_vs_v4"]["wins"],
        "better_gem_margin_vs_v4": result["paired_vs_v4"]["mean_margin_delta"] > 0,
        "note": "All gates needed; CI success alone does not establish a better bot; reject fuel spills."
    }
    (OUT / "summary.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2), flush=True)
    if any(r.get("error") for r in rows):
        raise SystemExit("Incomplete matches: inspect individual games")

if __name__ == "__main__":
    main()
