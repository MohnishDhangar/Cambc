# Bot6 v6.7 — altar tribute reliability

Status: EXPERIMENTAL. The change is implemented, but the advantage is not
established until the paired CI experiment completes successfully.

Parent: 4d38b1b5b9697783d555e76797e1adc78e36637a (v6.6).
V4 and v5 are frozen and unchanged.

## Hypothesis

The v6.6 banking routine can waste turns on a dangerous tribute tile and
manually attack enemy altar locks even though CAMBC 3.0.1 specifies that
attempted tributes automatically attack hostile locks. Improving the altar
decision and fallback behavior may increase safely submitted gems.

Only Bot::bank() differs from v6.6. The complete v6.6 implementation remains
within the V6_SMART_BANK=0 preprocessor branch and is additionally reconstructed
from the exact pinned Git commit for independent control runs. The new path
(V6_SMART_BANK=1) prefers open in-range altars, uses submit_gems on hostile locks,
selects lower-danger tribute squares, and avoids waiting forever if none exists.
All other gameplay including v6.6 macro mode 1, banking threshold 0 and the
Prism/Tavi/Vesper draft is unchanged.

## Fixed benchmark protocol

The workflow v6.7-tribute-benchmark.yml builds release WASM with CAMBC 3.0.1.
It checks the frozen v4 ZIP SHA256, reconstructs the complete original v6.6 bot
from its pinned commit, verifies unchanged auxiliary v6 source files, and runs:

- v6.7 versus frozen v4: 17 training maps x 2 starting sides, 34 games.
- pinned v6.6 versus frozen v4: 17 training maps x 2 sides, 34 games.
- v6.7 versus pinned v6.6: 17 training maps x 2 sides, 34 games.

102 matches total. A fixed map/side grid avoids map-selection bias.
Four HELD-OUT maps are excluded from all testing and tuning:
00lanes, 01corridors, 01hooks, 01islands. Each benchmark checks the existing
17-map manifest before reading the selected map files.

Success gate: compile, zero engine faults, zero caught exceptions and new-bot
fuel spills; improved wins AND banked-gem margin against both v6.6 and frozen
v4; no catastrophic side-specific regression. A further independent
training-map repeat is needed before declaring any repeatable superiority.

Script: tools/benchmark_v6_7_tribute.py.
Workflow: .github/workflows/v6.7-tribute-benchmark.yml.
Output when complete: match-data/analysis/v6.7-tribute-reliability/games.csv
and summary.json. Do not report benchmark success before files exist.
