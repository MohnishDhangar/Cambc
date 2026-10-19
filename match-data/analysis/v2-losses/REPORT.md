# Bot1 v2 failure analysis

## The uploaded filename was correct

`Bot1-v2.zip` was the intended v2 source submission. The local archive matches the recorded release SHA-256:

```text
92bee128ea6bd48f58c03a7fa30f6496e98c52aa711227dbe54ab3067cb9f324
```

Every supplied game logs `Bot1 strategy v2 (SDK 2.2.5)` and the recorded drafts agree with v2. The evidence points to failures in the released implementation, rather than selection of the wrong file. The platform's uploaded archive itself is not present for a separate byte comparison.

All 15 original replays were decoded directly with the official engine 0.0.3. Each reaches an outcome with zero replay errors. Original replay hashes remain unchanged. [Complete results](RESULTS.md), [native summaries](summaries.json), and [derived action diagnostics](diagnostics.json) are retained alongside per-game events and champion turns.

The results confirm **0:5 against german, 0:5 against literallyafk, and 0:5 against princess-donut**. These are different map/opponent samples from the original v1 matches, so the series scores alone are not a controlled v1/v2 comparison. The specific defects below are independently visible in the recordings and source.

## 1. V2 exceeded the actual turn budget

The original input logs contain **63 Bot1 fuel-exhaustion boundaries** across five games. Stdout contains **61 fuel-spill messages** and **two caught action errors**. These counts measure different things: a suspended turn does not necessarily print a spill message before the game ends.

| Opponent / game | Fuel exhaustions |
| --- | --- |
| german 2 | 13 |
| german 3 | 3 |
| literallyafk 4 | 15 |
| princess-donut 1 | 14 |
| princess-donut 4 | 18 |

The original v1 recordings had zero fuel-exhaustion boundaries. V2 introduced several sources of extra work:

- [Initialization continued into a complete gameplay decision](../v2-source/bot.cpp:874), using the first-turn budget for both map setup and ordinary decisions. On the 71×71 map, all five champions log an initial spill from round 1 to round 2.
- [Detailed allied fighter models were built on every turn](../v2-source/bot.cpp:345), even when no enemy or team objective needed them. These models repeatedly query health, strength, focus, cooldowns, and ability metadata.
- [Navigation sorted candidates with a comparator that called the SDK](../v2-source/bot.cpp:461). Repeated distance reads, full fields, and fresh occupancy masks consumed the fuel intended for movement. A dash could also trigger a second full threat-model rebuild.

The rules suspend execution on exhaustion and resume it in a later round. Saved positions, availability checks, and local variables can then refer to an earlier state. The two caught errors in german game 3 occur at navigation actions: `Champion cannot act` and `Invalid metadata, alignment, overlap or argument`. They are consistent with invalid actions following suspended execution; the recordings do not expose a native stack trace proving the precise origin of each argument failure.

**Repair implemented:** restore initialization as its own turn, omit unnecessary allied combat models, stop native searches once they reach the champion, compute each candidate cost once, refresh occupancy after hidden-obstruction failures, reserve more action fuel, provide a bounded low-budget movement fallback, and reject navigation/actions when the recorded decision round is stale.

## 2. Carriers moved without making delivery progress

**german game 5, Marcella:** a bag of 22 gems remains unchanneled for **356 consecutive turns, rounds 130–485**. Around rounds 145–157 she repeatedly alternates between `(21,14)` and `(22,15)`. Her health remains 1,160 during that initial loop. The game finishes 88–1,018.

V2's [banking recovery](../v2-source/bot.cpp:631) relied partly on staying on the same tile. Moving back and forth reset that counter. Its navigation progress record was also shared across different goals. More seriously, the main turn could choose escape when a threat entered range, then immediately resume its original altar route after one safe step. A carrier could alternate between two incompatible objectives without committing to a safer delivery route.

**Repair implemented:** track repeated positions over a short history, give banking its own best-distance and progress timer, penalize an altar after a failed approach, and retain escape intent for several turns. An enemy-induced retreat now invalidates the blocked altar choice rather than repeatedly approaching it again.

This is a different failure from v1's stationary `rows` deadlock. Fixing the missing-health threat inference did not prevent this new moving loop.

## 3. The monolith rally started before the squad could afford it

**german game 3:** 0–400 at the round-2,000 limit, with **47 Bot1 deaths and zero collected gems**.

The [rally became available at round 150](../v2-source/bot.cpp:683), independently of the squad's equipment. At round 149, our entire team had earned only **385 gold**, against 750. That is insufficient to give five champions their intended core equipment.

The diagnostics show repeated failed rallies. One reports `ready=1`, estimated incoming damage about 48,561, and only 425 usable health. These were explicit evidence that the party could not attempt the clear. Repeated travel and regrouping diverted champions from earning the equipment that would make a later clear possible. By round 500, lifetime team gold was only **560 versus 3,165**.

The local survival check prevented an immediate reckless clear, but it was placed after the expensive journey. The plan could therefore starve its own opening without ever attacking the objective successfully.

**Repair implemented:** advertise individual equipment readiness through shared memory. Starting a new rally requires enough equipped participants and an equipped healer. Core camp damage and camp mitigation are bought before optional durability upgrades. Gold captures already in progress are allowed to finish. The actual nearby-party survival check is retained before engaging.

## 4. Fight estimates were biased against our own squad

V2 added ready burst damage to the enemy side of the local damage comparison, while our side used average damage and healing. It then applied another safety multiplier. This could discourage defending even when the actual teams were comparable.

Retreating was not sufficient protection: our total basic attacks directed at champions were often very low while enemies kept landing hits during pursuit. german game 1 records eight of our basic attacks on champions versus 177 from the opponent; game 5 records zero versus 46. These are attack counts, not damage totals.

**Repair implemented:** use the same average-damage and ready-burst terms for both teams and apply consistent distance weighting. Carriers retain an additional safety margin. Escape hysteresis and altar replanning address the repeated retreat/approach cycle.

## 5. Farming also regressed when there was no combat loss

Three games have **zero Bot1 deaths and zero fuel exhaustion**, yet still finish:

- literallyafk 2: **528–1,056**.
- princess-donut 2: **564–1,044**.
- princess-donut 5: **648–1,008**.

The losses cannot all be attributed to crashes, fuel, or combat casualties. For example, on `rows` against literallyafk, Varg collects 561 gems while Tavi and Ryth collect none. Tavi spends 485 of 536 turns moving, produces only 27 turns with a recorded attack or cast, and never acquires a gem. Marcella finishes carrying 66 gems.

V2 also replaced the farming draft on almost every supplied map, using a broad geometry classification. It moved defensive shopping ahead of camp mitigation and introduced more conservative solo-camp estimates. The relative effects of these choices require local comparisons; the recordings alone cannot assign a precise score cost to each change.

**Repair implemented:** restore the original ordinary-map farming core and its early Monster/Jungle equipment order. Keep the specialized healer draft for monolith-only gem maps. A ranged helper can account for an actually present, healthy melee tank on the same camp, reducing the chance of harmless gold work permanently excluding it from gem farming.

## Release and validation status

The frozen v2 source is preserved under [v2-source](../v2-source/bot.cpp). Its ZIP and compiled module remain available for comparisons. The repair is implemented as **strategy v3** in `bots/Bot1/src/` and compiles with CAMBC/SDK 2.2.5 in release mode.

**V3 has not yet been exercised in local match simulations.** The candidate source archive [Bot1-v3.zip](../../../bots/Bot1/Bot1-v3.zip) was packaged at the user's request. Packaging and compilation do not establish gameplay performance.

The useful first comparisons are release-mode matches at the default fuel budget on the supplied 71×71, `rows`, 41×41 carrier-loop, and monolith maps. Both v1 and v2 should remain opponents/baselines, followed by the broader starter sweep. These can establish runtime reliability and local regressions; they cannot establish a lobby win rate against unavailable opponent implementations.

The earlier v2 release was compiled but not played locally. That allowed these implementation regressions to reach the uploaded bundle. A successful compile did not establish that its strategy or fuel budget worked in matches.

## Reproduction

```bash
node --no-warnings match-data/analysis/extract_native_replays.mjs \
  match-data/losses match-data/analysis/v2-losses
```

Each game's native folder contains the original map extracted from its recording. The independent original-action parser supplies turn and exhaustion counts; those turn counts were checked against the native engine for every champion in these matches.
