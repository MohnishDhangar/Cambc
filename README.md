# Cambridge Battlecode: Bot1

A playable C++ bot for the bundled CAMBC 2026 SDK (`2.2.5`). The implementation is in `bots/Bot1/src/`; `bots/starter-cpp/` is the comparison opponent.

**Current release: [Bot1-v4.zip](bots/Bot1/Bot1-v4.zip).** V4 keeps v1's ordinary-map farming core, elects one capture recipient while helpers move on, and uses equipped ranged casters for monoliths and large elk objectives. It was checked in 102 complete local games: **19/34 against frozen v1, 32/34 against frozen v3, and 34/34 against the starter**, with zero fuel exhaustion, caught errors, or bot faults. See the [v4 evaluation](replays/v4-release-evaluation/REPORT.md) and [strategy](bots/Bot1/STRATEGY.md).

V1/v2/v3 ZIPs and WASMs remain historical artifacts. V2 had runtime and strategy regressions; v3 reduced deaths but underperformed in the [paired platform analysis against lll](match-data/analysis/paired-v1-v3/REPORT.md). Those recordings informed v4; the local results do not establish a win rate against lll. The [offline explorer](match-data/analysis/paired-v1-v3/explorer.html) retains the opponent analysis.

## Updated client

The project client is CAMBC `2.2.5`, with replay engines `0.0.1`, `0.0.2`, and `0.0.3`. Enable it in a Bash terminal:

```bash
cd /home/mohnish/Y
source tools/activate-cambc.sh
cambc --version
```

Alternatively, use `./tools/cambc` directly. The wrapper keeps the client's asset cache under `.cambc/cache`. SDK initialization is complete; map downloads were skipped because this environment cannot resolve download hosts. Existing maps and the maps embedded in uploaded replays remain available. Run `cambc maps pull` when connected to refresh the published pool.

The pre-update SDK, configuration, maps, and bots are backed up in `.cambc/before-client-2.2.5.tar.gz`. The original bot artifacts are preserved as `bots/Bot1/Bot1-v1.zip` and `Bot1-v1.wasm`. The source from before v2 is backed up in `.cambc/Bot1-before-strategy-v2.tar.gz`; v2 is backed up in `.cambc/Bot1-before-v3.tar.gz`.

## Play a match

Run from this directory:

```bash
cambc build Bot1 --release --output bots/Bot1/Bot1-v4.wasm
cambc run Bot1 starter-cpp --release --map lanes --view
```

To save completed match statistics:

```bash
cambc run Bot1 starter-cpp --release --map lanes \
  --out-dir replays/my-match --statistics replays/my-match.json
```

Open an existing replay with `cambc view path/to/match.repl26a`. A short `--rounds` run may finish without a winner; omit that option to play a complete game.

## Strategy

Ordinary maps keep Tavi/Varg/Vendetta farming, with Ryth and Vesper Vale where team size permits. Participants clear camps together when useful, then elect a nearby recipient using equipment investment and distance. Helpers leave the capture region and resume work.

On maps where every gem group is a major objective, Focus casters farm equipment before using firing positions outside monster attack range. This includes both monoliths and large non-monolith groups. The exact spell-distance calculation matters: targeted spell range is Euclidean, while monster attacks use Chebyshev distance. Monster threat tracking uses actual awake state.

See [the strategy notes](bots/Bot1/STRATEGY.md) for the draft, purchases, decision flow, measured results, and known weaknesses.

## Original v1 local results

Under the previous CLI `2.1.6` / engine `0.0.1`, the final implementation won **18/18 completed matches against `starter-cpp`**, playing both sides on all nine local maps at the default fuel budget. Replay logs contained **zero caught bot errors, zero crashes, and zero fuel overruns**. Wins took 291–623 rounds. This sweep has not been repeated with the updated engine.

| Map | Bot1 as A: gems | Bot1 as B: gems |
| --- | --- | --- |
| collision | 1024–176 | 1002–286 |
| corners | 1032–58 | 1002–36 |
| elkring | 1008–306 | 1008–234 |
| expanse | 1020–394 | 1034–390 |
| interlock | 1018–368 | 1022–276 |
| lanes | 1024–564 | 1026–576 |
| monolith | 1010–220 | 1004–168 |
| packs | 1000–268 | 1032–132 |
| rows | 1056–396 | 1023–429 |

Scores list Bot1 first. The machine-readable report and replay paths are in `replays/Bot1-evaluation-final/summary.json`. Two additional completed self-play games on `interlock` and `elkring` also had no errors, crashes, or fuel overruns. These checks establish a working baseline against the local starter; they do not measure strength against competition submissions.

Reproduce the map sweep:

```bash
python3 bots/Bot1/scripts/evaluate.py
```

Use `--maps lanes packs` for selected maps, `--opponent NAME` for another local bot, and `--jobs 3` for concurrent matches. Results go under `replays/Bot1-evaluation/` by default. The script exits unsuccessfully if a match fails or Bot1 logs an error, crashes, or exceeds a turn's fuel budget.

## Package source

```bash
cambc bundle Bot1 --output bots/Bot1/Bot1-v3.zip
```

The candidate source archive is [Bot1-v3.zip](bots/Bot1/Bot1-v3.zip). The command requires a fresh output path if that archive already exists. The supplied v3 platform results are documented in the paired analysis above. Its compiled candidate is `bots/Bot1/Bot1-v3.wasm`; existing v1/v2 artifacts remain preserved.
