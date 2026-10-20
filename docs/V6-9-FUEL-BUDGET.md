# v6.9: guarded fuel budget (experimental)

## Hypothesis
The 52 v6.8 fuel-spill events in 34 games versus frozen v4 are mostly late navigation and ward execution. Raising per-turn minimum fuel from 18,000 to 32,000 before navigation and from 16,000 to 32,000 before scouting should prevent some exhaustion without substantially reducing wins.

## Isolation
Preserve v6.8 commit `0ddd5338b94db824f9f53261a17f020490b7017f` as pinned control. Change only two guard thresholds, independently feature-flagged with `V6_FUEL_BUDGET_GUARD`. Unmodified v4/v5. The four reserved maps `00lanes`, `01corridors`, `01hooks`, `01islands` must not be opened in tuning runs.

## Test
CAMBC 3.0.1; 17 development maps, A/B sides, 34 games each v6.9 vs v4, pinned v6.8 vs v4, v6.9 vs pinned v6.8, total 102. Compare win counts, tribute margins, replay fuel spills, exceptions, and faults. **Only promote after verified run and improved performance without unacceptable regressions.**

## State
Source patch submitted; CI evidence will determine acceptance or rejection. v6.8 remains the separate field-test bot.

## Actual result — REJECTED
The completed, pinned 102-game tournament reported 21/34 wins vs v4 (unchanged from v6.8), 85.68 mean gem margin (v6.8: 91.47), 47 round-change diagnostic log events (v6.8: 52), no engine faults or caught errors, and 17/34 head-to-head against v6.8. No convincing competitive improvement. See `match-data/analysis/v6.9-fuel-budget/summary.json`. These logged events are round-number changes during `play_turn`, not direct WASM fuel-fault measurements. Do not promote.
