# v6.9 distance-aware banking (experimental)

## Hypothesis
Pinned v6.8 (21/34 against frozen v4) has `V6_BANK_THRESHOLD=0`: any gems prompt an altar trip, even from far away. On large maps this may squander productive farming time. A healthy, unthreatened carrier more than 12 path steps from an altar should defer banking until carrying at least 8 gems (or until health, proximity, attack pressure, or late-game urgency overrides it). Nearby altars and late rounds use the original behavior.

## Exact change
One compile-time flag and one small block in `Bot::play_turn`, preserving all other game logic and source files from pinned v6.8 commit `0ddd5338b94db824f9f53261a17f020490b7017f`. An exact source-diff assertion runs before build. Never merge this change without positive evidence.

## Pre-registered trial
CAMBC 3.0.1; every one of the 17 unsealed training maps, both sides, 102 matched games: candidate vs frozen v4, exact v6.8 vs frozen v4, candidate vs exact v6.8. Record wins, side splits, tributed-gem margin, faults, exception events and round-crossing diagnostics; require no engine faults and a reproducible improvement in wins and gem margin.

Four held-out maps remain sealed: `00lanes`, `01corridors`, `01hooks`, `01islands`.

Script `tools/benchmark_v6_9_adaptive_bank.py`, workflow `.github/workflows/v6.9-adaptive-bank.yml`.

## Actual result — REJECTED
102 games completed: candidate 20/34 wins against frozen v4 (pinned v6.8: 21/34), mean gem margin +79.09 (v6.8: +91.47), 30 round-change log events (v6.8: 52), no engine faults or caught exceptions; head-to-head 16/34 against exact v6.8. The banking modification did not improve the primary win metric and thus is not promoted. Evidence: `match-data/analysis/v6.9-adaptive-bank/summary.json`. The legacy 'fuel spill' event string counts round-number changes, not confirmed WASM fuel faults.
