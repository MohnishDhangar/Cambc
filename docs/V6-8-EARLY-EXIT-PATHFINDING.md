# Bot6 v6.8 — target-limited pathfinding experiment

Status: CANDIDATE. Do not promote on build success; independent wins and
fuel-spill evidence determine whether the change is accepted.

## Diagnosis from pinned v6.6

In the six-game diagnostic (research/v6-fuel-spill-diagnostics-20261021),
399 fuel-spill log events were classified as 347 "navigate walk",
49 "scout", and 3 "navigate crystal". All navigation-walk incidents
were on the large training map 01big-world. These event labels are the
last reported actions, not exclusive attribution of fuel cost.

## One-variable hypothesis

CAMBC SDK 3.0.1 distance_field::compute always explores the complete
reachable map even when the bot only needs the distance gradient between
a goal and its current position. distance_field::compute_to can terminate
once the start tile is reached. Every strictly downhill movement candidate
has already been discovered by then, so a navigation action can follow
the same shortest-path gradient while consuming less WASM fuel.

Only Bot::navigate changes. Normal pathfinding uses compute_to with the
bot's current tile as destination. Escape keeps complete traversal to
preserve evasive paths temporarily moving away from the goal.
V6_EARLY_EXIT_PATH=0 restores the exact previous navigation logic.
The source inherited from pinned commit 4d38b1b5b9697783d555e76797e1adc78e36637a
is otherwise unchanged; the regression in v6.7 banking was NOT carried over.

## Pre-registered test

Build CAMBC 3.0.1 release WASM and run across all 17 unsealed training maps,
both sides, 34 games each:
- v6.8 versus frozen v4
- exact pinned v6.6 versus frozen v4
- v6.8 versus exact pinned v6.6

102 matches in a matched map/side grid. The script reconstructs both
historical sources and checks sha256 hashes. Record win count, gem
submission margin, fault/exception totals, fuel spills and side imbalance.
Any exception or remaining fuel spill blocks release promotion, even when
CI completes successfully. The four held-out maps (00lanes, 01corridors,
01hooks, 01islands) remain untouched.

Script: tools/benchmark_v6_8_navigation.py
Workflow: .github/workflows/v6.8-navigation-benchmark.yml
Expected report: match-data/analysis/v6.8-navigation-bfs/summary.json

No conclusions are claimed until the test completes and results are inspected.
