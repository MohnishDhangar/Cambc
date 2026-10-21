# CAMBC field diagnostics and v6.21 bank-access breakthrough

Status: 21 October 2026. Frozen baselines: pinned v6.8 `0ddd5338b94db824f9f53261a17f020490b7017f`, frozen v4 archive SHA256 `b296e83d43e8b16709e655ee4470a526e9e84160ee02fbad0e8c483661e1a062`. SDK 3.0.1.

## User-provided field archives

`elite-v3-match-data.zip`: 50 distinct raw replays; candidate stdout 68 fuel-spill markers, zero caught bot exceptions.
`elite-v5-match-data.zip`: 60 distinct raw replays; candidate stdout 97 fuel-spill markers, zero caught bot exceptions.
These are unsupervised runtime facts; no current-engine outcome or map/score information has been verified for all uploads. To protect the sealed four-map holdout, classify only against **17 permitted map fingerprints** and quarantine every unrecognized replay. Fingerprint classification confirmed 17 v3 and 27 v5 games as matches to permitted map binaries; 33 games from each archive remained unclassified/quarantined and did not influence tuning. Among the positively identified permitted replays, there were 24 and 21 fuel-spill markers respectively.

## Deterministic training-map root cause

The earlier permitted-map action trace showed gem carriers frozen from rounds 200–2000 on `01boss-battle`, repeating bank-`navigate` with unchanged position. Follow-up `research/v6-altar-goal-blockers` instrumented exact v6.8, both starting sides against frozen v4, and logged the same underlying pattern on 73 sampled blocked calls: **9 theoretical altar-approach tiles, 8 permanently terrain-blocked, 1 occupied by a living camp**, no champion or teleport occupants. Once occupied goals were stripped, `navigate()` returned false without BFS and `bank()` returned true, preempting farming, attacking the obstructing camp and other productive work.

## Rejected intermediate controls

- v6.18 watchdog: 21/34 vs v4, +103.53 mean gem margin, zero on boss-battle, 53 fuel-spill events. Did not solve blocked access.
- v6.19 approximate route camp selection: identical scores to v6.18, 57 spills. Rejected.
- v6.20 supported-fight heuristic: 11/34 vs v4, −149.29 mean margin, 51 spills, zero exceptions. Rejected; naive nearby ally/enemy counts are inadequate.

## v6.21 isolated, reproducible result

A specific strategy in `bots/Bot6/src/bot.cpp` checks when all terrain-legal altar approaches are occupied and selects a camp **physically stationed on the blocked altar approach**, approaches its firing range and attacks it until clearance. If no productive bank action is available, it permits alternate work instead of committing the entire turn to failed navigation. No other source file changed relative to pinned v6.8.

102-game tournament (17 permitted maps × A/B × 3 pairings):
- v6.21 vs frozen v4: **21/34 wins, +108.71 mean submitted-gem margin, 52 fuel spills, 0 caught exceptions, 0 engine faults**.
- pinned v6.8 vs v4: **21/34, +91.47, 52 spills, 0 exceptions/faults**.
- v6.21 vs v6.8: **18/34 wins, +31.65 gem margin, 55 fuel spills**.
- `01boss-battle`: side A improves **0→840 tributed gems** and side B **0→595**, with two wins vs v4. Once the route opens, v4 itself can also tribute: 487 and 362 in those games. This makes access control and protecting the opener relevant for genuine elite competition.
- `00contest` remains **0 gems on both sides**. Overall v4 win count unchanged; improvements do not establish general dominance or results against live high-Elo binaries.

## Next acceptance criteria

1. Test v6.21 against the live similar/high-Elo field pool and record paired results by opponent/map/side. It is a **field-test candidate**, not declared superior.
2. For `00contest`, inspect monolith range/damage/capture readiness and stage cooperative siege without wasting ordinary-map farming.
3. Optimize gem-bearing capture-to-tribute rate, gold economy at rounds 200/400, deaths, carrier losses, productive action rate, fuel faults and channel/altar-lock interruptions.
4. Opponent support must be based on **attacks that are reachable and useful**, not just local body count; previous copied elite-draft, ward and shop heuristics regressed.
5. Keep four maps `00lanes`, `01corridors`, `01hooks`, `01islands` sealed until final frozen evaluation. GitHub commit/replay manifests remain source of truth.

The input `REPORT.md` and `V6-STRATEGY.md` supply further opponent observations, but include aggregate measurements from a historical set containing a protected Islands match. Those unfiltered aggregate counts must not be used to tune new policies. Restrict development analysis to already permitted named maps or provenance-quarantined training subsets.
