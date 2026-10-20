# CAMBC Bot6 v6.9 — optional scouting fuel-budget guard

Status: **candidate experiment**, not promoted. Branch based on v6.8 commit `0ddd5338b94db824f9f53261a17f020490b7017f`, SDK 3.0.1.

## Hypothesis
v6.8 won 21/34 against frozen v4 and reduced fuel-spill logs from 399 (v6.6) to 52. The 52 residual events were restricted to 01big-world (14) and 01concentrated-wealth (38). Action log labels identify the last reported action, not proof of the costly instruction. v6.6 profiles associated the latter spills with "scout".

Scouting via wards is **optional**; farming, combat, banking, and navigation are not. Guard ward selection until at least 48,000 WASM fuel remains, and refuse the final optional ward action below 16,000. This may avoid expensive end-of-turn work with limited sacrifice in vision. This is a hypothesis, not a tested conclusion.

## Experimental controls
Only `Bot::scout()` and compile-time `V6_SCOUT_FUEL_FLOOR` change. Other Bot6 sources remain byte-identical to pinned v6.8. Frozen v4 archive sha256: `b296e83d43e8b16709e655ee4470a526e9e84160ee02fbad0e8c483661e1a062`.

Pre-registered paired comparisons, 17 training maps x both sides:
- v6.9 vs frozen v4 (34 matches)
- Pinned v6.8 vs frozen v4 (34 matches)
- v6.9 vs pinned v6.8 (34 matches)

Record wins, mean tributed-gem margin, side effects, fuel-spill events, caught exceptions, engine faults and game errors. Complete 102 games; CI success is not sufficient for promotion. Require zero faults and fuel spills and no degradation against v4, plus independent replication before superiority claims.

**Sealed maps excluded:** `00lanes`, `01corridors`, `01hooks`, `01islands` — never used for tuning.

Script: `tools/benchmark_v6_9_scout_budget.py`.
Workflow: `.github/workflows/v6.9-scout-budget.yml`.
Evidence: `match-data/analysis/v6.9-scout-budget/`.

v6.8 stays unchanged for real-opponent testing; field feedback is a separate evidence channel.

## Actual result — REJECTED
102 games completed: 20/34 wins against frozen v4 (v6.8: 21/34), mean gem margin +45.76 (v6.8: +91.47), 46 round-change log events (v6.8: 52), no engine faults or caught exceptions; head-to-head 17/34 against exact v6.8. The guard hurts tournament strength. The legacy log label 'fuel spill' reflects a round-number change during `play_turn`, not a direct fuel meter. Evidence: `match-data/analysis/v6.9-scout-budget/summary.json`. Do not promote.
