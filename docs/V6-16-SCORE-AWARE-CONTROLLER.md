# v6.16: score-aware team policy (experimental)

## Current v6.8 controller limitation
`V6_MACRO_MODE=1` is compile-time fixed economy. Legacy mode 5 is merely a camp-scoring adjustment; previous eight-map screening gave mode5/bank0 9/16 versus fixed economy/bank0 11/16. None of the prior results justify enabling mode 5 unconditionally.

## Pre-registered hypothesis
Use *public, legal* team tributed-gem scoreboard to switch from ECON (baseline economy policy) to TEMPO when the enemy has >=750 submitted gems, or after round 700 when enemy >=350 and leads by >150. Additionally, allow a single designated champion (slot 0) to intercept a visible enemy carrier (>=8 unbanked gems, within 10 tiles), when enemy score >=600, own champion carries none and is healthy. Reserve the other champions for economy. Measure gains in wins and failure of zero-gem games, plus fuel spills. This is a first two-level macro scheduler, not a fully coordinated bot.

## Isolation
Pinned source `0ddd5338b94db824f9f53261a17f020490b7017f`. Guard all new behavior with `V6_SCORE_AWARE_CONTROLLER=1`, retaining original logic under `#if` alternative. Reuse the exact six files, v4 archive SHA, SDK 3.0.1. No v4/v5 changes. Never load `00lanes`, `01corridors`, `01hooks`, `01islands` for tuning. User field replays on held-out/unknown maps are not used for decisions.

## Evaluation
102 matches: candidate vs frozen v4, pinned v6.8 vs frozen v4, candidate vs pinned v6.8, 17 development maps, both teams/sides. Report win rate, submitted-gem margin, zero-tribute games, number and contexts of triggers in a subsequent telemetry experiment, runtime faults, replay fuel spills. Preserve output whether accepted or rejected. Competitive upgrade only if reproducible advantage and reliability criteria achieved.

## Measured result (CI run 39513192436, completed)

- Candidate v6.16 vs frozen v4: **21/34 wins**, mean submitted-gem margin **+98.09**, 59 fuel-spill events, zero engine faults/exceptions.
- Pinned v6.8 vs frozen v4: **21/34 wins**, mean margin **+91.47**, 52 fuel-spill events, zero engine faults/exceptions.
- Candidate v6.16 vs pinned v6.8: **18/34 wins**, mean margin **−17.29**, 61 fuel-spill events.
- All four original under-100 (actually 0) tribute matches on `00contest` and `01boss-battle` remain zero in the candidate's controlled v4 games.
- **Verdict: DO NOT PROMOTE**. Equal v4 win count, +7 spill events, not superior in direct games by mean gem margin. In addition, activation counts for ECON/TEMPO/interceptor are not yet instrumented; cannot claim all new branches were frequently exercised.
- Reproducible evidence: `match-data/analysis/v6.16-score-aware/summary.json` and `games.csv` in this branch, CI https://github.com/MohnishDhangar/Cambc/actions/runs/39513192436.
