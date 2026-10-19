# Bot1 v1/v3 versus lll: paired replay analysis

**The strongest strategy to learn is cooperative clearing with a single reward recipient, supported by map-specific drafts and role-specific equipment.** V3 substantially reduces deaths, but leaves too much of the team traveling or farming low-value resources. It also retains fuel overruns on two maps. A more aggressive combat setting alone does not address these failures.

Open the [offline replay explorer](explorer.html) to compare both versions on each map, scrub champion positions, inspect equipment, and jump to capture events. The [implementation plan](STRATEGY-PLAN.md) turns the findings into separate, measurable changes.

## What was actually supplied

There are **50 games: five five-game series for each version**, all against the opponent labeled `lll`. The series/game numbers do not pair the maps correctly. Matching the SHA-256 of each embedded map gives **17 exact map pairs**. Each version has eight repeated recordings whose entire replay bytes are identical to another supplied recording. Those repetitions are retained but counted once for strategy comparisons.

| Measure | V1 | V3 |
| --- | ---: | ---: |
| Supplied games won | 2 / 25 | 2 / 25 |
| Distinct map games won | 2 / 17 | 1 / 17 |
| Champion deaths across distinct games | 250 | 40 |
| Gems lost on death across distinct games | 760 | 166 |
| Losses with zero Bot1 deaths | 1 | 6 |
| Recorded fuel-exhaustion boundaries across distinct games | 0 | 42 |

V3 scores more gems on eight maps, fewer on seven, and ties v1 at zero on two. These are descriptive paired results, not independent win-rate trials. All our bots play team A; side effects cannot be separated. Games end at different rounds, so final resource totals must be interpreted alongside their timelines. V1's better results against other opponents do not carry over to this particular opponent.

The opponent uses the same draft on each matching map across versions, but **seven different draft compositions across the 17 maps**. Cassi & Issac provide an extra champion body on 14 maps. Their linked death risk still matters; an extra body is not automatically an advantage in every matchup.

## 1. Help clear, then let one champion capture

The rules split a camp's reward among occupants; extra occupants do not accelerate its capture. The opponent repeatedly has several attackers help clear a camp, then one champion receive its reward. This leaves helpers free to attack another camp and gives the recipient enough gold for a meaningful purchase. The total reward is not increased by assigning one recipient.

**Rows, v3:** the opponent captures its first three-wolf camp at **round 34**, receiving **270 gold and 66 gems on Issac**. Recorded attacks/spells targeting those camp coordinates come from Issac, Vendetta, Cassi, and Varg, beginning at round 10. Our Varg clears its first gem camp alone and captures it at **round 69**. By round 200 the opponent has earned 1,620 gold and spent all of it; we have earned 1,230 and still hold 450 unspent.

The opponent ultimately collects 1,122 gems and submits 1,056. V3 collects 462, all on Varg, and submits 396. Tavi, Vendetta, and Ryth collect **zero**. Tavi spends 361 of 413 completed turns in the movement-without-gems category; Ryth spends 335 of 414 there. No champion on either team dies. This is a team productivity failure, independent of PvP casualties.

Evidence: [rows v3 strategy](v3/team-lll-match4/05/strategy.json), [native events](v3/team-lll-match4/05/events.json), [turn states](v3/team-lll-match4/05/turns.json).

**31×31, v3:** our team captures 11 gem groups, splitting eight between multiple allies. The opponent captures 22 and splits none. Examples:

| Round | Event |
| ---: | --- |
| 28 | Our Varg and Vendetta split 44 gems: 22 each. |
| 33 | Opponent Cassi receives 48 gems after Cassi and Stellar attack the group. |
| 36 | Opponent Issac receives 48 gems after Issac and Ren attack the group; our Tavi also records a few attacks there. |
| 58 | Opponent Ren receives 44 gems after Ren and Stellar attack the group. |
| 76 | Our Varg and Vendetta again split 44 gems. |
| 80 | Opponent Issac receives 44 gems after contributions from Issac, Stellar, and Cassi. |

The opponent takes a lead that persists from round 46 onward. At round 200 the score is **176–416**; the final score is **468–1,036**, with zero deaths on both sides. It has four bodies against our three, but it also clears twice as many groups.

Our average continuous bag interval is **11.1 turns**, versus **11.3** for the opponent. Mean completed delivery size is 27.5 versus 47.1 gems. In this case, the larger deliveries come chiefly from whole camp rewards, not longer carrying intervals. This revises the earlier hypothesis that a general “bank less often” change should be the main solution.

Evidence: [31×31 strategy, captures and equipment](v3/team-lll-match1/01/strategy.json).

Across the 17 distinct v3 games, our side splits **61 of 610 resource captures**; the opponent splits **3 of 737**. The counts include gold-only camps. They establish a repeated behavior, although the opponent's internal assignment algorithm is unknown.

The current ordinary-camp code lets every assigned champion enter a cleared reward region: [farm reward handling](../../../bots/Bot1/src/bot.cpp:903). Its selection heuristic discounts shared rewards rather than assigning a clearer, helper, and recipient: [camp selection](../../../bots/Bot1/src/bot.cpp:333). V3 has recipient election for the monolith special case, but not ordinary farming.

## 2. Match equipment to the champion's actual job

The opponent generally starts with **Power Strength for basic attackers** and **Power Focus for spellcasters**, then adds defensive equipment as needed. It repeatedly builds Focus on Cassi, Stellar, Ren, and Tavi. Our ordinary draft mostly buys Monster Strength, then Jungle Strength, even for Tavi.

On the 31×31 map, opponent Ren has a Power Focus emblem and a Durability Health shard at round 59. Our Tavi does not receive its first reward or buy equipment until round 120. By round 200, the opponent has earned 1,320 gold against our 900, and holds only 70 unspent against our 270.

The rules explain why the build choice is plausible: Tavi's damaging stun scales at 2.2× Focus; Ren's stun and retaliation scale with Focus; Stellar has single-target and area Focus damage. Power emblems provide six shards' worth of stats for five purchases. Strength remains appropriate for Varg's splash attacks and attack-reset champions.

**Inference to test:** Focus-based helpers can contribute burst and stuns while melee farmers maintain basic attacks and tank. This does not prove a universal Power-first build or that Focus beats Strength for solo-farming Tavi. The opponent also sometimes spends substantial gold on durability. Test role-specific builds separately from the coordination change.

Evidence: per-champion `equipmentProgression` in each strategy JSON; [local champion and equipment rules](../../../GameRules.md).

## 3. The 60×50 map needs a team objective, even though it has no monolith

All gem resources on this map belong to **one connected group: six elks plus six gem clusters**, worth 360 gems. There are also many gold-only camps. Both versions farm gold successfully but never capture the gem group.

| Version | Our gold | Opponent gold | Final gems | End round |
| --- | ---: | ---: | --- | ---: |
| V1 | 14,760 | 10,880 | 0–1,080 | 1,709 |
| V3 | 14,134 | 12,370 | 0–720 | 2,000 |

In v3, our team completes **157 resource captures, all without gems**. The opponent completes 136, including the decisive gem captures at **rounds 1,758 and 1,896**, awarded entirely to Stellar and Ren respectively. Multiple opponent champions record attacks at the objective in each capture cycle. Our Varg records one attack in each cycle, so “we never approach or attack it” would be incorrect; we fail to secure its reward.

The gold phase itself is not evidence of a failure: the opponent also farms for most of the game. The failure is never completing the transition to the scoring objective. Stellar's last purchase before its first gem capture leaves it at 830 Focus. The opponent converts its equipment into group damage and completes the objective while our champions continue competing with gold tasks.

V3's team objective planner activates only on monolith-only maps. Large non-monolith groups still pass through a solo-survival estimate with limited nearby-helper accounting. **Extend objective planning to any scoring group the team must clear together.** The replay supports this requirement; it does not establish the optimal engagement threshold.

Evidence: [60×50 v3 strategy](v3/team-lll-match5/05/strategy.json), [v1 strategy](v1/team-lll-match1/01/strategy.json).

## 4. Monolith readiness cannot substitute for a functioning gold economy

On the monolith-only 50×50 map, v3 reduces our deaths from 97 to 19, but still scores zero. By round 200 the opponent has earned **1,240 gold against our 280**; by round 500 it is **3,320 against 805**. Our Varg spends 1,410 of 1,817 completed turns in the movement-without-gems category.

The opponent uses Ryth, Stellar, Prism, Ren, and Tavi—**no Willow**. It farms and fights first, then captures monoliths at rounds **1,120, 1,318, 1,447, 1,580, and 1,771**. Each capture has one recipient, with several champions contributing attacks during the preceding attempts. It finishes with 1,000 gems at round 1,817.

The evidence does not show that healing is useless. It shows that a healer draft plus readiness checks has not delivered an adequate opening economy. The next design needs productive nearby farming assignments before any rally and should evaluate a damage/control composition alongside the healer variant.

Evidence: [monolith-only v3 strategy](v3/team-lll-match3/02/strategy.json), [v1 strategy](v1/team-lll-match1/02/strategy.json).

## 5. V3 still has a separate runtime regression

On the **90×30 map**, v1 wins **1,022–982**; v3 loses **628–1,024**. Neither game has a Bot1 death. V3 records **39 fuel-exhaustion turn boundaries**. Its stdout logs five initialization spill messages and 33 navigation spill messages; stdout messages and engine boundary counts are different measurements. There are **18 altars**, and initialization builds a separate full distance field for every altar. Navigation can perform several searches in one decision before its next fuel check.

The 80×80 v3 game records three additional exhaustion boundaries during initialization, although it wins. V1 has no exhaustion boundaries in these supplied games. Across all files including duplicates, v3 records 84 boundaries; after deduplication there are 42. There are no caught `bot error` messages in either version's supplied logs.

The source structure and spill locations point to expensive initialization and navigation as repair targets; attributing each fuel cost to a particular SDK call requires instrumentation. The score difference on 90×30 cannot be assigned entirely to fuel, because the versions also differ strategically.

Evidence: [90×30 strategy](v3/team-lll-match1/05/strategy.json), original stdout alongside the linked replay; [initialization](../../../bots/Bot1/src/bot.cpp:35), [navigation searches](../../../bots/Bot1/src/bot.cpp:446).

## What to build from this evidence

Replace isolated greedy farming with **small cooperative clearing groups and one designated capturer per camp**. Let helpers leave for the next job while the recipient captures, shops if needed, and banks. Rotate recipients to keep multiple useful champions equipped. Use map structure and camp layout to select roles; retain the successful spacious-map farming behavior as a comparison baseline.

Add an objective plan for every map where ordinary solo farming cannot produce gems. Give it a productive opening, explicit nearby participants, one recipient, a damage/survival check, and a bounded retry policy. Fix the remaining fuel regression before evaluating strategy variants.

Do not combine all changes into another untested release. The [implementation and validation plan](STRATEGY-PLAN.md) separates coordination, equipment, draft, objectives, and runtime work. No bot source or upload ZIP was changed by this analysis.

## Evidence quality and limitations

- All 50 original inputs replay to completion under the official 0.0.3 engine, with zero replay errors and unchanged SHA-256 hashes.
- Every champion's native completed-turn count **and round sequence** matches an independent parser of the recorded actions. Gem balance differences match gem losses on death in every game.
- Map pairing uses the embedded map bytes, not dimensions or folder names. Instantiated camps are read after draft expansion, including reflected copies. Capture recipients and reward amounts come directly from engine events; their camp groups are located using the recipient's preceding turn position and engine group membership.
- Champion activity categories are mutually exclusive observations. “Attack or cast” includes support abilities and dashes; “other without move/attack/cast” can include useful waiting or shopping. Movement categories do not by themselves reveal intent. All categories sum to completed turns.
- Helpers are inferred from attacks/spells targeting camp coordinates between successive captures. Those counts can include separated attempts, and do not prove an uninterrupted clear or the opponent's internal role assignment. The early uncontested examples provide the cleanest evidence.
- Equipment progression records end-of-turn inventory changes, not the exact order of several purchases within one turn. Bag intervals include the sampled time carrying gems and can end at death or the end of the game.
- V3 banners identify strategy v3 in every supplied v3 stdout file. V1 uses the user's version label and compatible behavior/drafts; a remote upload binary was not supplied for cryptographic verification. The opponent's rank and source code are not in these files.
- Same-side, same-map replay comparisons support diagnosis, not proof of a causal fix or general strength against other teams. Opponent reactions change with our behavior. Run controlled local variants and then validate against another opponent.

## Reproduce

```bash
node --no-warnings match-data/analysis/extract_native_replays.mjs match-data/v1 match-data/analysis/paired-v1-v3/v1
node --no-warnings match-data/analysis/extract_native_replays.mjs match-data/v3 match-data/analysis/paired-v1-v3/v3
python3 match-data/analysis/analyze_paired.py
python3 match-data/analysis/build_paired_explorer.py
```

Full paired results follow. Hash prefixes distinguish maps of the same size. Scores always list Bot1 first.

<!-- matched-results -->
| Map fingerprint | Size | V1 score | V3 score | V1 / V3 deaths | V3 fuel boundaries |
| --- | --- | --- | --- | --- | --- |
| `37b8ace8` | 30x30 | [540–1008](v1/team-lll-match2/03/strategy.json) | [756–1008](v3/team-lll-match1/02/strategy.json) | 8 / 0 | 0 |
| `9696d128` | 30x30 | [532–1042](v1/team-lll-match4/04/strategy.json) | [322–1048](v3/team-lll-match3/05/strategy.json) | 19 / 3 | 0 |
| `c84673dd` | 30x80 | [856–1018](v1/team-lll-match3/05/strategy.json) | [696–1018](v3/team-lll-match4/03/strategy.json) | 3 / 2 | 0 |
| `116b2c56` | 31x31 | [612–1020](v1/team-lll-match3/03/strategy.json) | [468–1036](v3/team-lll-match1/01/strategy.json) | 5 / 0 | 0 |
| `c7ac6997` | 40x40 | [788–1026](v1/team-lll-match4/05/strategy.json) | [904–1020](v3/team-lll-match3/04/strategy.json) | 4 / 1 | 0 |
| `61fa921a` | 41x30 | [198–1008](v1/team-lll-match4/03/strategy.json) | [220–1002](v3/team-lll-match3/03/strategy.json) | 27 / 2 | 0 |
| `ebfcace1` | 41x41 | [242–1004](v1/team-lll-match1/03/strategy.json) | [366–1032](v3/team-lll-match3/01/strategy.json) | 12 / 1 | 0 |
| `988f7804` | 45x30 | [0–1000](v1/team-lll-match1/04/strategy.json) | [36–1008](v3/team-lll-match5/04/strategy.json) | 23 / 3 | 0 |
| `50365c96` | 50x50 | [462–1056](v1/team-lll-match3/04/strategy.json) | [396–1056](v3/team-lll-match4/05/strategy.json) | 0 / 0 | 0 |
| `61bcbc25` | 50x50 | [674–1004](v1/team-lll-match3/01/strategy.json) | [630–1004](v3/team-lll-match4/01/strategy.json) | 2 / 0 | 0 |
| `c76debb1` | 50x50 | [0–600](v1/team-lll-match1/02/strategy.json) | [0–1000](v3/team-lll-match3/02/strategy.json) | 97 / 19 | 0 |
| `13843d1e` | 50x65 | [364–1020](v1/team-lll-match1/05/strategy.json) | [204–1028](v3/team-lll-match4/02/strategy.json) | 16 / 1 | 0 |
| `43362dd0` | 60x50 | [0–1080](v1/team-lll-match1/01/strategy.json) | [0–720](v3/team-lll-match5/05/strategy.json) | 14 / 6 | 0 |
| `ee68ccad` | 71x71 | [88–1026](v1/team-lll-match2/02/strategy.json) | [514–1010](v3/team-lll-match1/04/strategy.json) | 17 / 0 | 0 |
| `95a4e642` | 80x80 | [1018–760](v1/team-lll-match2/04/strategy.json) | [1072–804](v3/team-lll-match1/03/strategy.json) | 0 / 0 | 3 |
| `bf50fd85` | 90x30 | [1022–982](v1/team-lll-match2/05/strategy.json) | [628–1024](v3/team-lll-match1/05/strategy.json) | 0 / 0 | 39 |
| `cd0e19ff` | 100x100 | [640–1082](v1/team-lll-match2/01/strategy.json) | [832–1068](v3/team-lll-match2/01/strategy.json) | 3 / 2 | 0 |
