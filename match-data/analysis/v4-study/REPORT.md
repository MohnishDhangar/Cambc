# CAMBC Bot1 v4 — Opponent Replay Study

> **Engine:** archived CAMBC 0.0.3 (pre–Week 2 balance). Generated from native replay records. This report is observational, not a causal test of proposed strategies.

> **Important correction (20 October 2026):** The folder labels were checked against the engine's actual winner in all 245 matches, with Team A identified as Bot1 v4 in every match. **46 folder labels disagree with engine outcomes**; the 44 cited below was based on tributed score comparisons and did not handle tied-score tiebreaks correctly. The category aggregates below use the *original directory labels* and should not be treated as true win/loss stratifications. Use the [reconciled outcome report](reconciliation/RECONCILIATION.md) and [per-match CSV](reconciliation/manifest.csv) for corrected classifications.

## Data quality
- Folders found: **245**. Native decoding: **245**. Analysis: **245**. Distinct replay SHA-256 values: **245**.
- Decode failures: **0**. Metric extraction failures: **0**. Duplicate replays: **0**. Folder outcome mismatches: **44**.
- Team A is assumed to be Bot1 v4 based on verified repository stdout samples; verify all stdout if applying this report beyond exploratory use.
- The categories are a selected set of wins/losses, not random samples. Do not interpret category win rates as an Elo estimate.

## Outcome and efficiency by replay category

| Category | Unique games | Median score Bot1–Opp | Median gold Bot1–Opp | Median first tribute Bot1–Opp | Median deaths Bot1–Opp | Median captures Bot1–Opp |
|---|---:|---|---|---|---|---|
| higher-elo/losses | 120 | 356–1,020 | 2,315.5–3,882.5 | 73–73 | 8.5–0 | 17.2–25.7 |
| same-elo/losses | 75 | 564–1,018 | 3,142–3,695 | 73–76 | 8–2 | 22.6–28.7 |
| same-elo/wins | 50 | 1,013–829 | 4,358–3,560.5 | 77–87.5 | 4–1.5 | 27.9–29.3 |

## Early advantage (opponent minus Bot1 score)

| Category | Median advantage by round 100 | By round 200 | By round 400 (games lasting ≥400) |
|---|---:|---:|---:|
| higher-elo/losses | 16 | 121 | 322 |
| same-elo/losses | 0 | 30 | 82 |
| same-elo/wins | 0 | 0 | 0 |

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
| Stellar | 6 | 114 |
| Issac | 0 | 107 |
| Cassi | 0 | 107 |
| Varg | 120 | 86 |
| Ren | 6 | 83 |
| Ryth | 91 | 75 |
| Tavi | 120 | 38 |
| Vendetta | 114 | 17 |
| Prism | 6 | 11 |
| Marcella | 0 | 4 |
| Willow | 0 | 3 |
| Vesper Vale | 77 | 2 |

### same-elo/losses

| Champion | Bot1 appearances | Opponent appearances |
|---|---:|---:|
| Issac | 0 | 62 |
| Cassi | 0 | 62 |
| Varg | 75 | 58 |
| Stellar | 3 | 57 |
| Ren | 3 | 48 |
| Ryth | 57 | 45 |
| Tavi | 75 | 31 |
| Vendetta | 72 | 24 |
| Marcella | 0 | 5 |
| Willow | 0 | 4 |
| Prism | 3 | 2 |
| Vesper Vale | 49 | 1 |

### same-elo/wins

| Champion | Bot1 appearances | Opponent appearances |
|---|---:|---:|
| Stellar | 2 | 48 |
| Issac | 0 | 45 |
| Cassi | 0 | 45 |
| Ren | 2 | 40 |
| Varg | 50 | 36 |
| Tavi | 50 | 31 |
| Ryth | 42 | 25 |
| Vesper Vale | 38 | 6 |
| Vendetta | 48 | 3 |
| Prism | 2 | 0 |

## High-Elo opponent profiles (aggregated over each five-game group)

| Group | Median score Bot1–Opp | Opp median gold | Opp median first tribute | Opp avg captures | Opp roster frequency |
|---|---|---:|---:|---:|---|
| team-1 | 88–1,020 | 3,970 | 44 | 21.0 | Stellar(5), Cassi(5), Issac(5), Ren(4), Ryth(3) |
| team-10 | 362–1,026 | 4,000 | 89.5 | 27.6 | Stellar(5), Cassi(5), Issac(5), Varg(5), Ryth(5) |
| team-11 | 290–1,018 | 3,530 | 62 | 22.2 | Ren(5), Stellar(5), Cassi(5), Issac(5), Varg(3) |
| team-12 | 360–1,020 | 3,860 | 140 | 28.4 | Cassi(5), Issac(5), Varg(5), Ren(5), Stellar(4) |
| team-13 | 60–1,025 | 3,470 | 56 | 21.0 | Varg(5), Cassi(5), Issac(5), Stellar(4), Tavi(3) |
| team-14 | 414–1,020 | 3,393 | 91 | 14.8 | Stellar(5), Tavi(5), Cassi(3), Issac(3), Ren(3) |
| team-15 | 60–1,080 | 4,175 | 105 | 20.0 | Stellar(5), Ren(5), Cassi(5), Issac(5), Ryth(5) |
| team-16 | 90–1,000 | 4,580 | 81 | 37.8 | Varg(5), Cassi(5), Issac(5), Stellar(5), Ryth(4) |
| team-17 | 66–1,020 | 4,590 | 73 | 33.2 | Varg(5), Stellar(5), Cassi(5), Issac(5), Ryth(3) |
| team-18 | 768–1,014 | 3,550 | 53 | 17.0 | Cassi(5), Issac(5), Varg(5), Ryth(4), Stellar(4) |
| team-19 | 258–1,018 | 4,305 | 74 | 40.8 | Stellar(5), Prism(4), Ren(4), Tavi(2), Willow(1) |
| team-2 | 690–1,020 | 3,560 | 81 | 25.0 | Cassi(5), Issac(5), Varg(4), Ryth(4), Tavi(4) |
| team-20 | 856–1,030 | 3,700 | 71 | 20.6 | Ren(5), Stellar(5), Cassi(5), Issac(5), Varg(3) |
| team-21 | 132–1,063 | 4,240 | 50 | 25.0 | Cassi(5), Issac(5), Stellar(5), Varg(5), Ryth(4) |
| team-22 | 936–1,000 | 3,680 | 107.5 | 18.0 | Cassi(5), Issac(5), Stellar(5), Ryth(4), Ren(4) |
| team-23 | 630–1,016 | 3,445 | 86 | 31.2 | Varg(5), Stellar(5), Ren(5), Vendetta(5), Marcella(4) |
| team-24 | 480–1,020 | 4,500 | 61 | 45.2 | Cassi(5), Issac(5), Stellar(5), Ryth(5), Tavi(3) |
| team-3 | 323–1,024 | 4,826 | 86 | 23.0 | Ren(5), Stellar(5), Cassi(5), Issac(5), Ryth(4) |
| team-4 | 864–1,024 | 3,690 | 125 | 38.6 | Varg(5), Stellar(5), Cassi(5), Issac(5), Ryth(2) |
| team-5 | 318–1,064 | 4,050 | 91.5 | 11.8 | Cassi(5), Issac(5), Stellar(5), Varg(5), Ren(5) |
| team-6 | 336–1,044 | 4,160 | 89 | 19.6 | Ryth(5), Ren(5), Cassi(5), Issac(5), Stellar(5) |
| team-7 | 300–1,020 | 3,885 | 87 | 34.4 | Stellar(5), Ren(5), Cassi(4), Issac(4), Tavi(4) |
| team-8 | 60–1,020 | 4,445 | 59 | 21.8 | Stellar(5), Cassi(4), Issac(4), Ryth(4), Ren(2) |
| team-9 | 386–1,020 | 3,396 | 58 | 19.2 | Varg(5), Stellar(5), Cassi(5), Issac(5), Ren(4) |

## Match-level evidence targets

### Strongest early score leads
- \`higher-elo/losses/team-9/04-734168de-1e88-4d32-ba49-06a4314db6af\`: round 200 score Bot1 60, opponent 720.
- \`higher-elo/losses/team-16/03-d5c0cc70-0efb-458d-b2bd-e404a4ab1065\`: round 200 score Bot1 44, opponent 618.
- \`higher-elo/losses/team-13/02-de69888e-3aaa-43c7-83fc-fe2481d7540b\`: round 200 score Bot1 0, opponent 448.
- \`higher-elo/losses/team-10/05-7c3c27dc-eab9-4bce-bf84-c5e486ff0ae3\`: round 200 score Bot1 0, opponent 432.
- \`higher-elo/losses/team-14/05-f3511e3b-d355-454f-a156-2a18330b732f\`: round 200 score Bot1 0, opponent 392.
- \`higher-elo/losses/team-6/02-14378c38-2103-4f32-9df0-eb9ac8cd4077\`: round 200 score Bot1 110, opponent 488.

### Largest opponent capture lead
- \`higher-elo/losses/team-16/05-09970453-de58-4357-9523-6ed97f04d5c8\`: captures Bot1 9, opponent 109; final [0, 1000].
- \`higher-elo/losses/team-24/01-b7512a73-4dbe-42f0-85d9-64576c5ae926\`: captures Bot1 17, opponent 117; final [200, 1000].
- \`higher-elo/losses/team-19/02-dcaaeae5-fe93-4b70-bfdd-de948b79fb5f\`: captures Bot1 19, opponent 113; final [0, 1000].
- \`higher-elo/losses/team-17/01-625fd4b5-359a-4a02-860e-4ebf1ce765c8\`: captures Bot1 5, opponent 73; final [0, 1000].
- \`higher-elo/losses/team-23/01-4d441141-2308-4beb-b683-d307215daf7e\`: captures Bot1 22, opponent 73; final [0, 1000].

### Stationary gem carriers (Bot1)
- \`higher-elo/losses/team-10/03-286e0f16-417f-4bfa-ad7f-596b5bce79f8\`: up to 1932 stationary carrying turns; final [0, 0].
- \`higher-elo/losses/team-5/02-e6e74775-eb58-4350-b882-f2ac069e870d\`: up to 1932 stationary carrying turns; final [0, 0].
- \`same-elo/losses/team-3/04-b7dec445-16d6-4983-b5d4-5f302c2f4d37\`: up to 1932 stationary carrying turns; final [0, 0].
- \`same-elo/wins/team-2/04-852e8b28-4aa2-4f57-af37-d660badb9417\`: up to 1932 stationary carrying turns; final [0, 0].
- \`same-elo/wins/team-8/05-3aedf8ad-6434-42bd-a320-6079138ffdf0\`: up to 1932 stationary carrying turns; final [0, 0].
- \`same-elo/wins/team-9/04-b32de207-5a55-45e9-8533-14db55eebf07\`: up to 1932 stationary carrying turns; final [0, 0].
- \`higher-elo/losses/team-16/04-057f50de-9a25-4fec-91bf-c79f6c48671a\`: up to 1922 stationary carrying turns; final [0, 0].
- \`same-elo/losses/team-13/02-3d14ce35-c682-4480-845c-47bc2596a0a6\`: up to 1922 stationary carrying turns; final [0, 0].
- \`higher-elo/losses/team-16/01-751b9afd-a2de-462e-a27a-607b8763abbb\`: up to 44 stationary carrying turns; final [868, 1006].
- \`same-elo/wins/team-4/05-c4c73d33-37cb-4b04-bf11-15342b429890\`: up to 35 stationary carrying turns; final [583, 1023].
- \`same-elo/losses/team-5/02-011e6c3e-2aa7-46f5-bde9-e60f6c898290\`: up to 26 stationary carrying turns; final [1030, 852].
- \`higher-elo/losses/team-13/01-07555cf5-fa43-43fe-8812-d659d00b9007\`: up to 25 stationary carrying turns; final [808, 1034].

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
