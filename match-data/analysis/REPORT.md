# Original Bot1 lobby analysis — verified with engine 0.0.3

This report concerns the original bot used in the supplied matches. Its source is preserved in `bot-v1-source/`. The current strategy update is documented in [Bot1 v2](../../bots/Bot1/STRATEGY.md).

The two lost series have several distinct causes: a banking deadlock on `rows`, repeated combat deaths on contested maps, a missing coordinated objective on the monolith map, and one close delivery race. The updated client now lets us establish the complete results of every supplied game.

## Evidence and client setup

CAMBC **2.2.5** is installed inside this project. It includes the official **0.0.3** replay engine. All **15 original recordings** loaded directly and reached a game outcome with **zero replay errors**. No headers, draft records, or gameplay inputs were converted. All source SHA-256 hashes match those saved before this update.

The extractor uses the official engine and the snapshot decoder from its bundled viewer. Champion statistics are checked against the full final snapshot, champion tribute totals against team scores, and champion turn counts against an independent parser of the original action records. Across all 15 games, gem balance differences also match gems lost in recorded death events.

To use the updated client in Bash:

```bash
cd /home/mohnish/Y
source tools/activate-cambc.sh
cambc --version
```

`./tools/cambc` also works without shell activation. The SDK is refreshed to `2.2.5`, and the unchanged Bot1 source compiles with it. The new build is `.cambc/Bot1-client-2.2.5.wasm`. Existing upload artifacts remain unchanged. The previous SDK, maps, configuration, and bots are backed up in `.cambc/before-client-2.2.5.tar.gz`.

Initialization reused the already cached WASI SDK 33, CMake, and Ninja. Published map downloads were skipped because this environment cannot resolve download hosts. This does not affect analysis: each original replay contains its own map. Run `cambc maps pull` when connected to refresh the published pool.

The earlier engine-0.0.1 reconstruction is retained separately as historical evidence. Its report is [REPORT-provisional.md](REPORT-provisional.md); the authoritative data are now under [native-0.0.3](native-0.0.3/RESULTS.md).

## Complete results

Scores list Bot1 first. Deaths count champion bodies, including camp deaths and linked Cassi/Issac deaths. A death count therefore need not equal the opponent's credited kills.

| Opponent | Game | Round | Score | Bot1 kills / deaths | Bot1 gems lost on death |
| --- | --- | --- | --- | --- | --- |
| Forged Tokens | 1 | 568 | 1,018–724 | 0 / 0 | 0 |
| Forged Tokens | 2 | 429 | 462–1,056 | 0 / 0 | 0 |
| Forged Tokens | 3 | 748 | 220–1,002 | 1 / 25 | 452 |
| Forged Tokens | 4 | 571 | 396–1,008 | 1 / 17 | 252 |
| Forged Tokens | 5 | 453 | 462–1,024 | 0 / 15 | 256 |
| lll | 1 | 800 | 228–1,020 | 0 / 19 | 0 |
| lll | 2 | 1,931 | 0–1,000 | 3 / 93 | 0 |
| lll | 3 | 568 | 1,018–760 | 0 / 0 | 0 |
| lll | 4 | 464 | 964–1,004 | 0 / 0 | 0 |
| lll | 5 | 475 | 540–1,044 | 0 / 7 | 0 |
| know | 1 | 568 | 1,018–824 | 0 / 0 | 0 |
| know | 2 | 653 | 396–1,023 | 1 / 1 | 0 |
| know | 3 | 541 | 1,018–958 | 2 / 5 | 88 |
| know | 4 | 700 | 1,096–854 | 10 / 16 | 634 |
| know | 5 | 971 | 1,030–894 | 11 / 7 | 120 |

The original series outcomes are confirmed: **1:4 against Forged Tokens, 1:4 against lll, and 4:1 against know**.

## 1. A banking deadlock explains much of the rows failure

**Forged Tokens, game 2:** 462–1,056 at round 429, with zero champion deaths on either side.

| Champion | Interval near (22,2) / (22,3) | Turns | Carried gems |
| --- | --- | --- | --- |
| Varg | 189–303 | 115 | 66 |
| Vendetta | 233–303 | 71 | 66 |

Both remain alive, with constant health and no recall or tribute channel running. Varg moves only twice during his interval; Vendetta moves once. They eventually bank, but lose many rounds of farming and scoring. Tavi contributes zero gems despite earning and spending 420 gold. Bot1 collects only 528 gems in total, compared with the opponent's 1,056.

**The same bug recurs much more severely against know, game 2:**

| Champion | Interval near the same location | Turns | Carried gems |
| --- | --- | --- | --- |
| Varg | 189–586 | **398** | 66 |
| Vendetta | 233–586 | **354** | 66 |

Varg's first 21 turns are at `(22,2)`, then 377 consecutive turns at `(22,3)`. Vendetta spends 354 consecutive turns at `(22,2)`. Their health and bags remain unchanged throughout these intervals. This game ends 396–1,023 at round 653. The recurrence against a team we otherwise beat makes the pathfinding failure especially clear.

Three code choices explain the deadlock:

1. [Threat inference](bot-v1-source/bot.cpp:198) treats missing camp health as continued aggression. Damaged monsters can go back to sleep after two rounds without taking damage.
2. [Navigation](bot-v1-source/bot.cpp:216) computes a distance field without danger, then adds danger only when choosing the next tile. It accepts only a strictly decreasing score. A safe detour can initially increase distance or leave it unchanged.
3. [Stall recovery](bot-v1-source/bot.cpp:488) requires an assigned camp target. [Banking](bot-v1-source/bot.cpp:372) clears that target, so carriers cannot trigger recovery.

At `(22,3)`, distance to an altar approach is 15. North leaves it at 15 and is rejected. West reduces it to 14, but a modeled 20-damage wolf adds 40 risk points, so it is also rejected. A safe route around the modeled danger exists. The [visual explanation](findings.svg) shows this local minimum.

**Fix first:** use a route planner that accounts for risk over the whole route, derive camp danger from current awake state, and recover from lack of progress while banking and retreating. If the bot reaches an altar approach but refuses tribute, it also needs to choose a safe alternative approach or altar.

## 2. Contested maps expose severe combat and survival problems

**Forged Tokens, games 3–5:** Bot1 suffers **57 champion deaths**, earns only **two kills**, and loses **960 carried gems** across the three games. The per-game losses are 452, 252, and 256 gems. These totals are confirmed both by champion resource balances and by individual death events.

Our first deaths occur at rounds 42, 94, and 38 respectively. The problem starts early and continues through repeated respawns. It costs both carried resources and time that could have produced new resources.

**lll, games 1 and 5:** Bot1 suffers 19 and seven deaths respectively. No gems are lost on those deaths: combat pressure also prevents champions from collecting resources in the first place. In game 5, Varg produces 474 of our 540 gems; Tavi and Vendetta contribute only 22 and 44 while dying three and four times. The rest of the squad is contributing little to the objective.

Relevant implementation weaknesses are visible in the source:

- [Enemy selection](bot-v1-source/bot.cpp:337) scores an individual nearby target without comparing nearby allied and enemy strength, health, or available abilities.
- [Combat precedes banking](bot-v1-source/bot.cpp:493), allowing carriers to spend scoring time in avoidable fights.
- [Recovery](bot-v1-source/bot.cpp:484) normally starts below 28% health, which can be too late against grouped damage and stuns.
- [Enemy danger](bot-v1-source/bot.cpp:196) uses basic attack range plus one, omitting spell ranges, dashes, and stun chains.
- Purchases initially emphasize camp clearing. Tavi's field purchases do not add health in the current implementation.

Fourteen opponent drafts include Cassi & Issac and therefore create an extra body. This is relevant to action economy, but does not explain every loss: lll's monolith game uses five bodies on each side, and we also win games against Cassi & Issac.

**Fix:** estimate local team strength and incoming burst before fighting, protect gem carriers, and retreat earlier when outmatched. Rejoining after respawn needs a safe destination and nearby support; returning to repeated unfavorable contact does not recover the lost farming time.

## 3. The monolith map combines a missing objective with a combat collapse

**lll, game 2:** Bot1 loses **0–1,000** after 1,931 rounds, with **three kills and 93 deaths**. We collect **zero gems** for the entire game and make **zero tribute starts**. The opponent makes five tribute starts, collecting and submitting 1,000 gems.

The map contains gold clusters and monoliths, with monoliths supplying all camp gems. The [camp selector](bot-v1-source/bot.cpp:160) requires a safe solo target before its cooperation fallback can join an already assigned live camp. It has no way to seed a team objective when every champion rejects the monolith individually.

The complete replay also shows that our gold opening fails under pressure. Lifetime team gold is **1,759 versus 18,400**. Our first death occurs at round 36. By round 500 we have earned only 750 gold, against 3,840; by round 1,000 it is 1,114 against 8,505. Farming gold does not turn into sufficient strength, a coordinated clear, or eventual score.

**Fix:** classify maps by their gem sources, organize a protected gold opening, and schedule a team rendezvous for a monolith clear. Assess combined damage and survival, coordinate capture and banking, and account for enemy pressure during assembly. This requires the survival improvements above as well as an objective planner.

## 4. One loss is a close farming and delivery race

**lll, game 4:** 964–1,004 at round 464, with zero deaths on either side.

| Metric | Bot1 | lll |
| --- | --- | --- |
| Collected gems | 1,022 | 1,048 |
| Tributed gems | 964 | 1,004 |
| Carried gems at the end | 58 | 44 |
| Lifetime gold | 4,505 | 4,300 |

The 58 carried gems do not imply an immediate available win. Tavi starts tributing 22 gems at round 463, too late to finish before the game ends. Varg captures the remaining 36 at round 464 and still needs travel and channel time.

**Fix:** shorten the full farming-to-altar cycle and make banking decisions with the opponent's likely finishing time in mind. The collection deficit is only 26 gems. Higher gold income did not translate into a faster score.

## 5. Why the 4:1 win is consistent with these weaknesses

All three series contain the same 80×80 farming map. Bot1 wins it at round 568 with exactly **1,018 gems**, with zero deaths on either side; the opponents finish at 724, 760, and 824. Our opening is repeatable when it is not disrupted.

Against know, we also win games with some combat losses. Game 3 ends 1,018–958 despite five deaths; game 4 ends 1,096–854 despite 16 deaths and 634 lost gems. Farming and delivery can overcome casualties in a weaker matchup. The lost `rows` game still exposes the same banking deadlock.

The competition results therefore support improving specific decision failures. They do not support treating the original starter-only sweep as an estimate of strength against lobby opponents.

## Runtime findings

Across all 15 original matches, Bot1 has no stdout `bot error` or `fuel spill` messages and **zero fuel-exhaustion turn boundaries**. All original action logs consume correctly and agree with native replay turn counts.

The losses are explained by decisions and resulting game state. There is no evidence here that fuel exhaustion or a bot crash caused them. Actionless turns require context: death, capture, healing, and channeling can all make them legitimate.

## Recommended implementation order

1. Fix risk-aware routing, actual camp awake-state handling, and progress recovery for carriers and retreating champions. The two `rows` games supply concrete examples.
2. Add local team-aware fight/escape decisions, carrier protection, and safer behavior after respawn. The contested losses show large survival and income costs.
3. Add explicit collective objectives for monolith-only gem maps, including a protected opening and rendezvous.
4. Improve endgame farming and banking timing for close races.
5. Evaluate draft and purchase variants against contested maps and relevant opponents, including Cassi & Issac and healing support.

The subsequent strategy update implements these plans; see [Bot1 v2](../../bots/Bot1/STRATEGY.md). The match results above remain evidence about the original bot.

## Artifacts and reproduction

- [Complete native results](native-0.0.3/RESULTS.md)
- [Native summaries](native-0.0.3/summaries.json)
- [Derived diagnostics and carrier stalls](native-0.0.3/diagnostics.json)
- [Visual explanation](findings.svg)
- [Independent original-action metrics](recorded-action-metrics.txt)

Each native game folder contains `summary.json`, `events.json`, `turns.json`, `rounds.json`, and the embedded map. The summaries record the original replay hash, engine hash, input count, and completion status.

Run from the workspace root:

```bash
node --no-warnings match-data/analysis/extract_native_replays.mjs
python3 match-data/analysis/native_diagnostics.py
python3 match-data/analysis/plot_findings.py
```

The older `extract_replays.mjs` is retained only for reproducing the provisional analysis. Use the native extractor above for these recordings.
