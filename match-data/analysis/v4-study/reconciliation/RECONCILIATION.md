# Reconciled v4 match labels

Generated from the existing 245 engine-0.0.3 replay reconstructions.
No replay files were changed or moved.

- Analyzed matches: **245**
- Team A identity: **245** verified v4 stdout markers, **0** unverified/missing.
- Original score-comparison discrepancies: **44**.
- Engine-outcome folder discrepancies: **46**.
- Replays needing manual outcome verification: **0**.
- True v4 engine wins in this selected dataset: **62**.
- True v4 engine losses in this selected dataset: **183**.

## Method

Engine outcome enum is inferred and checked against all decisive (non-tied) scores: 1 = Team A, 2 = Team B.
When scores tie, engine outcome is authoritative; a tie is not necessarily a draw.
Team A is verified against `team-a.stdout` within each match folder.
The original `category` retains the opponent Elo tier, but analyses should use the corrected result column rather than the folder's wins/losses directory.
Matched replays are anchored by their original `path` and SHA-256. This dataset is selected, not a random lobby sample.

## Counts by folder

| Original folder | Correct | Incorrect |
|---|---:|---:|
| higher-elo/losses | 111 | 9 |
| same-elo/losses | 55 | 20 |
| same-elo/wins | 33 | 17 |

A full per-match manifest is in [manifest-provisional.csv](manifest-provisional.csv).
