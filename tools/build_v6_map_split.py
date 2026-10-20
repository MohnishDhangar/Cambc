#!/usr/bin/env python3
"""Seal the four user-designated 2026a CAMBC holdout maps from v6 research.

Do NOT import per-game held-out replay data into optimization. This script reads
existing metadata only. It uses the prepared dataset's connected leakage-group
IDs, joining repeated replay content and five-game bundles, to quarantine every
training-map match in a connected component containing a holdout-map match.
Original files and prepared data are never modified.
"""
from collections import Counter, defaultdict
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSV = ROOT / "match-data/v5/prepared-high-elo/matches.csv"
MAPS = ROOT / "maps"
OUT = ROOT / "match-data/analysis/v6-elite-research"
HOLDOUT = frozenset(("01islands", "01hooks", "00lanes", "01corridors"))
EXPECTED_ALL = 21

def make_split():
    with CSV.open(newline="") as f:
        rows = list(csv.DictReader(f))
    local_maps = {p.stem for p in MAPS.glob("*.map26a")}
    if len(local_maps) != EXPECTED_ALL:
        raise ValueError(f"Expected {EXPECTED_ALL} distinct local maps, found {len(local_maps)}")
    missing = HOLDOUT - local_maps
    if missing:
        raise ValueError(f"Holdout maps absent from local repository: {missing}")
    if len(rows) != 500 or len({r["match_id"] for r in rows}) != 500:
        raise ValueError("Unexpected source match inventory; review split before proceeding")
    unknown = {r["map_name"] for r in rows} - local_maps
    if unknown:
        raise ValueError(f"Match maps not found locally: {unknown}")
    holdout_leakage_groups = {
        r["leakage_group"] for r in rows if r["map_name"] in HOLDOUT
    }
    annotated = []
    for r in rows:
        if r["map_name"] in HOLDOUT:
            split, why = "sealed_test", "four_user_reserved_maps"
        elif r["leakage_group"] in holdout_leakage_groups:
            split, why = "quarantine", "connected_to_sealed_test_bundle_or_replay"
        else:
            split, why = "train", "nonheldout_and_disconnected"
        annotated.append({**r, "v6_split": split, "v6_split_reason": why})
    subsets = {k: [r for r in annotated if r["v6_split"] == k]
               for k in ("train", "quarantine", "sealed_test")}
    def setvals(rows, key):
        return {r[key] for r in rows}
    train = subsets["train"]
    protected = subsets["quarantine"] + subsets["sealed_test"]
    for key in ("match_id", "replay_sha256", "match_group_id", "leakage_group"):
        if setvals(train,key) & setvals(protected,key):
            raise AssertionError(f"Training/test leakage in {key}")
    assert not ({r["map_name"] for r in train} & HOLDOUT)
    assert len({r["map_name"] for r in train}) == EXPECTED_ALL-len(HOLDOUT)
    counts = {k: {"records": len(v),
                  "distinct_replay_contents": len(setvals(v, "replay_sha256")),
                  "distinct_maps": len(setvals(v, "map_name")),
                  "opponents": dict(Counter(r["opponent"] for r in v)),
                  "sides": dict(Counter(r["our_side"] for r in v))}
              for k,v in subsets.items()}
    summary = {
        "schema_version": 1,
        "policy": "user_reserved_map_holdout_and_connected_component_quarantine",
        "reserved_map_names": sorted(HOLDOUT),
        "training_map_names": sorted(local_maps-HOLDOUT),
        "source_match_records": len(rows),
        "source_distinct_replay_contents": len(setvals(rows,"replay_sha256")),
        "split_counts": counts,
        "connected_components_quarantined": len(holdout_leakage_groups),
        "validation": {
            "no_heldout_maps_in_train": True,
            "no_train_test_replay_overlap": True,
            "no_train_test_five_game_bundle_overlap": True,
            "no_train_test_connected_leakage_group_overlap": True,
        },
        "note": "Never use sealed_test or quarantine records for model selection. Original source and prepared dataset are untouched. Replay engine version 1.0.0 is recording metadata, not the installed Linux CLI version.",
    }
    OUT.mkdir(parents=True, exist_ok=True)
    destination = OUT / "v6-map-split.csv"
    cols = ["match_id", "opponent", "our_side", "map_name",
            "replay_sha256", "match_group_id", "leakage_group",
            "v6_split", "v6_split_reason"]
    with destination.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(annotated)
    (OUT / "v6-map-split.json").write_text(json.dumps(summary,indent=2)+"\n")
    print(json.dumps(summary, indent=2))
    return summary

if __name__ == "__main__":
    make_split()
