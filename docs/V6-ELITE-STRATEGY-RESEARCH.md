# V6 Research Memo — Elite Opponent Diagnostics and Strategy Search Space

**Status:** Phase 1 completed: recording audit and action-stream analysis. Phase 2 (state/outcome decoding and causal match analysis) not yet completed. No v6 bot candidate has been implemented or tested.

**Repository:** `MohnishDhangar/Cambc`, branch `research/v6-elite-strategy-audit`.

## 1. Source integrity, provenance, and leakage

- Source collection: `match-data/v5/high-elo-teams`; preparation: `match-data/v5/prepared-high-elo`.
- **The submitted bot in these matches is v4**, explicitly confirmed in the prepared dataset's `collection.json` and corroborated by the `Bot1 strategy v4` stdout marker in all 179 distinct replay representatives. The directory's `v5` label is organizational.
- 500 distinct match IDs, 100 complete five-game groups, five named opponents, each 100 records (50 labeled side A, 50 side B).
- 179 distinct replay byte strings, 321 repeated occurrences. Do not use 500 as the number of independent demonstrations.
- All 500 records identify engine 1.0.0, replay format 0.0.3; previous preparation verified header parsing with matching official engine, but it did *not* advance gameplay.
- The new action-stream decoder parses **179/179** distinct replays, consuming exactly the recorded action count with no remainder or decoding failures. `tools/probe_v6_elite_actions.py` validates record layout; `tools/analyze_v6_elite_actions.py` attributes commands to Team A/B by documented alternating champion-turn ordering.
- Among distinct replays: our v4 was side A in 95 and side B in 84.
- Crucial: **0/500 individual match outcomes are verified**. Folder labels such as `losses` describe selected five-game series, not individual match outcomes. Neither final scores nor victory causes have been computed. Do not publish a win rate from them.
- 21 local map files exist, 18 are represented in the match data. The wholly absent maps are `00lanes`, `01corridors`, `01hooks`. The intended **five held-out map names have not been specified**, so neither training nor model selection should touch unassigned map-specific measurements. `01islands` appears once and must be handled separately.
- Prepared collection reports 11 connected leakage groups across 100 five-game groups when linked by repeated replay bytes. Do not randomly split individual match rows. For strict map holdout, remove every observation from held-out map names; also ensure a five-game bundle/repeated replay cluster cannot straddle training and validation groups, dropping conflicted training records if necessary.
- Relative metrics below reflect deduplicated **unique replay contents**, not independent random ladder samples. The archived matches may be highly selected and correlated.

## 2. Observed action gaps (not successful actions)

The following table reports mean *attempted* commands per distinct replay. Our-vs-elite match duration is identical in turns by construction of alternation; individual games can have different lengths.

| Metric | v4 | Elite | Interpretation |
|---|---:|---:|---|
| Move | 2833.2 | 3336.3 | +17.8% elite commands |
| Attack champion | 77.7 | 113.0 | +45.6% elite targeted attacks |
| Attack camp | 725.2 | 879.4 | +21.3% elite attacks |
| Cast | 355.9 | 429.0 | +20.5% elite casts |
| Buy item | 117.0 | 173.8 | +48.6% elite purchase commands |
| Recall | 32.9 | 51.7 | +57.2% elite recalls |
| Tribute | 27.1 | 31.3 | +15.5% elite tribute commands |
| Ward | 107.0 | 217.8 | +103.7% elite ward commands |
| No recorded commands / champion turns | 2282.7 / 5868.2 | 1524.0 / 5867.9 | 38.9% v4, 26.0% elite |

**What this does not prove:** commands succeeded; champions were able to act; items were obtained; gems were successfully tributed; early teamfights were won; maximizing command count yields higher scores. No-command turns may reflect death, channeling or other valid constraints.

### Opening, rounds 1–200

| Metric | v4 | Elite |
|---|---:|---:|
| Move | 472.2 | 517.8 |
| Champion-targeted attack | 16.6 | 27.8 |
| Camp-targeted attack | 171.6 | 171.4 |
| Cast | 74.1 | 80.2 |
| Buy | 11.2 | 13.5 |
| Recall | 5.6 | 7.6 |
| Tribute | 2.84 | 2.84 |
| Ward | 18.3 | 33.7 |

The camp-attack counts are almost equal in the opening, while opponent champion-targeted attacks and ward actions are higher. This is a *hypothesis-generating* signal to study early engagements, territory and vision; no causal claims.

### Different opponent styles exist

Mean counts across a distinct replay:

| Elite | Unique games | Elite vs our v4: move | Elite vs v4: champion attacks | Elite vs v4: buys | Elite vs v4: wards |
|---|---:|---|---|---|---|
| Error404 | 35 | 3279 / 3152 | 111 / 95 | 103 / 137 | 192 / 134 |
| Hello | 34 | 3326 / 2462 | 119 / 39 | 77 / 113 | 187 / 45 |
| HouseOfCoders | 33 | 3037 / 2839 | 131 / 122 | 102 / 106 | 303 / 239 |
| Pentakill | 43 | 3743 / 2589 | 126 / 60 | 413 / 112 | 291 / 39 |
| SSSA | 34 | 3181 / 3180 | 75 / 78 | 111 / 118 | 100 / 98 |

**Very important:** Pentakill makes many more purchase/ward commands; Error404 and Hello issue *fewer purchase commands* than our v4, while SSSA's actions are strikingly similar to ours. Do not design one generic "elite strategy" from the all-opponent averages. Different teams may win through completely different mechanisms, or command counts may include failed/repeated attempts.

Draft indices follow the archived engine's 0–11 roster: Ryth 0, Vesper Vale 1, Vendetta 2, Cassi 3, Issac 4, Stellar 5, Prism 6, Marcella 7, Willow 8, Ren 9, Varg 10, Tavi 11. These are *observed picks*, not proof of champion win rates. Our v4 selected Ren and Varg in **179/179** unique games, Vendetta in 169/179. Elite drafts differed considerably, e.g. Pentakill selected Issac and Tavi in 43/43, Varg in 38/43. Opponent selection is confounded by maps, draft sizes and team strategies.

## 3. A broad, testable strategy portfolio

Every proposal below is a candidate experiment, **not an experimentally established best practice**. Each must become a configurable policy with its own metrics and ablation. The objective is gem *tributed*, not merely camp damage or gold collected.

### Draft and composition (D)

| ID | Alternative policies / features |
|---|---|
| D1 | Terrain-aware champion roster: mobility on fragmented maps, long range on siege maps, sustain on large jungle maps |
| D2 | Optimize complementarity: burst+CC for ganks vs 3 farming specialists vs mixed escort/banker |
| D3 | Adapt drafting to enemy visible selections; mitigate enemy melee/ranged counters |
| D4 | Value extra team utility: passive gold/gems, attack resets, mobility, AoE camps, shield/support |
| D5 | Estimate roster time-to-first-tribute rather than standalone champion DPS |
| D6 | Optimize joint draft + initial task assignment, rather than draft with no opening plan |

### Camp and objective economy (J)

| ID | Alternative policies / features |
|---|---|
| J1 | Fastest-safe-first camp routing (gem-throughput objective) |
| J2 | Gold-first opening until a learned item power spike, then gem farming |
| J3 | Counter-jungle vulnerable high-value camps with escape-route constraints |
| J4 | Prioritize objectives by *expected bankable gems*, incorporating death and delivery risk |
| J5 | Jointly route champions through low-travel camp clusters (orienteering/vehicle routing) |
| J6 | Spawn-timer scheduling to arrive just before high-reward camp respawns |
| J7 | Contest vs avoid choices based on local enemy numbers and likely arrival |
| J8 | Large-camp siege assignment (specialized caster + protective champion vs independent farming) |

### Combat and tactical choices (C)

| ID | Alternative policies / features |
|---|---|
| C1 | Gank isolated gem carriers when estimated kill/deny probability warrants it |
| C2 | Fight only for objectives, gem recovery or superior local numbers; otherwise disengage |
| C3 | Coordinated focus fire and CC chain timing |
| C4 | Target priority combining estimated time-to-kill, carried gems and threat |
| C5 | Kite ranged champions while preserving attack/cast allowance constraints |
| C6 | Retreat based on predicted incoming multi-turn damage, not fixed HP alone |
| C7 | Intercept retreating/enemy banking carriers near altars |
| C8 | Spell/attack planning: maximize damage per turn with cooldown and exclusivity constraints |

### Banking, safety and game phases (B)

| ID | Alternative policies / features |
|---|---|
| B1 | Dynamic tribute trigger by carried gems, map distance, danger, team score and game round |
| B2 | Escort high-value carriers and discourage redundant altar clustering |
| B3 | Risk-sensitive altar choice and safe routing |
| B4 | Opportunistic micro-tribute vs fewer large deliveries (time cost vs drop risk) |
| B5 | Deny opponent tribute through interception/altar lock only when opportunity cost is positive |
| B6 | Endgame mode switch: exploit score lead, force combat from behind, optimize tiebreaks |

### Economy and shopping (E)

| ID | Alternative policies / features |
|---|---|
| E1 | Item purchase schedule conditioned on the next intended camp and champion |
| E2 | Optimize recall-for-shop versus continuing farming |
| E3 | Health/defense purchases to reduce lost carried gems and death downtime |
| E4 | Power-spike thresholds: buy after a specific gold amount or imminent fight |
| E5 | Adaptive strength/focus/sustain build per draft role and patch |
| E6 | Optimize consumable economics (TP, scouting, safety) |
| E7 | Gold investment versus gem throughput switching after modeled payback time |

### Team coordination (T)

| ID | Alternative policies / features |
|---|---|
| T1 | Auction/task assignment: champions bid by time, capability, gem value and risk |
| T2 | Split farming versus 2+1 or 3+2 objective grouping according to local advantage |
| T3 | Persistent team roles: farmer, contest, escort, banker, with dynamic reassignment |
| T4 | Shared target reservation to avoid multiple champions chasing the same small camp |
| T5 | Shared target and sighting memory to exploit enemy information without omniscience |
| T6 | Synchronize ganks and disengagements by expected arrival round |
| T7 | Champion action-priority scheduling to create effective combined turns |

### Vision and information (V)

| ID | Alternative policies / features |
|---|---|
| V1 | Ward contested chokepoints instead of placing when convenient |
| V2 | Enemy threat belief map that ages last-seen positions over time |
| V3 | Information-value-driven scouting only if it changes the next strategic decision |
| V4 | Track visible enemy carried gems and estimate probable altar approach |
| V5 | Opponent archetype classifier to adapt the macro policy during a match |

### Search and learning (L)

| ID | Alternative policies / features |
|---|---|
| L1 | Tunable baseline: optimize 10–20 interpretable parameters without structural change |
| L2 | Search over macro archetypes (farm, contest, escort, raid, siege) via controlled tournaments |
| L3 | Contextual bandit or small tree predicting best objective class from observable state |
| L4 | Learned estimated time-to-clear and damage for each champ/camp/build combination |
| L5 | Bayesian risk model for carrier death before successful tribute |
| L6 | Self-play population with multiple policy archetypes, if patched offline engine is available |
| L7 | Lightweight planning/MCTS for combat at decision points, subject to SDK fuel limits |
| L8 | Distill offline optimizer into compact C++ tables / small trees; avoid network/runtime inference |

## 4. Prioritize experiments by evidence and implementation cost

| Rank | Experiment | Why test now | Required measurement |
|---|---|---|---|
| P0 | Decompose 38.9% v4 no-command turns into death/channel/valid idle/blocked | Largest *observed* gap; may expose genuine engine or strategy faults | Per-turn actual state and action legality |
| P0 | Verify outcomes, gem trajectories, and draft before optimization | 500 outcome labels unverified and bot version was v4 | Engine-side winner, scores, gold, deaths |
| P1 | Opening enemy engagement + safety | Elite champion attacks ~67% higher in first 200 rounds | Net gem margin, deaths, fights won/lost |
| P1 | Safe high-value camp routing/assignment | Elites move 18% more and attack camps 21% more per match | Gems **banked per 100 rounds**, travel, downtime |
| P1 | Dynamic shop/recall/tribute schedule | Elites recall 57% more and buy 49% more on average, but strong teams disagree | Investment payback, gold earned, deaths, actual gems banked |
| P2 | Draft policy that responds to map and teammate roles | v4 effectively repeats fixed core while elites adapt composition | Held-out maps, mirrored-side paired matches |
| P2 | Vision/ward planning | Elites ward roughly twice as often; visibility payoff still unknown | Enemy encounter prediction and subsequent value |
| P3 | Joint planners, Bayesian models and population learning | Valuable after simulator parity and stable outcome labels | Held-out tournament performance vs >=3 opponents |

**The SSSA counterexample matters:** it has almost the same action volume as our v4. Therefore maximizing action count alone is **not** our objective.

## 5. V6 architecture

```text
observed game state + team-shared draft memory
    -> map archetype + game phase + opponent belief
    -> team-level strategic controller
         selects macro mode: split-farm | concentrated siege | contest | raid | defend | endgame
    -> objective candidate generator
    -> team assignment optimizer
         expected bankable gems, turn cost, death risk, upgrade ROI, team synergy
    -> champion local controller
         attack/cast/move legally; no state leaks, capped fuel
    -> telemetry (observable state, commands, predicted reward, actual outcome when available)
```

Proposed tunable parameters: `carry_threshold, health_reserve, enemy_pressure_penalty, contested_camp_bonus, bank_route_penalty, recall_for_shop_threshold, damage_window, ally_focus_bonus, fight_advantage_threshold, camp_respawn_lookahead, ward_information_weight, escort_weight, phase_switch_score_gap, objective_switch_hysteresis`. Do not prematurely optimize all at once; first tune low-dimensional groups and avoid the bad historical v5 experiment of changing multiple unrelated mechanisms together.

A provisional objective function for offline tournaments:

```text
Primary: paired match win/loss on current rules
Secondary: gem-tribute difference over the match
Diagnostics: early gem tempo, deaths, gold investment efficiency,
             time carrying gems, time unable to act, invalid commands,
             map/side robustness
```

Win rate and final score are the *only* promotion targets; auxiliary metrics diagnose why policies improve or regress and must not be gamed.

## 6. Experimental protocol

1. Freeze v4 and v5 live results; do not mutate them. Use `research/v6-elite-strategy-audit` only for analysis artifacts.
2. Confirm **all five withheld map names**. Protect them from tuning, preprocessing decisions and optimizer feedback. Three maps are already entirely absent; exact other two are unresolved.
3. Build matching-engine timeline extraction for replay outcome, score at rounds 100/200/400, gold, deaths, carrier loss, and zero-command cause. Don't re-execute on older, mismatched engine and claim validity.
4. Correctly partition episodes: exact map holdout, then bundle/replay-hash protection; discard cross-boundary observations that create leakage; compare by opponent and side.
5. Implement one rule-based v6 baseline (the smallest set of strategies that makes legal decisions and can reproduce/beat baseline objectives).
6. Run paired seed/map/side matches against v4, v5, and diverse strategies; use bootstrap or stratified confidence estimates accounting for opponent and map clusters. Do not promote on small one-hour batches.
7. Search discrete macro structures before precise numeric weights; tune knobs via successive halving / Bayesian optimization offline. Evaluate each survivor on unseen matches/held-out opponents and then **once** on sealed five-map test set.
8. Reserve official ladder allowances for compatibility and final confirmation, not broad parameter sweeps. Log source SHA, source ZIP hash, engine patch, opponent, map, side and result.

## 7. Current limitations / next artifact

Available now:
- `match-data/analysis/v6-elite-research/attempted-actions-per-match.jsonl`
- `match-data/analysis/v6-elite-research/attempted-actions.csv`
- `match-data/analysis/v6-elite-research/attempted-actions-summary.json`
- `tools/probe_v6_elite_actions.py` (179/179 validity)
- `tools/analyze_v6_elite_actions.py` (179/179 success)

Still required to promote hypotheses into findings: official v1.0.0 *stateful* replay decoder and verifiable winner/score data, map holdout names, new v6 implementation, and statistically meaningful controlled tests.

**Do not train v6 on v4's action labels as if they were optimal**; the data primarily teaches constraints, encounter patterns, opponent responses and what *not* to overfit. Retain only source-grounded evidence, and use new self-play outcomes for optimization.
