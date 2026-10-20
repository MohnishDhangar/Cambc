# CAMBC Bot1 v4 — Opponent Replay Study

> **Engine:** archived CAMBC 0.0.3 (pre–Week 2 balance). Generated from native replay records. This report is observational, not a causal test of proposed strategies.

## Data quality
- Folders found: **1**. Native decoding: **1**. Analysis: **1**. Distinct replay SHA-256 values: **1**.
- Decode failures: **0**. Metric extraction failures: **0**. Duplicate replays: **0**. Folder outcome mismatches: **0**.
- Team A is assumed to be Bot1 v4 based on verified repository stdout samples; verify all stdout if applying this report beyond exploratory use.
- The categories are a selected set of wins/losses, not random samples. Do not interpret category win rates as an Elo estimate.

## Outcome and efficiency by replay category

| Category | Unique games | Median score Bot1–Opp | Median gold Bot1–Opp | Median first tribute Bot1–Opp | Median deaths Bot1–Opp | Median captures Bot1–Opp |
|---|---:|---|---|---|---|---|
| higher-elo/losses | 1 | 60–1,020 | 1,425–3,970 | 213–44 | 24–7 | 13–17 |

## Early advantage (opponent minus Bot1 score)

| Category | Median advantage by round 100 | By round 200 | By round 400 (games lasting ≥400) |
|---|---:|---:|---:|
| higher-elo/losses | 60 | 120 | 360 |

## Repeated opponent mechanisms — observations to test

The following patterns are **hypotheses** supported by recorded differences in resources or timing. They do not prove a particular opponent decision policy. First prioritize replay-level reconstruction where the effect size is large.

1. **Opening tempo and first-tribute lead.** Compare first reward pickup, first capture, first tribute and score checkpoints. A large lead before round 200 suggests a draft, route, camp-selection or upgrade difference rather than late-match PvP.
2. **Economic throughput.** Compare gold earned and capture counts separately from gems secured. Faster gold accumulation suggests efficient farm selection and better upgrades; without item chronology this is not evidence of a specific shard purchase policy.
3. **Resource securing versus risk-taking.** Compare captured/collected gems, bank ratio, gem loss on deaths, and stationary carrying episodes. Contested altar losses may be due to navigation or enemy lock timing; quantify before assuming a tactic.
4. **Pressure versus passive farming.** Compare opponent champion damage and attacks, but do not assume attacks are on champions without inspecting target-specific records. Champion kills now pay more gold under Week 2.
5. **Draft specialization.** Compare opponent champion compositions within a map hash and opponent group, rather than applying one universal roster. Composition frequency in selected elite losses alone does not prove the champions caused victory.

## Opponent champion pick frequency

### higher-elo/losses

| Champion | Bot1 appearances | Opponent appearances |
|---|---:|---:|
| Cassi | 0 | 1 |
| Stellar | 0 | 1 |
| Ren | 0 | 1 |
| Issac | 0 | 1 |
| Ryth | 1 | 1 |
| Varg | 1 | 0 |
| Tavi | 1 | 0 |
| Vendetta | 1 | 0 |

## High-Elo opponent profiles (aggregated over each five-game group)

| Group | Median score Bot1–Opp | Opp median gold | Opp median first tribute | Opp avg captures | Opp roster frequency |
|---|---|---:|---:|---:|---|
| team-1 | 60–1,020 | 3,970 | 44 | 17.0 | Ren(1), Stellar(1), Cassi(1), Issac(1), Ryth(1) |

## Match-level evidence targets

### Strongest early score leads
- \`higher-elo/losses/team-1/01-dc3936e1-8d1d-44e6-a0f6-1eff108365ce\`: round 200 score Bot1 0, opponent 120.

### Largest opponent capture lead
- \`higher-elo/losses/team-1/01-dc3936e1-8d1d-44e6-a0f6-1eff108365ce\`: captures Bot1 13, opponent 17; final [60, 1020].

### Stationary gem carriers (Bot1)

## Prioritized v5 experiments (not yet measured)

1. **Fix objective throughput before combat:** first identify the earliest systematic losing checkpoint by map and opponent; test path/camp changes on paired seeds.
2. **Tune bank/tribute routing:** ensure a gem carrier can escape local minima and select alternative altars when a lock or threat blocks the closest approach.
3. **Test opponent-informed drafting:** map-conditional variants using the most effective draft archetypes; separately account for the Week 2 champion/stat changes.
4. **Add combat opportunism conditionally:** quantify which opponents gain via invades/kills, and test against carry-loss risk after the Week 2 kill-gold buff.
5. **Rebalance farm valuation for Week 2:** new gem values and 120-HP gem clusters change optimal farming loops; benchmark against frozen v4 only as a pre-patch regression, not as a post-patch estimate.

## Reproduction and caveats

- This study uses \`match-data/analysis/extract_v4_study.mjs\` and \`match-data/analysis/summarize_v4_study.py\`; metric data and traceable replay identifiers are in \`metrics.json\`.
- Numbers are a first-pass quantitative screening, not proof that an opponent action was intentional, optimal, or legally observable to the bot.
- Original map hashes, replay SHA-256 fingerprints and exact relative replay paths are recorded for follow-up deep dives.
