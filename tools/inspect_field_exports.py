#!/usr/bin/env python3
"""Deduplicated, holdout-filtered diagnostics from nested CAMBC match exports.
Does NOT reconstruct wins/scores; official simulation is needed for that.
"""
import collections
import hashlib
import io
import json
import re
import sys
import zipfile
from pathlib import Path

SEALED = {"00lanes", "01corridors", "01hooks", "01islands"}
ROOT = Path(__file__).resolve().parents[1]

def blob_sha(data):
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\\0" + data).hexdigest()

def index_maps():
    result = {}
    for path in (ROOT / "maps").glob("*.map26a"):
        raw = path.read_bytes()
        result[blob_sha(raw)] = path.stem
    return result

def embedded_map(replay):
    offsets = [replay.find(bytes([4, 1, pick, 0, 0, 0, 255, 3, 0]))
               for pick in range(12)]
    offsets = [x for x in offsets if x >= 18]
    if not offsets:
        return None
    return replay[14:min(offsets) - 4]

def process(files):
    maps = index_maps()
    rows, seen_by_version = [], collections.defaultdict(set)
    counts = collections.Counter()
    for label, filename in files:
        with zipfile.ZipFile(filename) as top:
            for group_name in top.namelist():
                if not group_name.endswith(".zip"):
                    continue
                with zipfile.ZipFile(io.BytesIO(top.read(group_name))) as group:
                    for match in group.namelist():
                        if not match.endswith(".zip"):
                            continue
                        with zipfile.ZipFile(io.BytesIO(group.read(match))) as game:
                            raw = game.read("replay.repl26a")
                            digest = hashlib.sha256(raw).hexdigest()
                            if digest in seen_by_version[label]:
                                counts[(label, "duplicate")] += 1
                                continue
                            seen_by_version[label].add(digest)
                            mapbytes = embedded_map(raw)
                            mapname = maps.get(blob_sha(mapbytes), "UNKNOWN") if mapbytes else "UNKNOWN"
                            if mapname in SEALED:
                                counts[(label, "heldout_excluded")] += 1
                                continue
                            stdout = game.read("team-a.stdout").replace(b"\\0", b"").decode(errors="replace")
                            actions = collections.Counter(x.split(" from ")[0]
                                for x in re.findall(r"fuel spill at ([^\\n]+)", stdout, re.I))
                            rows.append({"version": label, "map": mapname, "game": match[:2],
                                         "sha256_prefix": digest[:12], "fuel_spills": sum(actions.values()),
                                         "last_action_markers": dict(actions)})
                            counts[(label, "included")] += 1
    return {"observations": rows,
            "counts": {label: {metric: counts[(label, metric)]
                for metric in ("included", "duplicate", "heldout_excluded")}
                for label, _ in files},
            "warning": "No scores/winner can be inferred without the matching CAMBC engine."}

def main():
    if len(sys.argv) < 3:
        raise SystemExit("usage: python tools/inspect_field_exports.py v6.8.zip v6.9.zip")
    report = process([("v6.8", sys.argv[1]), ("v6.9", sys.argv[2])])
    Path("field-diagnostics-nonheldout.json").write_text(json.dumps(report, indent=2) + "\\n")
    print(json.dumps(report["counts"], indent=2))
if __name__ == "__main__":
    main()
