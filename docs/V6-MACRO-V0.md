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
