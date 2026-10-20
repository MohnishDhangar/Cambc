# CAMBC 2026a — V4 Opponent Strategy Study and V5 Development Playbook

**Prepared:** 20 October 2026  
**Source:** 245 archived Bot1 v4 games against 49 opponent groups, plus nine inspected action-level case studies  
**Engine:** official CAMBC 0.0.3 via client 2.2.5; **PRE–WEEK 2 balance**  
**Status:** Evidence-driven strategic recommendations; NOT a post-patch win-rate claim

## Executive findings

**V4 is losing on three coupled fronts**: its opponents accumulate resources earlier, usually win combat engagements, and convert a larger fraction of collected gems into score. This is more than a draft discrepancy. In the 120 high-Elo-series games, the opponent has the larger round-200 gold total in **80.8%**, deals more champion damage in **92.5%**, and wins the champion-kill count in **95.8%**. V4 loses gems on death or otherwise permanently in **64.2%** of these games; opponents in only **10.8%**.

The most promising reusable opponent mechanisms are:

1. **Combine farming with protection and selective PvP.** Fast early gold plus early upgrades leads to stronger fights and safer resource delivery. The elite opponents' median score/gold lead expands after the opening; mere early tribute timing does not explain it.
2. **Concentrate allied damage on the same target.** In inspected attrition maps, opposing champions repeatedly damaged the same champion within a round. This was dramatically rarer for V4.
3. **Buy survival alongside damage when contention is expected.** Observed opponents purchased Jungle/Bruiser/Durability Health in combination with Focus/Strength rather than V4's predominantly farming-focused early economy. The *specific* shard mix is not universally optimal.
4. **Protect the banking pipeline.** Across the higher-Elo series, median banked/collected gem fraction was **0.96** for opponents versus **0.69** for V4. Combat deaths, accumulated carry risk and routing losses all require investigation.
5. **Use multiple strategies by map.** A 30×30 tempo game ended in 255 rounds; 50×50 contests included more than 50 kills and lasted over 1,400 rounds. The right policy is conditioned on map, objectives, travel distances and enemy composition.

Do **not** conclude from this study that “PvP always wins.” In one inspected high-Elo-series match, V4 won 1,152–0 despite losing the kill battle 2–22; in another same-Elo-series match, V4 won 1,052–902 with zero champion damage from either side. The objective remains tributed gems.

## 1. Dataset and validation

| Original folder | Opponent groups | Replays | Actual V4 victories | Actual V4 defeats |
| --- | ---: | ---: | ---: | ---: |
| higher-elo/losses | 24 | 120 | 9 | 111 |
| same-elo/losses | 15 | 75 | 20 | 55 |
| same-elo/wins | 10 | 50 | 33 | 17 |
| **Total** | **49** | **245** | **62** | **183** |

**Integrity checks:** 245/245 reconstructed through the exact archived native 0.0.3 engine; zero decoding failures; zero metrics failures; 245 distinct SHA-256 replay hashes; no duplicates. The high-Elo cohort spans 21 distinct map hashes.

**Critical labeling correction:** `wins` and `losses` categorize opponent *series*, not every individual match. **43 of 245 actual winner labels disagree with their folder** (7 wins in higher-elo/losses, 19 wins in same-elo/losses, and 17 losses in same-elo/wins). The initial auto-generated screening found 44 when comparing **scores** instead of engine outcomes because eight matches end 0–0 and invoke gold/kills/team-order tiebreaks. **The engine outcome is authoritative.**

These are intentionally selected opponents and grouped recordings, not a representative random Elo sample. Accordingly, the above percentages are **conditional on this dataset**, not a predicted ladder win rate. Verified Team-A V4 stdout samples identify the subject bot; for formally published aggregate results, add automatic per-file stdout verification.

Data and provenance:
- [All raw v4 metrics and replay SHA-256 identities](../match-data/analysis/v4-study/metrics.json)
- [Auto-generated full quantitative screening](../match-data/analysis/v4-study/REPORT.md)
- [Native replay extractor](../match-data/analysis/extract_v4_study.mjs)
- [Quantitative analysis source](../match-data/analysis/summarize_v4_study.py)
- [Turn-level tactics study source](../match-data/analysis/study_v4_tactics.py)

## 2. Quantitative differences

### 2.1 Higher-Elo-series: match-level medians

| Metric | Bot1 v4 | Opponent | Interpretation |
| --- | ---: | ---: | --- |
| Final tributed gems | 356 | 1,020 | Large scoring gap |
| Lifetime gold | 2,315.5 | 3,882.5 | Opponent also wins the economy |
| Collected gems | 533 | 1,078 | V4 fails to acquire enough |
| Banked / collected gems | 0.69 | 0.96 | V4 also fails to retain/bank efficiently |
| Champion kills | 0 | 8.5 | V4 generally loses fights |
| Champion deaths | 8.5 | 0 | Repeated respawn and resource denial |
| Gems irrecoverably lost | 60 | 0 | Median attrition |
| Recorded champion-damage events | 29.5 | 80.5 | Opponent attacks champions more effectively |
| Damage to champions (recorded) | 2,515 | 7,670 | Strong direct combat disparity |
| Ability-cast events | 152 | 240 | Higher active skill throughput |
| First camp reward-recipient event, round | 40 | 32 | Earlier opponent objective income |
| First tribute, round | 73 | 73 | Timing of *first* tribute alone is not the gap |

Each column's median is calculated separately, and medians need not represent one actual game. `Reward-recipient events` count champion awards rather than unique camp-group captures; split captures can inflate that count.

### 2.2 Opening snowball in high-Elo-series games

| Checkpoint | V4 median tributed gems | Opponent median tributed gems | V4 median earned gold | Opponent median earned gold |
| --- | ---: | ---: | ---: | ---: |
| Round 100 | 0 | 72 | 371 | 570 |
| Round 150 | 66 | 163 | 511 | 940 |
| Round 200 | 88 | 240 | 800 | 1,252.5 |
| Round 300 | 154 | 432 | 1,385 | 2,045 |
| Round 400 | 176 | 616 | 1,660 | 2,885 |

**In 80.8% of the 120 high-Elo-series replays, opponents lead in lifetime gold already by round 200.** In 76.7%, they lead in tributed gems by that checkpoint. Median within-game score lead (opponent minus V4) grows from **16 by round 100**, to **121 by round 200**, to **322 by round 400** (for games lasting that long).

**Working mechanism:** improve camp selection, early capture timing, first upgrades and transition from farm to PvP. The replays do not establish whether any single purchase or path choice caused the lead.

### 2.3 Combat survival and resource security

In higher-Elo-series games:
- Opponent deals more champion damage in **111/120 (92.5%)**; at least double V4's damage in **92/120 (76.7%)**.
- Opponent outscores V4 on credited champion kills in **115/120 (95.8%)**.
- Opponent has zero deaths in **62/120 (51.7%)**; V4 has zero deaths in only **3/120 (2.5%)**.
- Opponent gets at least five champion kills in **83/120 (69.2%)**.
- V4 loses some collected gems in **77/120 (64.2%)**; opponent loses some in **13/120 (10.8%)**.
- Opponent collects more total gems in **109/120 (90.8%)**.

This shows a **compounding combat–economy loop**: surviving keeps champions working; killing enemy champions delays their farming, capture and tribute cycles; safely retaining bags converts collected resources into actual score. Causality and relative contributions require controlled tests.

### 2.4 Same-Elo comparisons are informative

| Series bucket | V4 median score | Opp. median score | V4 median gold | Opp. median gold | V4 median deaths |
| --- | ---: | ---: | ---: | ---: | ---: |
| same-elo/losses | 564 | 1,018 | 3,142 | 3,695 | 8 |
| same-elo/wins | 1,013 | 829 | 4,358 | 3,560.5 | 4 |

V4 wins more often when it achieves better economic throughput and suffers fewer deaths. It can win with fewer champion kills. Hence the desired v5 balance is **profitable fighting when necessary**, not a permanent combat objective.

## 3. Repeated elite tactics and evidence

### A. Multi-champion focus fire / target convergence — HIGH priority

We inspected **nine** full turn/event case studies after the 245-match screen. “Same-round multi-attacker focus” means at least two *different allied champions* actually reduced the HP of the same enemy champion in one round.

| Recorded case | V4 focus events | Opponent focus events | Final score V4–Opponent |
| --- | ---: | ---: | --- |
| high team-13, game 02, 41×41 | 0 | 11 | 46–1,025 |
| high team-16, game 05, 50×50 | 5 | 18 | 0–1,000 |
| high team-19, game 02, 50×50 | 2 | 27 | 0–1,000 |
| high team-24, game 01, 50×50 | 1 | 47 | 200–1,000 |
| high team-2, game 01, 60×60 | 1 | 71 | 1,152–0 |
| high team-22, game 04, 60×60 | 0 | 21 | 1,008–456 |

The numbers imply **effective coordinated targeting**, whether achieved through deliberate team logic or common local target preferences. V4's `defend()` picks a local victim independently; its shared memory is used for camp claims, not an enemy focus target. Improvements: candidate target scores should incorporate nearby allies, enemy HP/burst, stun status, carried gems and lethal-burst probability. Communicate a single target ID/short expiration where useful within the 8-byte team memory.

**Counterexample:** high team-2 game 01 ends 1,152–0 *in V4's favor* despite opponent 71 focus events and 22 champion kills. Focus fire is not sufficient to win if the opponent cannot turn combat into tribute.

### B. Safe scaling through hybrid damage + durability purchases — HIGH priority

Specific observed opening (before round 150) item-count increases:

- **High team-19 game 02:** opponent gains 12 Monster Focus shards, 3 Monster Focus emblems and 5 Jungle Health shards (aggregated across champions). V4's opening is predominantly Power Focus and a small amount of jungle/monster Strength. The opponent wins 1,000–0 with 51 champion kills; opponent first kill at round **46**.
- **High team-24 game 01:** opponent gains 7 Power Focus shards, 7 Power Strength shards, 4 Jungle Strength shards, 2 Power Health shards and an additional health emblem. The opponent wins 1,000–200, delivers 56 kills and first kills V4 at round **58**.
- **High team-9 game 04 (30×30):** opponent adds 6 Durability Health shards, 3 Jungle Health shards, a Jungle Health emblem and Bruiser Health emblem by round 150. The game ends by round **255**, score 1,020–60.
- **High team-13 game 02:** opponent emphasizes Jungle Strength and early Bruiser Health/other emblems, winning 1,025–46 in 353 rounds.

These are **observed builds**, not a universal item recipe. They suggest adapting combat versus camp damage and durability to champion role and expected map contention. Week 2 alters champion growth rates, so exact breakpoints must be recalculated.

### C. Control the contested center rather than necessarily spawn-camp — HIGH priority

In the high-Elo extended-combat samples, our proximity calculation found **zero early opponent champion-turns within nine Chebyshev tiles of Bot1's spawn**. Yet those opponents achieved 10–56 champion kills. This is compatible with pressure at neutral objectives, lanes or altars, not proof of spawn invasion.

A contrasting example exists: **same-elo/wins/team-1/game 01** actually ended 0–1,008 *against V4*, with 31 opposing champion kills, **133 recorded opponent champion-turns near the V4 spawn before round 250**, and 85 opponent multi-attacker focus events versus V4's seven. It is an example of sustained proximity pressure, though map geometry may contribute.

**Lesson:** two different mechanisms exist. V5 should contest profitable regions and only approach an enemy spawn if the exchange of risk, denial and resources favors it.

### D. Keep both the farm and tribute loops productive — HIGHEST priority

Two extremely violent cases demonstrate the resource-denial loop:

| High opponent | Rounds | V4 score | Opp. score | V4 deaths | Opp. kills | Opp. gold |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| team-19/game 02 | 1,497 | 0 | 1,000 | 51 | 51 | 16,370 |
| team-24/game 01 | 1,592 | 200 | 1,000 | 56 | 56 | 16,540 |

The old kill reward was 50 gold; these opponents still earned vastly more gold than kill payments alone. Thus they continued obtaining resources **while** suppressing V4.

Under Week 2, champion kill reward rises to 100 gold; this potentially increases the attractiveness of safe picks, without making a suicidal fight profitable.

### E. Use draft/body advantages selectively — MEDIUM priority

Of 120 higher-Elo-series games, opponent rosters include:
- Stellar in **114**;
- Cassi & Issac pair in **107** (two independent bodies for one draft choice);
- Varg in **86**;
- Ren in **83**;
- Ryth in **75**.

V4 selected Tavi and Varg in all 120; Vendetta in 114, Ryth in 91 and Vesper Vale in 77. V4 has far less ranged burst and lacks the extra Cassi/Issac body, which is consistent with the combat and reward-control disparities—but frequency is not causation.

**Major Week 2 qualification:** Cassi/Issac, Stellar, Varg, Ren and Ryth received nerfs. Copying pre-patch top drafts verbatim is a poor method. Use opponent drafts to identify *roles*: ranged damage, extra-body objective pressure, stun/control, sustain, carry defense and safe clear speed.

### F. Win without necessarily fighting — MEDIUM priority

**same-elo/losses/team-10/game 02** is an actual V4 victory, score **1,052–902**. Full recorded analysis found **zero champion damage by either team**. A purely economic outcome is achievable: farming efficiency and successful banking still matter even when no PvP happens.

This is why the v5 score function should maximize expected **net tributed gems per round**, then add PvP denial/gold when likely to be profitable.

### G. Detect map-specific deadlocks — HIGH impact in affected maps

Eight archived games finish at **0–0** and resolve by gold or another tiebreak. Multiple V4 gem carriers also show extremely long unchanged-position/bag intervals on such matches. These are exceptional map states, not representative of routine losses. Nevertheless, stall loops can completely prevent scoring.

Validate navigation toward altars, channel safety rules, long carry-stalls and large-camp siege decisions on maps where ordinary gems are unavailable or paths are constrained.

## 4. Specific v4 code weaknesses to inspect

These are **verified code structure observations**, not all demonstrated causal explanations:

1. **PvP occurs before banking.** In `Bot::play_turn()`, `defend()` is evaluated before `bank()`. Under pressure, a carrier may spend scoring time fighting. Change only after comparing the opportunity cost of fight versus tribute.
2. **Independent target selection.** `Bot::defend()` scores visible enemies mostly by low HP, bags and distance, with no ally burst calculation or team-wide focus memory. This is consistent with V4's lack of same-round damage concentration.
3. **Under-modeled enemy abilities.** `refresh_threats()` assumes enemy threat using Strength + 35 and basic attack range + 1, not full stun/ability reach. This can leave carriers and low-health farmers exposed.
4. **Recovery may start too late.** Outside spawn, V4's regular health return threshold is 28% max HP or 180 flat, whichever is larger. Against clustered, ability-heavy teams this may not leave sufficient escape margin.
5. **Equipment rigidly favors farming.** Ordinary champions start with Monster/Jungle Strength; casters focus Power Focus. The scheme lacks a measured mode switch to survivability or PvP combat investment on contested maps.
6. **Uncertainty and claims.** Camp assignments are shared in eight bytes, but ally vision is private; plans can diverge and duplicate or delay captures.
7. **Reward estimates and siege positions were written pre-patch.** Post-patch gem/gold values, Golem and increased elk/monolith ranges change the profitability/safety of old routing. The current v5 branch began patch-safe refactoring but has not been validated under the patched server engine.

Source: [V4 combat, banking, farming and navigation implementation](../bots/Bot1/src/bot.cpp), [v4 drafting](../bots/Bot1/src/draft.cpp).

## 5. Prioritized v5 experiment queue

| Priority | Candidate change | Primary measure | Guardrail |
| --- | --- | --- | --- |
| P0 | Improve carrying/banking protection and alternate-altar path escape | Score per round; collected-to-tributed ratio; carrier deaths | Do not strand non-carriers or suppress profitable counterattacks |
| P0 | Team-assisted focus-target policy with burst/stun evaluation | Kills per death; enemy damage concentration; gem denial | Do not chase enemies at the cost of camp/altar income |
| P0 | Refit Week 2 camp utility, respawn timing and objective routing | Gold/gems by rounds 100, 200, 400; unique captures | Avoid reward-recipient-count artifacts |
| P1 | Contested-map equipment roles: durability vs monster damage vs champion damage | Survival; early gold; damage output; winning score | Preserve solo-farm breakpoints and Tavi's field economy |
| P1 | Draft role optimizer conditioned on camp topology and number of bodies | Paired win rate across all map families | Do not blindly copy nerfed Cassi/Issac/Stellar compositions |
| P1 | Contest valuable enemy-carried bags/altars when positive utility | Enemy denied gems; our gem loss; kills | No fights into superior local burst |
| P2 | Objective/siege and long-stall recovery tests | Monolith/golem score; zero-progress windows | Respect updated camp ranges and legal actions |

**Testing protocol:** Freeze unchanged V4, separate each patch as an ablation, use same maps/seeds and swapped sides, record opponent and engine version, and require statistically meaningful repeated improvements. Evaluate both traditional farming opponents and combat-heavy profiles. Do not promote v5 based only on its successful compile or two pre-patch `packs` smoke matches (which it lost).

## 6. Confidence, gaps, and follow-up research

**Directly measured:** complete-match scores/outcomes, drafts, kills/deaths, earned gold, champion damage from recorded events, gem collection/banking, first tribute, and 9 selected action-level upgrade and multi-attacker windows.

**Supported inference:** strong opponents achieve compounding economic and survival advantage, often coordinating damage on enemies and preserving their own scoring pipeline.

**Still unverified:** precise enemy planning objectives, why every enemy chose an individual target, whether target convergence was shared-memory coordination or common heuristics, the optimal specific shard sequence, the counterfactual effect of a build under another map, and how the October 20 server-side balance changes modify each tactic.

**Additional analysis worth automating next:** per-camp group capture attribution instead of recipient awards; per-champion action-space regret; time-to-score per objective; line-of-sight/ability-cooldown windows; opponent altar-lock actions; team presence around altars; map-conditioned policy clusters; low-HP retreats versus fatal combat engagements; exact gem-bag transfer/death timelines.

### Reference links

- [Replay study generated metrics](../match-data/analysis/v4-study/metrics.json)
- [Full first-pass report](../match-data/analysis/v4-study/REPORT.md)
- [Native extraction workflow](../.github/workflows/v4-replay-study.yml)
- [Selected-case tactics extraction workflow](../.github/workflows/v4-tactics.yml)
- [The October 20 Week 2 patch notes supplied in this discussion](https://2026a.battlecode.co.uk/game/patch-notes/2e172875-2)
