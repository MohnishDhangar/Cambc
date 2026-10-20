# v6.10 — Altar progress experiment

## Field evidence (uploaded real-opponent replays, private)
The user provided ZIPs with 24 unique v6.8 and 25 unique v6.9 replay recordings (v6.8 also contained one duplicate game-group export). Both replays and fuel/stdout streams were read offline. On the v6.8 side, 35 fuel-spill diagnostics occurred across four games: 15 navigation walk, 14 scout, 5 initialize, 1 crystal. On v6.9, 36 spill diagnostics across five games: 28 navigation walk, 2 scout, 5 initialize, 1 crystal. Fifteen replay files are byte-for-byte identical across the versions. These data do not by themselves provide team score/winner without replaying through the matching engine. The uploaded replays are not committed; no held-out map data is used to optimize.

## Source-level bottleneck, independent of maps
In pinned v6.8, `bank()` checked danger before calling `submit_gems` at an altar. If danger was above the cutoff, it invoked `navigate(goals)` where `goals` includes the current tile, so navigation returned false, and `bank()` returned true. The policy could repeat without moving, fighting, or tributing. The game rules state that damage does not cancel tribute (only stun, death, lock), and submitting against enemy lock attacks lock automatically.

## Change and hypothesis
Introduce `V6_ALTAR_PROGRESS=1` at a valid adjacent altar, call `submit_gems` unconditionally and exit; old path preserved under `#else`. All other v6.8 behavior retained. Hypothesis: prevent indefinite missed tributes at contested altars, possibly improve real-opponent results. Risk: enemies can kill or stun channeling carriers, worsening some matches.

## Controlled test
Pinned v6.8 control commit `0ddd5338b94db824f9f53261a17f020490b7017f`, frozen v4 SHA256 `b296e83d43e8b16709e655ee4470a526e9e84160ee02fbad0e8c483661e1a062`. 102 games total across the existing 17 development maps, both starting sides, three pairings (v6.10 vs v4, v6.8 vs v4, v6.10 vs v6.8). Zero held-out maps: 00lanes, 01corridors, 01hooks, 01islands. Evidence will be in `match-data/analysis/v6.10-altar-progress/`. A successful CI build alone does not mean improved competitive performance.
