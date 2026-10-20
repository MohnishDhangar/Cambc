# CAMBC v6: adaptive macro-controller audit and radical-strategy portfolio

Date: 2026-10-21. Baseline: pinned v6.8 source `0ddd5338b94db824f9f53261a17f020490b7017f`.

## Confirmed code behavior (not hypotheses)
1. `bots/Bot6/src/bot.cpp` begins with `V6_MACRO_MODE=1`: fixed economy. The mode-5 branch is unreachable in the pinned competitive executable.
2. `v6_macro_adjust` modifies **camp scores only** inside `select_camp`. It does not schedule banking, map objectives, PvP, altar locks, or coordinated team roles.
3. The **nominal adaptive** mode-5 rule uses round, gold, major and carried-gem flags; two branches return tempo, so it is effectively an early economy/otherwise tempo score selector, not a macro finite-state planner.
4. `draft.cpp` writes `draft_memory` with objective, team-size, distributed, and monolith flags; `bot.cpp` does not consume this payload to execute a role-aware map plan. The bot does recompute an `objective_map` flag at initialization.
5. Camp assignments are exchanged through the 8 match-time shared bytes; this is mutual-exclusion for camp farming, not a team-level strategy coordinator.
6. `V6_BANK_THRESHOLD=0` makes every positive gem bag bank-eligible, and the `bank()` return value preempts farm/defend/siege. Previous independent banking changes regressed versus v4.
7. Roster-only objective patch from `develop/v6.10-objective-roster` tied v6.8 at 21/34 vs v4 and lost the direct comparison 16/34; not promoted.

## Reproducible prior screening and game symptoms
V6.6 macro/bank screen, **same first 8 development maps** at threshold 0: economy 11/16, default utility 10/16, contest 10/16, objective 10/16, tempo 5/16, nominal adaptive 9/16. Chosen economy then validated 10/18 on a disjoint nine development maps, total 21/34 vs v4.
Pinned v6.8: 21/34 vs v4, mean gem margin +91.47, 52 replay fuel-spill events, zero caught exceptions and recorded engine faults. All four v6.8-v4 games with <100 tributed gems were `00contest` (both sides) and `01boss-battle` (both sides), all actually 0. These are **training-map** findings, not final held-out-map tests.

## Genuine alternatives to test (all hypotheses, not validated improvements)

| Profile | Team plan | Theory and target weakness | Primary costs/failure modes |
|---|---|---|---|
| A: Fixed economy | Keep v6.8 control and same fixed draft | Empirical control | Predictable; ineffective vs adversarial interception and difficult objective maps |
| B: Score-aware race / disruption | Public submitted gems drive ECON→TEMPO; nominate a single interceptor of *visible* enemy gem carriers when score near loss | Deny a last enemy tribute while retaining most farmers | Hunter loses farming time; enemy may be unobservable; reactive and too late |
| C: Draft-to-game roles | Encode map playbook in draft memory; allocate per-champion farmer/capturer/banker/escort/raider roles; phase switch with hysteresis | Prevent redundant walking and coordinate 5-round capture phases | Rigid roles, dynamic vision, only 8 live shared bytes |
| D: Objective blitz | Identify major-only sparse maps at draft; draft sustained siege DPS/support; concentrate attackers for one kill, then split capturer vs escort | Specifically address zero-gem contest/boss games | Overcommit to objectives; attrition, powerful monsters; lockstep group routing costs fuel |
| E: Tribute denial | One roaming controller buys 10g altar locks, times placements vs enemy channel and fights low-HP carriers | Disrupt an advanced opponent's gem conversion | Wasted gold/time, lock can be cleared in 3 attacks, poor against dispersed altars |
| F: Territorial counter-jungle | Reserve safe resources for income, contest enemy-side rich camps with a high-mobility raider and a support | Starve opponent of gems; win tempo race without massive PvP | Long unsafe trips, feeding enemies, vision asymmetry |
| G: Tiebreak optimization | If gem race stalls, switch selected champions to safe gold generation (second tiebreak) and kills (third), rather than idle spawns | Win zero-gem, 2000-round maps without brute-force siege | Opponent may find gems; insufficient score evidence if chase |
| H: Risk-aware bankroll logistics | Estimate channel time, camp-to-altar route, opportunity cost, death/lock risk; select group+route+bank as a joint plan | Reduce pointless gem-1 bank trips and altar stagnation | Prior batching heuristics regressed; complicated coupled optimization |

## Test methodology
1. Pin all source and opponent SHA256 hashes; compile with CAMBC 3.0.1. Keep v4/v5 frozen.
2. One independent change/profile per candidate, with unchanged v6.8 plus strong opponents. For each, 17 development maps × both sides (34 vs v4; 34 vs v6.8, ideally replicates or seeds when supported). Use initial search maps vs separate training-validation maps to avoid rewarding lucky 34-game outcomes.
3. Report win/loss, submitted-gem margins and absolute scores, `<100`/zero-submitted games, income/camp captures, 5-round capture occupancy, altar channel cancellations, carries lost to death, deaths, fuel spills, faults, and action/phase frequency.
4. Add a **no-productive-action** counter: state/rule dominated by walking, scouting, recover or shop for >N turns without capture, attack, income or tribute. Diagnose objective-map strategy with a separate early game time series.
5. Test vs frozen v4 and v5, mirrored self-play, and external skill tiers when safe/reproducible; only promote with repeatable gain and no important regression. Do not train/tune on `00lanes`, `01corridors`, `01hooks`, `01islands`, including user-provided replay slices on these maps.

## Live first experiment
The independent `develop/v6.16-score-aware-controller` branch implements profile B as an experimental feature flag on the pinned v6.8 economy engine. A GitHub Actions 102-game paired benchmark tests this. Its existence **does not** establish effectiveness.
