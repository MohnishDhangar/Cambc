# v5 live replay audit — initial evidence

Source: `match-data/v5/similar-elo-teams` on GitHub main, archived on 20 Oct 2026.

- Complete replay folders: **55**, with **50 unique replay hashes**.
- Folder labels: **45 losses**, **10 wins**. **Not engine-verified:** previous v4 labels were wrong in some matches.
- Recorded v5 team side: **45 Team A**, **10 Team B**; a cross-tab is below.
- Bot stdout identity markers: **55/55**.
- Identical replay-content duplicate groups: **5**, excess folders: **5**. These are repeated observations, not independent games.
- Replay engine header bytes: `{'010000000003': 55}` (header alone does not validate game scores or outcomes).
- 'fuel spill at' stdout messages: **284** across **10** matches.
- 'bot error' stdout lines: **5** across **5** matches.

## Folder category and observed side

| Folder result | Bot team A | Bot team B |
|---|---:|---:|
| wins | 5 | 5 |
| losses | 40 | 5 |

## Duplicate replay contents

| SHA-256 prefix | Folder paths |
|---|---|
| \`b99d3a73d183\` | \`losses/team-8/01-0f78505e-4fd4-4bc8-8561-39080a4e1c50\`, \`wins/team-1/01-0f78505e-4fd4-4bc8-8561-39080a4e1c50\` |
| \`9093a817207b\` | \`losses/team-8/02-27ada525-e2f3-4174-837a-892118bfb65c\`, \`wins/team-1/02-27ada525-e2f3-4174-837a-892118bfb65c\` |
| \`e49e378009a4\` | \`losses/team-8/03-ac4e0ffa-d53c-4822-91fc-35b765967381\`, \`wins/team-1/03-ac4e0ffa-d53c-4822-91fc-35b765967381\` |
| \`1cb7b9cdc008\` | \`losses/team-8/04-52d7865b-0cc2-4fbb-9f57-c21fd2943997\`, \`wins/team-1/04-52d7865b-0cc2-4fbb-9f57-c21fd2943997\` |
| \`9ea90373332b\` | \`losses/team-8/05-5d8d234c-2973-46bb-b22c-f4b075a441db\`, \`wins/team-1/05-5d8d234c-2973-46bb-b22c-f4b075a441db\` |

## Qualification

Folder results are provisional until reconciled with official server winner or matching replay decoder. Each match uses whichever of `team-a.stdout` or `team-b.stdout` is present, to avoid assuming Bot1 is always Team A. A printed `fuel spill at` message is a bot diagnostic; **it is not by itself proof of an engine-reported fault**. Inspect full replay and fuel trace to determine any performance impact.

## Most diagnostic logs

| Labeled result | Match | Spill messages | First spill round |
|---|---|---:|---:|
| losses | `team-8/02-27ada525-e2f3-4174-837a-892118bfb65c` | 69 | 2 |
| wins | `team-1/02-27ada525-e2f3-4174-837a-892118bfb65c` | 69 | 2 |
| losses | `team-1/02-ed3322a6-a6c3-42ac-9b4d-ed4b3b9d5ccd` | 39 | 2 |
| wins | `team-2/01-e5cb7039-8904-406d-9b91-7cb80be092a1` | 34 | 2 |
| losses | `team-2/01-332bc691-d8b9-4f03-9066-cecef0ffe6fe` | 30 | 2 |
| losses | `team-6/03-f31d25ab-6797-4a1e-b936-92c16e782685` | 16 | 2 |
| losses | `team-4/02-373d67be-6765-41fb-a413-09cf712797f4` | 12 | 668 |
| losses | `team-3/04-4e3a1037-5553-4e60-ad50-cf3a040112f5` | 5 | 1 |
| losses | `team-4/05-18e09de6-c327-4efb-87ff-54ccde9321d3` | 5 | 1 |
| losses | `team-9/04-2e34c63c-d707-4196-bbf2-89bf910ffb82` | 5 | 1 |

## Follow-up

1. Verify 55 outcomes from the official result or engine timeline, as was necessary for v4.
2. Analyze replays at champion-turn resolution for draft balance, score checkpoints, camp selection and coordination.
3. Validate fuel diagnostic significance before changing bot code.
4. Stratify by map and opponent group; wins/losses are selected data, not an unbiased win-rate estimate.
