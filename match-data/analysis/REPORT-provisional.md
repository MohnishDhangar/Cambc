# Bot1 lobby analysis

The clearest failures are a reproducible banking deadlock, a missing team objective on monolith-only gem maps, and combat decisions that do not account for enemy groups. These explain different parts of the two lost series. The 4:1 win is consistent with a functioning farming bot that still has these map-dependent weaknesses.

## Evidence and limits

The supplied directory contains 15 original replays, 15 team-A fuel traces, 15 stdout files, and empty debug files. It does not contain separate native match-summary JSON files. Team A is Bot1, identified by the recorded draft choices and its own draft output.

The platform recordings identify engine/format 0.0.3. The installed CLI and visualiser contain engine 0.0.1. I decoded the original action records directly and independently of simulation. To inspect positions, channels, and resources, I also converted the draft framing for the older local engine: a default spawn selector was removed, and explicit draft yields were omitted because the older engine advances draft turns automatically. Every gameplay record was preserved. Original files were not modified.

Five replays reached the end with every gameplay input accepted by the older engine. Ten reached an incompatible action; reconstruction stops at the first such action. **Acceptance by the older engine does not prove identical behavior under engine 0.0.3.** Reconstructed scores, health, and resource statistics below are therefore provisional. Full native 0.0.3 summaries are needed to verify all final totals. I have not supplied final scores or death counts for the ten partial reconstructions.

The original action records establish round boundaries, draft composition, action counts, tribute starts, and fuel-exhaustion boundaries without the simulation. The independently parsed turn counts match every champion's turn count in all five completed reconstructions.

## 1. A banking deadlock cost two carriers most of a hundred rounds

**Forged Tokens, game 2, `rows`, 50×50.** The completed local reconstruction finishes at round 429 with Bot1 at 462 gems and the opponent at 1,056. Neither side has a champion kill in that reconstruction; the original records also contain no basic attacks against champions.

Two carriers spend long intervals near `(22,2)` / `(22,3)`:

| Champion | Rounds in the stalled area | Duration | Bag | Health throughout, reconstructed |
| --- | --- | --- | --- | --- |
| Varg | 189–303 | 115 turns | 66 gems | 420 |
| Vendetta | 233–303 | 71 turns | 66 gems | 286 |

They have no recall or tribute channel running during these intervals. Varg makes only two ordinary moves during the 115 turns; Vendetta makes one during the 71 turns. Both eventually bank their 66 gems after movement resumes. This is a loss of scoring time and subsequent farming capacity, even though the gems themselves survive.

Three implementation choices combine to explain the stall:

1. [Threat inference](bot-v1-source/bot.cpp:198) treats a group with missing health as dangerous indefinitely. Damaged camps can go back to sleep; missing health is not evidence of continued aggression.
2. [Navigation](bot-v1-source/bot.cpp:230) computes a distance field that ignores danger, then adds danger only when scoring the next tile. It accepts only a strictly lower score. A safe detour may initially leave the distance unchanged or increase it, so the bot refuses to start it.
3. [Stall recovery](bot-v1-source/bot.cpp:488) requires `target >= 0`. [Banking](bot-v1-source/bot.cpp:372) clears the target, so gem carriers cannot trigger that fallback.

A simplified calculation on the actual map illustrates the local minimum. At `(22,3)`, walking distance to an altar approach is 15. Stepping north keeps it at 15, so the bot rejects the step. Stepping west reduces walking distance to 14, but a modeled 20-damage wolf adds 40 to the score, making it 54. A route north around the danger exists, yet neither first step is accepted.

Tavi also contributes **zero gems**, despite earning and spending 420 gold in the completed reconstruction. He moves on 307 of 428 turns and makes unsuccessful clearing trips as well as gold farming. His activity is not turning into captured gem camps. Poor farm allocation and failed clearing compound the two banking stalls.

**First fix:** plan an entire route around risk, expire inferred camp aggression, and apply progress recovery to banking and retreat as well as camp targets. Banking near an unsafe altar also needs an alternative destination: currently, refusing tribute and then navigating to a goal set containing the current tile can leave the champion standing still.

## 2. The bot has no way to initiate a coordinated monolith objective

**lll, game 2, 50×50, 1,931 rounds.** The map contains gold clusters and monoliths, with no wolves, elk, or gem clusters. Monoliths are the only camp source of gems.

The original, fully parsed action records contain:

| Team | Tribute starts over the entire game |
| --- | --- |
| Bot1 | **0** |
| lll | **5** |

This conclusion does not depend on the older replay engine. Bot1 never attempts to turn carried gems into score in this game.

The [camp selector](bot-v1-source/bot.cpp:160) first requires a safe solo target. Its cooperation fallback can join an **already assigned** live camp. It cannot seed a team objective when every champion rejects the monolith as individually unsafe. Gold clusters keep supplying acceptable individual work, without a transition to a collective gem objective. Farming gold and buying more strength are not sufficient unless the team eventually gathers, clears a monolith, captures it, and banks the reward.

**Second fix:** classify maps by their actual gem sources. On this map type, explicitly plan a gold-and-equipment opening followed by a team rendezvous, combined-damage assessment, tank rotation, monolith capture, and tribute. A healing draft option may be useful here, but should be evaluated against the actual map and squad survival estimate.

## 3. The compact-map losses expose weak combat decisions

The original records show more opponent basic attacks directed at champions in several losses:

| Game | Bot1 attacks on champions | Opponent attacks on champions |
| --- | --- | --- |
| Forged Tokens 3 | 92 | 178 |
| Forged Tokens 4 | 52 | 124 |
| Forged Tokens 5 | 41 | 78 |
| lll 1 | 39 | 127 |
| lll 5 | 21 | 42 |

These are action counts, **not damage or kill counts**. They establish greater direct combat activity by the opponents. Early reconstructed prefixes also show casualties on our side, but the engine mismatch prevents trustworthy final death totals for these games.

The code has specific weaknesses that make this pressure costly:

- [Enemy selection](bot-v1-source/bot.cpp:337) chooses one nearby target using that target's health, bag, and distance. It does not compare the number, health, strength, or available burst of nearby allies and enemies.
- [Combat precedes banking](bot-v1-source/bot.cpp:493). A carrier can spend turns attacking instead of completing its scoring route.
- [Recovery](bot-v1-source/bot.cpp:484) normally starts below 28% health. That can be too late against several spells and stuns in the same round.
- [Enemy danger](bot-v1-source/bot.cpp:196) uses basic attack range plus one. It does not model spell range, dashes, or stun chains.
- The default purchases favor camp damage and camp damage reduction. Tavi's field purchases never add health in this implementation.

Fourteen of the fifteen opponent drafts include Cassi & Issac, creating one extra body. That improves their available actions and pressure when both survive. We also win games against these drafts, so the extra body alone does not explain the losses. It is a draft option worth benchmarking after the navigation and objective failures are fixed.

**Third fix:** make fight/escape decisions from the local team situation and enemy burst, with explicit protection for carriers. Use healthier builds where the matchup requires them, and reserve movement or escape abilities when continuing the fight is unfavorable.

## 4. One loss was a close farming and delivery race

**lll, game 4, 90×30.** The completed local reconstruction ends at round 464:

| Metric | Bot1 | lll |
| --- | --- | --- |
| Tributed gems | 964 | 1,004 |
| Collected gems | 1,022 | 1,048 |
| Carried gems at the end | 58 | 44 |
| Earned gold | 4,505 | 4,300 |
| Champion kills / deaths | 0 / 0 | 0 / 0 |

This is a throughput and timing loss, without combat kills. Having 58 carried gems does **not** mean we could win immediately by pressing tribute. Tavi starts channeling his 22 gems at round 463, too late to finish before the opponent wins. Varg captures the other 36 at round 464 and still has to travel and channel.

The useful improvement is to shorten the whole farm-to-altar cycle and anticipate the endgame earlier. The collection deficit is only 26 gems; shopping income alone is not the bottleneck. Route choice, capture timing, draft efficiency, and channel latency all matter in such a close race.

## 5. What the winning series tells us

All three series contain the same large, 80×80 farming map. Bot1's recorded action totals there are identical across opponents. Each completed local reconstruction produces **1,018 gems at round 568**, with no champion kills or deaths on either side. The opponent totals differ: 724, 760, and 824.

This is evidence that Bot1 has a repeatable farming opening when the opponent does not interfere with it. The `know` series also contains a long `rows` game with only seven Bot1 tribute starts versus 24 by the opponent. The recurring weakness therefore appears map-dependent, even within the series you won 4:1. Exact scores for that `know` game need its native summary.

## Runtime findings

Across all 15 original games:

- Bot1's stdout contains no `bot error` or `fuel spill` messages.
- Bot1 has **zero recorded fuel-exhaustion turn boundaries**.
- The fuel traces are consistent with normal consumption, with larger initialization turns covered by the increased first-turn budget.

There is no evidence that crashes or fuel exhaustion explain these series losses. High counts of actionless turns are not automatically wasted time: they can include death, capture waits, healing, and channels. The specific banking stalls above were checked separately.

## Recommended order of work

1. Fix danger-aware routing, camp-aggression expiry, and carrier stall recovery. Reproduce the `(22,2)` / `(22,3)` case as a targeted regression scenario.
2. Add explicit team objectives for maps where monoliths are the only gem source.
3. Make combat and retreat decisions sensitive to nearby teams, burst damage, and carried gems.
4. Optimize farm-to-altar cycles and deadline decisions for close races.
5. Benchmark draft variants, including Cassi & Issac and healing support, against stronger opponents and relevant map types.

The first two changes address concrete failures shown by these recordings. More starter-only wins would not establish that those failures are fixed; the regression scenarios must exercise the specific stall and objective conditions.

## Artifacts and reproduction

- [Visual explanation](findings.svg)
- [Original-action metrics](recorded-action-metrics.txt)
- [Machine-readable action metrics](recorded-action-metrics.json)
- [Reconstruction summaries](summaries.json)
- Per-game folders contain reconstructed `events.json`, `turns.json`, `rounds.json`, and `summary.json`, plus the map extracted from that original replay.

Commands, run from the workspace root:

```bash
node --no-warnings match-data/analysis/extract_replays.mjs
python3 match-data/analysis/raw_metrics.py
python3 match-data/analysis/plot_findings.py
```

The extractor stops at the first incompatible gameplay action. The raw action counter continues through every original record and checks that it consumes each file exactly. Source SHA-256 hashes are saved in the reconstruction summaries.
