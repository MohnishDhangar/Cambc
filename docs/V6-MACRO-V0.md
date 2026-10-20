# Bot6 v6.0 — experimental macro-strategy foundation

**Status:** First modular implementation. **Not yet a competitive replacement for v4.** Do not promote it on compilation alone.

## Frozen baselines

V4 and V5 are archived read-only at the exact refs and hashes in [FROZEN-V4-V5.md](FROZEN-V4-V5.md). Bot6 lives in `bots/Bot6/src/` and does not alter Bot1 files. All tests against prior versions reconstruct frozen artifacts into temporary `Bot4Frozen` / `Bot5Frozen` directories.

## Architecture

1. Draft composition is map-contextual, using real group size/health and map shape; it no longer assumes Ren/Varg/Vendetta are always the best composition.
2. The **macro controller** chooses among 5 strategy families: economic snowball (`economy`), bankable-gem throughput (`tempo_farm`), opportunistic enemy-carrier pressure (`contest`), large-objective control (`objective`) and runtime switching (`adaptive`).
3. **Team assignment** reserves current camp objectives through eight shared-memory bytes and discounts duplicate claims. This is a distributed *greedy approximation*, not yet a full team-wide auction.
4. The **tactical executor** handles spell selection and normal attacks, pathfinding with known-obstacle filtering, bank/recover behavior, scouting, and engine-action exceptions.
5. A compact `v6 macro` log event is emitted every 100 rounds by the first champion for reproducible behavioral inspection.

The policy is deterministic and exposes separated heuristic parameters in `Bot::Params`. No machine-learning weights are trained yet. Avoid treating ad-hoc numbers as proven optima.

### Fixed-mode ablation support

By default `V6_DEFAULT_MACRO=4` enables adaptive switching. To build a fixed mode, add a C++ compiler definition before compiling:
- `0` economy
- `1` tempo farming
- `2` contest
- `3` objective
- `4` adaptive (default)

The macro selector is under `Bot::macro_mode` in `bot.cpp`; controlled variant builds can pass `-DV6_DEFAULT_MACRO=N`. Only export a final ZIP when that choice is tracked in a source hash and tested; do not silently alter source flags before submission.

## Build and smoke tests

The project is pinned to CAMBC/SDK **3.0.1**, not 2.2.5.

```bash
cambc --version
cambc build Bot6 --release
python3 tools/build_v6_map_split.py
python3 tools/test_bot6.py --opponents starter-cpp --maps 00ambush 00contest 01gold-rush --output replays/v6-local
python3 tools/package_bot6.py
```

Only the **17 training maps** from `match-data/analysis/v6-elite-research/v6-map-split.json` may be used for development or tuning. The withheld maps `00lanes`, `01corridors`, `01hooks`, `01islands` must remain unseen through development, including smoke testing.

The CI workflow `.github/workflows/v6-build-test.yml` restores v4/v5 from pinned frozen references, builds all bots with 3.0.1, tests v6 from both sides against starter, frozen v4 and frozen v5, checks bot errors, then packages the **six-file source ZIP** to `submissions/Bot6-v6.0-macro.zip`.

### How to interpret results

This is a new strategy architecture, **not trained nor optimized**. A successful compile and completed match indicates engine compatibility only. Win rate, gem scores, and zero-fault behavior against diverse opponents must determine any upgrade. A weak v6.0 is still a useful experimental foundation if it produces stable modular experiments.

The first two priorities after the baseline release are: (1) state-aware zero-command-turn diagnosis and team-level assignment, (2) Bayesian/evolutionary comparisons among five fixed macro modes on training maps. Only after this should we attempt adaptive policy learning and final withheld-map evaluation.

## First verified run — 21 October 2026

**Test evidence:** https://github.com/MohnishDhangar/Cambc/actions/runs/39489048624

The current-client CI runner installed CAMBC **3.0.1**, initialized its SDK, and release-compiled Bot6, frozen Bot4, frozen Bot5 and starter-cpp. All 14 non-held-out test matches completed, with **zero Bot6 engine faults and zero logged Bot6 exceptions**. The paired test suite used both starting sides.

| Opponent | Maps | Games | V6 wins | Notes |
|---|---|---:|---:|---|
| starter-cpp | `00ambush`, `00contest`, `01gold-rush` | 6 | 4 | Lost both Ambush starts |
| Bot4Frozen | `00ambush`, `00contest`, `01gold-rush` | 6 | 0 | 00contest ties in submitted gems still resulted in losses on tiebreaks |
| Bot5Frozen | `00ambush` | 2 | 0 | Lost both starts |

**Therefore v6.0 does not outperform the frozen baseline.** It is a modular candidate framework for phase-two strategy development, not a promoted tournament entry. The default bank threshold was lowered from 22 to 8 in one recorded experiment, but **this did not improve wins** in the matched suite (4/6 against starter; 0/6 against v4; 0/2 against v5). These settings are experimental and should be optimized with more representative scoring/risk telemetry.

### Reproducible source archive

`submissions/Bot6-v6.0-macro.zip` is exactly six source files immediately inside `src/`. Its SHA256 is `7e83559ad08617e1c390363297e1c6eaafef053f3170802df2e9dd8a8ac2182d`, with per-file SHA256 values in `submissions/Bot6-v6.0-macro.manifest.json`. A compiled WASM was also uploaded as a GitHub Actions artifact, but the CAMBC website expects the **source ZIP**.

### Next phase — diagnosed performance, not blind parameter tweaking

The highest-priority problems to investigate are repeated low/zero successful gem submissions on `00ambush`, insufficient objective turnover versus v4, and lack of a proper task-assignment auction and sustained action planning. Decode state transitions from current-engine match replays before changing several policy variables. Do not touch four held-out maps.
