# High-Elo collection: prepared data

Preparation only. No gameplay timelines were advanced, no strategy or performance analysis was performed, and no bot changes were made.

Original collection: `../high-elo-teams/`. The requested `higher-elo-teams` path was not present. All original archives and files are preserved; their SHA-256 hashes were checked before and after preparation.

## Inventory

- 500 distinct platform match IDs in 100 complete five-match groups.
- Five opponents: error404 (1820), houseofcoders (1830), pentakill (1845), sssa (1856), hello (1907). Names and Elo are user-supplied folder labels, not independently queried platform records.
- 100 matches per opponent: 50 from side A and 50 from side B, based on folder labels.
- 450 ZIP packages and 50 already-extracted bundles; all contain a replay and the expected own-side stdout, debug, and fuel files. Empty debug files are present artifacts, not missing data.
- Every replay reports engine **1.0.0**, replay format **0.0.3**, and loads in the matching official engine.
- All 500 embedded maps match local map files exactly; 18 distinct map contents are preserved.
- **179 unique replay contents** across 500 match IDs. There are 321 repeated occurrences beyond one representative per content. No original match was removed.

## Files

| Path | Purpose |
| --- | --- |
| `matches.csv` | Spreadsheet-friendly index of all 500 matches |
| `matches.jsonl` | Complete metadata, one JSON object per match |
| `unique-replays.jsonl` | One representative per exact replay hash, with all associated match IDs |
| `matches/<match-id>/metadata.json` | Individual metadata and field provenance |
| `matches/<match-id>/replay.repl26a` and logs | Byte-identical extracted/copied artifacts |
| `maps/<sha256>.map26a` | Exact map bytes matched inside recordings |
| `groups.json` | Five-game group membership and completeness |
| `audit.json` | Integrity, duplicates, missing files, and loader validation audit |
| `source-manifest.json` | SHA-256 of every original source file, keyed relative to the original collection |
| `engine-validation.json` | Official engine parse checks and validator engine hashes |
| `collection.json` | Preparation timestamp and user-confirmed submission label, if supplied |
| `validation-input.json` | Inputs to the non-playing engine validation pass |

Artifact paths in match records are relative to this prepared directory. `sources[].path` and source-manifest paths are relative to the original collection. Validator-engine paths are relative to the repository root.

## Metadata and limits

Each match has `our_bot`, `opponent`, `map`, `draft`, `result`, `diagnostics`, `collection_labels`, `sources`, `validation`, and `deduplication` objects. `files_sha256` and `files_bytes` describe the downloaded artifact bytes.

Missing or unverified values are JSON `null` (blank in CSV). No match date is inferred from file modification time or ZIP timestamps. The preparation timestamp is not the match timestamp.

The collection was described as losses of five-game series, some 1:4. Therefore the folder label is retained in `collection_labels.outcome_folder`; it is **not** assigned to `result.outcome` for individual games. Scores, winners, rounds, drafts, crash/fuel-exhaustion flags, and completion status remain unset pending replay decoding during the later analysis phase.

The logs contain `Bot1 strategy v4 (SDK 2.2.5)`. This is preserved as an observed banner and is not trusted as a submission identifier. The collection's `v5` directory label also does not establish an exact source commit or uploaded artifact. Submission IDs, hashes, patch labels, timestamps, and opponent versions remain unknown unless independently supplied.

`engine_parse_valid` means the official engine accepted the replay bytes. It does not establish that the whole timeline replays correctly or that the match completed. `gameplay_replayed` and `completion_verified` remain false.

## Duplicate handling and future splits

All matches are retained. The lexicographically smallest match ID represents each byte-identical replay in `unique-replays.jsonl`; that choice has no performance meaning. Logs remain separate per match even when replay contents are identical.

`deduplication` includes the replay hash, representative ID, occurrence count, and all matching IDs. Do not count repeat contents as independent learning examples without an explicit weighting decision.

`dataset_split` remains `unassigned`. `leakage_group` joins all matches connected by a common five-game group or identical replay contents, so those records can stay together in later train/evaluation splits. A map or opponent holdout must impose those additional constraints too. `pair_id` stays null: shared maps and opposite sides alone do not prove deliberately paired conditions.

The collection is selected by opponent and user-labelled series outcome. It should not be treated as an unbiased sample of overall ladder performance.

## Reproduce

From the repository root:

```bash
python3 tools/prepare_match_data.py
```

If the user confirms one submission for the entire collection:

```bash
python3 tools/prepare_match_data.py --our-submission 'USER-CONFIRMED-LABEL'
```

Do not supply that option based on the stale log banner. If different submissions were used, record the mapping before assigning per-match labels.

The preparation script uses Python's ZIP CRC verification and SHA-256 hashes, preserves originals, refuses conflicting extracted artifacts, and uses the locally bundled matching WASM engine through `tools/validate_replay_headers.mjs`. It makes no network requests. Existing extracted artifacts must match on rerun; metadata/indexes are regenerated. A previously confirmed collection submission label is preserved when the option is omitted.

Replay header version offsets and magic values follow the official bundled viewer's header decoder. Map identification uses exact embedded bytes, with the input-count boundary cross-checked against the official engine; it does not guess the map from gameplay.
