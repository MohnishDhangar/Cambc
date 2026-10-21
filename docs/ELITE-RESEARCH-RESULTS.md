# Elite-inspired independent BotElite research: reproducible ledger

Date: 21 October 2026. Game SDK/CLI CAMBC 3.0.1. Pinned v6.8 control: `0ddd5338b94db824f9f53261a17f020490b7017f`. Frozen v4 archive SHA-256 `b296e83d43e8b16709e655ee4470a526e9e84160ee02fbad0e8c483661e1a062`. Frozen references untouched.

## Empirical inspiration versus strategic certainty

From `research/v6-elite-strategy-audit` **strict training split** (161 distinct valid action recordings), elite teams attempted more combat, wards, movement, buying and recall commands than frozen v4. Replays remain *attempted-action* evidence, not validated success rates or proof of causation. Pentakill's frequently selected Cassi+Issac/Tavi/Varg core was also observed. Original enemy source code was not available and was not replicated. Four sealed maps never used in research/tuning: `00lanes`, `01corridors`, `01hooks`, `01islands`; 49 quarantined linked records also excluded.

## Isolated strategy ablations against pinned control

Each row is a complete 102-game 17-training-map tournament (34 candidate vs v4, 34 exact pinned control vs v4, 34 candidate vs control), same rules and two starting sides. Candidate wins and submitted-gem margin shown against v4; fuel spills and exceptions from replay stdout.

| Experiment | v4 wins | Avg margin | Fuel spills | Caught errors | Head-to-head wins vs control | Verdict |
|---|---:|---:|---:|---:|---:|---|
| Pinned v6.8 baseline | 21/34 | +91.47 | 52 | 0 | — | Frozen control |
| Elite v0: Cassi/Tavi/Varg draft | 15/34 | −32.09 | 23 | 0 | 16/34 | Reject |
| Elite v1: draft + first pressure prototype | 14/34 | −92.50 | 82 | 1166 | 15/34 vs v0, NOT v6.8 | Reject (visibility bug and regression) |
| Elite v2: guarded ally-supported early pressure, original draft | 18/34 | +42.00 | 52 | 0 | 18/34 | Reject |
| Elite v3: bush-only information-coverage warding (corrected) | 21/34 | +49.53 | 48 | 0 | 17/34 | Reject for margin regression |
| Elite v4: 120g return-to-shop vs 180g | 10/34 | −70.62 | 35 | 0 | 15/34 | Reject |
| Elite v5: skip banking when no reachable altar | 21/34 | +96.71 | 57 | 0 | 18/34 | Not promoted, zero-tribute failures persist |
| Elite v6: teammates transient in BFS field | 15/34 | −26.35 | 49 | 0 | 14/34 | Reject, zero-tribute failures persist |

## Reproducible sources

- v0 `research/elite-bot-v0-roster` / `match-data/analysis/elite-v0-roster`
- v1 `research/elite-bot-v1-pressure` / `match-data/analysis/elite-v1-pressure`
- v2 `research/elite-bot-v2-pressure-only` / `match-data/analysis/elite-v2-pressure-only`
- v3 `research/elite-bot-v3-vision` / `match-data/analysis/elite-v3-vision`
- v4 `research/elite-bot-v4-shop-cycle` / `match-data/analysis/elite-v4-shop-cycle`
- v5 `research/elite-bot-v5-productive-fallback` / `match-data/analysis/elite-v5-productive-fallback`
- v6 `research/elite-bot-v6-allied-navigation` / `match-data/analysis/elite-v6-allied-navigation` (102 games completed; rejected)

Each branch includes its complete `bots/BotElite/src/` six-file source, a paired `tools/benchmark_*.py` and CI workflow. The independent BotElite tree does not modify frozen v4/v5 or deployed v6.8. The source ZIPs under `releases/elite/` contain exactly `src/*.cpp`/`src/*.h`, tested by GitHub CI.

## Conclusions and next high-value research

1. The observed elite action-frequency gap alone is not a valid optimization objective: unspecialized aggression, draft imitation, ward scoring and early shopping harmed outcomes. Need opponent action *success/outcome* data and per-turn state to attribute their advantage.
2. Pinned v6.8 still yields zero tributed gems against frozen v4 on `00contest`/ `01boss-battle` on both training sides. In training-only action traces for `01boss-battle`, carriers held 8–23 gems and repetitively attempted navigation without progress for the remainder of 2,000 rounds. Pure no-altar fallback v5 does not resolve those cases. Dynamic teammate/pathfinding congestion is a separate v6 ablation.
3. Performance against actual elite opponents is a separate evaluation problem. Their binaries are unavailable; do not claim performance from v4-only score or silently use held-out map replays for optimization.
4. A genuinely different elite-strength candidate must demonstrate improvements in complete capture-to-bank conversion, productive map goals, coordinated fights, and safe resource logistics — not merely added commands.

**Promotion status: no elite-derived candidate is currently proven superior to pinned v6.8.** All variants remain experimental until reproducibly better against multiple opponents with acceptable runtime reliability.

## Follow-up bottleneck hypothesis after v6

Both no-reachable-altar fallback (v5) and ally-through-BFS (v6) failed to produce any gem tributes on training maps `00contest`/`01boss-battle`. Avoid repeating guesses about pathfinding. Instrument map altar count and each champion's distance-field reachability, goals, terrain component, selection target and bank action outcomes at key intervals, then reproduce a single frozen scenario. Test coordinated capture + bank logistics only after root cause is observed. For real high-Elo transfer, first confirm elite replay outcomes and correlate successful combat/ward/recall actions with gem-scoring trajectories rather than superficial action counts.
