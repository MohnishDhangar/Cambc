# Elite-influenced BotElite v0: composition ablation

Based on pre-existing permitted-map elite-opponent action dataset: 161 unique training replays, four held-out maps excluded by provenance quarantine. The Pentakill subset shows Cassi & Issac and Tavi selected 43/43; Varg 38/43. These are frequency observations **not estimated causal advantage or source-code cloning**.

## Change from reference
A new and independent `bots/BotElite/src/` source tree is pinned to exact v6.8 revision `0ddd5338b94db824f9f53261a17f020490b7017f` for all C++ files except `draft.cpp`. On *non-objective* maps only, draft prioritizes Cassi & Issac, Tavi, Varg, then baseline backups. Objective draft and match-time executor are identical to v6.8. This isolates composition and champion-specific synergies from more speculative tactical logic.

## Controlled tournament
SDK CAMBC 3.0.1. 17 allowed training maps, both starting sides. 34 candidate-vs-v4, 34 pinned-v6.8-vs-v4, 34 candidate-vs-pinned-v6.8. Saves scores, wins, engine errors, exceptions, and fuel spills in `match-data/analysis/elite-v0-roster`. Only build further features on this roster if direct outcomes justify it; otherwise retain an independent elite-inspired strategy branch but restore baseline draft. Frozen v4/v5 untouched. Excluded from all tuning: `00lanes`, `01corridors`, `01hooks`, `01islands`.

## Next independent candidate modules
1. **Elite tactical contact**: early opportunistic champion pressure under allied-number/health advantage; must not cause carrier deaths.
2. **Vision activity**: information-oriented ward placement during camp-search and safe movement, not just at end of farm.
3. **Economy uptime**: objective and camp-progress watchdog, shopping/recall ROI, safer high-value carrier delivery.
Independent ablations required. Do not label the bot elite-strength simply because it imitates superficial frequency metrics.
