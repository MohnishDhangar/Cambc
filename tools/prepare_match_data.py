#!/usr/bin/env python3
"""Prepare downloaded matches without replaying or analyzing gameplay."""
import argparse
from collections import Counter, defaultdict
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import struct
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]
UUID = r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n")


def store(path, data):
    """Never overwrite a different previously extracted artifact."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != data:
            raise ValueError(f"Existing artifact differs: {path}")
    else:
        path.write_bytes(data)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=ROOT / "match-data/v5/high-elo-teams")
    parser.add_argument("--output", type=Path, default=ROOT / "match-data/v5/prepared-high-elo")
    parser.add_argument("--our-submission", help="User-confirmed submission label, not inferred from logs")
    args = parser.parse_args()
    source, output = args.source.resolve(), args.output.resolve()
    if output == source or source in output.parents:
        raise ValueError("Keep generated output outside the original collection")
    output.mkdir(parents=True, exist_ok=True)
    recorded_at = datetime.now(timezone.utc).isoformat()
    # A rerun without a new answer must preserve an earlier user-confirmed label.
    collection_path = output / "collection.json"
    previous = json.loads(collection_path.read_text()) if collection_path.exists() else {}
    submission = args.our_submission or previous.get("our_submission")
    files = sorted(p for p in source.rglob("*") if p.is_file())
    before = {str(p.relative_to(source)): sha(p.read_bytes()) for p in files}
    candidates = [p for p in files if p.suffix in (".zip", ".repl26a")]
    if not candidates:
        raise ValueError("No replay packages found")
    map_files = [(p.name, p.read_bytes()) for p in sorted((ROOT / "maps").glob("*.map26a"))]
    records, rejected, extras = {}, [], []
    for item in candidates:
        try:
            parts = item.relative_to(source).parts
            team = re.fullmatch(r"team-(.+?)-(?:elo-)?(\d+)", parts[0])
            side = re.fullmatch(r"position-([AB])", parts[2])
            group = re.fullmatch(rf"match-group-({UUID})", parts[3])
            identity = re.fullmatch(rf"(\d+)-({UUID})", item.stem if item.suffix == ".zip" else item.parent.name)
            if not all((team, side, group, identity)):
                raise ValueError("Unrecognized source path layout")
            artifacts = {}
            if item.suffix == ".zip":
                with zipfile.ZipFile(item) as archive:
                    if len(archive.namelist()) != len(set(archive.namelist())):
                        raise ValueError("Duplicate archive member names")
                    for info in archive.infolist():
                        if info.is_dir():
                            continue
                        if info.filename != Path(info.filename).name:
                            raise ValueError(f"Unexpected archive path: {info.filename}")
                        # read() checks the ZIP CRC; never use extractall().
                        artifacts[info.filename] = archive.read(info)
                provenance = {"kind": "zip", "path": str(item.relative_to(source)),
                              "sha256": before[str(item.relative_to(source))], "crc_verified": True}
            else:
                artifacts = {p.name: p.read_bytes() for p in sorted(item.parent.iterdir()) if p.is_file()}
                provenance = {"kind": "directory", "path": str(item.parent.relative_to(source)),
                              "crc_verified": None}
            raw = artifacts["replay.repl26a"]
            if len(raw) < 25 or int.from_bytes(raw[:8], "little") != 125779999602273:
                raise ValueError("Missing or invalid replay header")
            if int.from_bytes(raw[14:22], "little") != 120265261594231:
                raise ValueError("Missing embedded map header")
            engine = ".".join(map(str, raw[8:11]))
            fmt = ".".join(map(str, raw[11:14]))
            match_id, ours = identity[2], side[1]
            expected = {"replay.repl26a", *(f"team-{ours.lower()}.{ext}" for ext in ("stdout", "fuel", "debug"))}
            missing = sorted(expected - artifacts.keys())
            unexpected = sorted(artifacts.keys() - expected)
            if unexpected:
                extras.append({"match_id": match_id, "files": unexpected})
            replay_hash = sha(raw)
            if match_id in records:
                old = records[match_id]
                hashes = {name: sha(data) for name, data in artifacts.items()}
                if (old["files_sha256"] != hashes or old["opponent"]["team_name"] != team[1]
                        or old["our_bot"]["side"] != ours or old["match_group_id"] != group[1]):
                    raise ValueError("Conflicting artifacts or labels for repeated match ID")
                old["sources"].append(provenance)
                continue
            dest = output / "matches" / match_id
            for name, data in artifacts.items():
                store(dest / name, data)
            matches = [(name, data) for name, data in map_files if raw[14:14 + len(data)] == data]
            map_data = matches[0][1] if matches else None
            if map_data:
                store(output / "maps" / (sha(map_data) + ".map26a"), map_data)
            banners = sorted(set(m.decode("utf-8", errors="replace") for m in re.findall(
                rb"Bot1 strategy[^\x00\r\n]*", artifacts.get(f"team-{ours.lower()}.stdout", b""))))
            records[match_id] = {
                "schema_version": 1, "batch_id": "v5-high-elo", "match_id": match_id,
                "match_group_id": group[1], "match_index_in_group": int(identity[1]),
                "recorded_at": recorded_at, "played_at": None, "match_url": None,
                "source": "platform_download", "sources": [provenance],
                "patch": None, "engine_version": engine, "replay_format_version": fmt,
                "our_bot": {"collection_label": "v5", "submission_label": submission,
                            "submission_id": None, "git_commit": None, "artifact_sha256": None,
                            "side": ours, "observed_log_banners": banners},
                "opponent": {"team_name": team[1], "team_id": None, "submission_id": None,
                             "elo_at_collection": int(team[2]), "rank_at_collection": None},
                "map": {"name": Path(matches[0][0]).stem if len(matches) == 1 else None,
                        "matching_local_files": [name for name, _ in matches],
                        "sha256": sha(map_data) if map_data else None,
                        "file": f"maps/{sha(map_data)}.map26a" if map_data else None,
                        "serialized_bytes": len(map_data) if map_data else None,
                        "seed": None},
                "draft": {"ours": None, "opponent": None},
                "result": {"status": None, "outcome": None, "our_tributed_gems": None,
                           "opponent_tributed_gems": None, "rounds": None, "termination_reason": None},
                "collection_labels": {"outcome_folder": parts[1], "outcome_scope": "unverified",
                                      "user_reported_series_outcome": "loss"},
                "diagnostics": {"our_crash": None, "our_fuel_exhaustion": None},
                "files": {name: f"matches/{match_id}/{name}" for name in sorted(artifacts)},
                "files_sha256": {name: sha(data) for name, data in sorted(artifacts.items())},
                "files_bytes": {name: len(data) for name, data in sorted(artifacts.items())},
                "replay_sha256": replay_hash, "missing_artifacts": missing,
                "pair_id": None, "dataset_split": "unassigned",
                "leakage_group": group[1],
                "provenance": {
                    "opponent_identity_elo_and_our_side": "source_folder_labels",
                    "engine_and_replay_format": "replay_header; official viewer header layout",
                    "map": "exact embedded bytes matched against local maps" if matches else "unresolved",
                    "submission_label": "user_confirmation" if submission else "unknown",
                    "played_at": "not supplied; filesystem/ZIP timestamps are not match timestamps",
                    "outcome": "not decoded; folder labels may describe a five-game series"
                },
                "validation": {"header_valid": True, "engine_parse_valid": None,
                               "gameplay_replayed": False, "completion_verified": False},
            }
        except (ValueError, KeyError, zipfile.BadZipFile, OSError) as exc:
            rejected.append({"source": str(item.relative_to(source)), "error": str(exc)})
    ordered = sorted(records.values(), key=lambda r: (r["opponent"]["team_name"], r["our_bot"]["side"],
                                                     r["match_group_id"], r["match_index_in_group"]))
    # The official engine loads each recording but never seeks/advances its timeline.
    validation_input = output / "validation-input.json"
    write_json(validation_input, [{"match_id": r["match_id"], "engine_version": r["engine_version"],
                                  "replay": str(output / r["files"]["replay.repl26a"])} for r in ordered])
    subprocess.run(["node", "--no-warnings", str(ROOT / "tools/validate_replay_headers.mjs"),
                    str(validation_input), str(output / "engine-validation.json")], check=True)
    validation = json.loads((output / "engine-validation.json").read_text())
    hashes, groups = defaultdict(list), defaultdict(list)
    for record in ordered:
        hashes[record["replay_sha256"]].append(record)
        groups[record["match_group_id"]].append(record)
    # Keep identical recordings AND all members of a five-game group together
    # in any future split. Splits themselves remain unassigned.
    parents = {r["match_id"]: r["match_id"] for r in ordered}
    def find(key):
        while parents[key] != key:
            parents[key] = parents[parents[key]]
            key = parents[key]
        return key
    for bucket in [*hashes.values(), *groups.values()]:
        leader = bucket[0]["match_id"]
        for record in bucket[1:]:
            a, b = find(leader), find(record["match_id"])
            parents[max(a, b)] = min(a, b)
    for record in ordered:
        record["validation"].update(validation[record["match_id"]])
        if record["map"]["serialized_bytes"] is not None:
            raw = (output / record["files"]["replay.repl26a"]).read_bytes()
            offset = 14 + record["map"]["serialized_bytes"]
            recorded_count = struct.unpack_from("<I", raw, offset)[0]
            record["validation"]["embedded_input_count_matches_engine"] = (
                recorded_count == record["validation"].get("recorded_input_count"))
            if not record["validation"]["embedded_input_count_matches_engine"]:
                raise ValueError(f"Embedded map boundary does not match engine: {record['match_id']}")
        duplicate_ids = sorted(r["match_id"] for r in hashes[record["replay_sha256"]])
        record["deduplication"] = {"replay_content_group": record["replay_sha256"],
                                   "representative_match_id": duplicate_ids[0],
                                   "match_ids_with_identical_replay": duplicate_ids,
                                   "occurrences": len(duplicate_ids)}
        record["leakage_group"] = find(record["match_id"])
        write_json(output / "matches" / record["match_id"] / "metadata.json", record)
    (output / "matches.jsonl").write_text("".join(json.dumps(r) + "\n" for r in ordered))
    columns = ["match_id", "match_group_id", "opponent", "opponent_elo", "our_side", "submission",
               "engine_version", "replay_format_version", "map_name", "map_sha256", "folder_outcome",
               "verified_outcome", "dataset_split", "engine_parse_valid", "replay_path", "metadata_path",
               "replay_sha256", "representative_match_id", "replay_occurrences", "leakage_group"]
    with (output / "matches.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        for r in ordered:
            writer.writerow(dict(zip(columns, [
                r["match_id"], r["match_group_id"], r["opponent"]["team_name"],
                r["opponent"]["elo_at_collection"], r["our_bot"]["side"], submission,
                r["engine_version"], r["replay_format_version"], r["map"]["name"], r["map"]["sha256"],
                r["collection_labels"]["outcome_folder"], r["result"]["outcome"], r["dataset_split"],
                r["validation"]["engine_parse_valid"], r["files"]["replay.repl26a"],
                f'matches/{r["match_id"]}/metadata.json', r["replay_sha256"],
                r["deduplication"]["representative_match_id"], r["deduplication"]["occurrences"],
                r["leakage_group"]])))
    representatives = [r for r in ordered if r["match_id"] == r["deduplication"]["representative_match_id"]]
    (output / "unique-replays.jsonl").write_text("".join(json.dumps(r) + "\n" for r in representatives))
    group_records = [{"match_group_id": key, "match_ids": [r["match_id"] for r in values],
                      "indices": sorted(r["match_index_in_group"] for r in values),
                      "complete_five_match_group": sorted(r["match_index_in_group"] for r in values) == [1,2,3,4,5]}
                     for key, values in sorted(groups.items())]
    after = {str(p.relative_to(source)): sha(p.read_bytes()) for p in source.rglob("*") if p.is_file()}
    if before != after:
        raise RuntimeError("Original collection changed during preparation")
    audit = {
        "source_files": len(files), "source_bytes": sum(p.stat().st_size for p in files),
        "zip_packages": sum(p.suffix == ".zip" for p in candidates),
        "loose_replays": sum(p.suffix == ".repl26a" for p in candidates),
        "unique_match_ids": len(ordered), "match_groups": len(groups),
        "unique_replay_contents": len(hashes), "repeat_replay_occurrences": len(ordered) - len(hashes),
        "unique_maps": len({r["map"]["sha256"] for r in ordered if r["map"]["sha256"]}),
        "leakage_groups": len({r["leakage_group"] for r in ordered}),
        "counts_by_team_and_side": {team: dict(Counter(r["our_bot"]["side"] for r in ordered
                                                     if r["opponent"]["team_name"] == team))
                                    for team in sorted({r["opponent"]["team_name"] for r in ordered})},
        "engine_versions": dict(Counter(r["engine_version"] for r in ordered)),
        "exact_local_map_matches": sum(r["map"]["sha256"] is not None for r in ordered),
        "rejected_packages": rejected, "unexpected_artifacts": extras,
        "missing_artifacts": [{"match_id": r["match_id"], "files": r["missing_artifacts"]}
                              for r in ordered if r["missing_artifacts"]],
        "repeated_match_ids": [r["match_id"] for r in ordered if len(r["sources"]) > 1],
        "identical_replay_groups": [[r["match_id"] for r in bucket] for bucket in hashes.values() if len(bucket) > 1],
        "incomplete_groups": [g for g in group_records if not g["complete_five_match_group"]],
        "engine_parse_failures": [r["match_id"] for r in ordered if not r["validation"]["engine_parse_valid"]],
        "source_hashes_unchanged": True, "gameplay_analysis_performed": False,
    }
    write_json(output / "source-manifest.json", before)
    write_json(output / "groups.json", group_records)
    write_json(output / "audit.json", audit)
    write_json(collection_path, {"schema_version": 1, "source_root": str(source),
                                "prepared_at": recorded_at, "our_submission": submission,
                                "our_submission_provenance": "user_confirmation" if submission else "unknown",
                                "analysis_started": False})
    print(json.dumps({key: (len(value) if isinstance(value, list) else value)
                      for key, value in audit.items()}, indent=2))


if __name__ == "__main__":
    main()
