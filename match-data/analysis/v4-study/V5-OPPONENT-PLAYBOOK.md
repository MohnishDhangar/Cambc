# V5 opponent playbook — evidence from 245 archived v4 matches

*Prepared 20 October 2026. Scope: engine 0.0.3, pre–Week 2 balance. Keep conclusions separate from post-patch tests.*

## Source of evidence and reliability

The repository contains a **complete extracted v4 replay analysis**, including:
- [Quantitative report](REPORT.md), [metrics.json](metrics.json) and [turn-level opponent case studies](TACTICS.md).
- 245/245 unique replay files decoded and analyzed; zero decode failures.
- 120 high-Elo-labelled losses, 75 same-Elo-labelled losses, 50 same-Elo-labelled wins.
- **44 folder outcome mismatches**. This is material: category labels are not trustworthy match outcomes. Recompute categories using actual replay outcome before comparing win/loss policies. The analysis assumes team A = Bot1 v4 based on checked stdout samples; verify for every replay.
- Many "stationary carrying" episodes of ~1,932 turns accompany final 0–0 scores. **Do not use them as proven deadlocks** without reviewing state semantics and trace generation.

All claims below are *recorded observations*, not proof of opponent intent or proof they generalize across map or post-patch balance.

## High-value strategies revealed by opponents

### 1. Open with rapid compounding investments rather than waiting to accumulate gold
- Early purchase traces show winning opponents purchasing multiple jungle/monster strength, focus and durability items by round 150.
- Example [team-13 game 2](../../v4/higher-elo/losses/team-13/02-de69888e-3aaa-43c7-83fc-fe2481d7540b/): opponents recorded 7 Jungle Strength shards, 2 Bruiser Health shards and additional emblems before round 150; Bot1 recorded only 3 Monster Strength shards.
- What to copy: evaluate purchases by **round to first shard, subsequent damage/clear thresholds, and upgrade-induced downtime**. Never copy one fixed purchase list across all champions/maps.
- **Confidence: high** that faster investment occurred in some decisive games; **medium/low** that this exact purchasing policy is causally optimal.

### 2. Use coordinated burst / concentrated PvP only when conversion is profitable
- On [team-16 game 5](../../v4/higher-elo/losses/team-16/05-09970453-de58-4357-9523-6ed97f04d5c8/), opponent recorded 49 champion kills versus Bot1's 1; team-oriented same-round focus opportunities 18 versus 5. Final 0–1000.
- On [team-19 game 2](../../v4/higher-elo/losses/team-19/02-dcaaeae5-fe93-4b70-bfdd-de948b79fb5f/), opponent recorded 51 champion kills versus Bot1's 1 and 27 same-round focus opportunities versus 2.
- [team-24 game 1](../../v4/higher-elo/losses/team-24/01-b7512a73-4dbe-42f0-85d9-64576c5ae926/) shows 56 opponent champion kills versus Bot1's 7.
- Potential mechanism: group focus denies enemy farming and captures. With Week 2 champion kill reward now 100 gold, the economics may improve, but survivability and lost farm time still dominate. Add a tactical **local 2-v-1 or 3-v-1 opportunity classifier**, not unconditional hunting.
- **Confidence: high** that concentrated aggression appears in these matches; **medium** about positive expected value.

### 3. Prioritize durable hybrid purchases when expecting PvP
- Example [team-9 game 4](../../v4/higher-elo/losses/team-9/04-734168de-1e88-4d32-ba49-06a4314db6af/): opponent purchased early Durability Health and Jungle Health plus Monster Strength; Bot1 invested only in Monster/Jungle Strength. By round 200 opponent led 720–60 and completed match 1020–60.
- Example [team-22 game 4](../../v4/higher-elo/losses/team-22/04-4fa29193-73cc-4083-8e9f-38c6d14963f3/): opponent invested health/focus and had nine champion kills vs zero, yet Bot1 ultimately won 1008–456. **This is a negative control:** more PvP does not automatically win the objective race.
- Proposed strategy: adaptive survival budget dependent on map congestion, enemy proximity, repeated death count and gem bag exposure.
- **Confidence: medium**.

### 4. Contest objective throughput, not just duel wins
- Highest capture discrepancy: [team-16 game 5](../../v4/higher-elo/losses/team-16/05-09970453-de58-4357-9523-6ed97f04d5c8/), recorded Bot1 9 vs opponent 109 capture events; [team-24 game 1](../../v4/higher-elo/losses/team-24/01-b7512a73-4dbe-42f0-85d9-64576c5ae926/) 17 vs 117.
- Warning: verify event definition of "captures" and distinguish capture *progress* ticks from unique rewards before claiming those are 109 distinct camp captures.
- Proposed v5 metric: time from monster-group death to *uncontested capture reward*, ally-ally capture splits, score conversion efficiency, duplicate route assignments.
- **Confidence: high** on large event-count asymmetry; **low** on counts as unique captures until audited.

### 5. Earlier scoring is decisive on compact or contested maps
- Against [team-9 game 4](../../v4/higher-elo/losses/team-9/04-734168de-1e88-4d32-ba49-06a4314db6af/), at round 200 opponent had 720 vs Bot1 60, ending at round 255.
- Against [team-16 game 3](../../v4/higher-elo/losses/team-16/03-d5c0cc70-0efb-458d-b2bd-e404a4ab1065/), round 200 score 618 vs 44.
- Against [team-13 game 2](../../v4/higher-elo/losses/team-13/02-de69888e-3aaa-43c7-83fc-fe2481d7540b/), round 200 448 vs 0.
- Target the first 200 turns: map-aware opening draft, first camp choice, investments, first capture, and first safe tribute. An ideal initial policy should be selected by paired simulation, not imitation alone.
- **Confidence: high** that opening score gap exists; **medium** regarding its cause.

### 6. Exploit map-conditioned roles, not a universal draft
- Across 120 high-Elo labelled losses, opponent appearances: Stellar 114; Cassi + Issac 107 each; Varg 86; Ren 83; Ryth 75. Bot1 heavily selected Tavi 120, Varg 120, Vendetta 114.
- This is **selected-sample composition frequency**, not causal selection or a reliable meta win-rate estimator. Week 2 nerfs Cassi/Issac, Stellar, Varg and Ryth; do not transplant frequency tables into current patch unchanged.
- Test archetypes: (a) high-opening burst and mobility, (b) mixed economic-farm, (c) durability/focus PvP, (d) large-objective siege; select by map topology and opponent.
- **Confidence: high** on observed frequency; **low** on draft superiority after patch.

## Major vulnerabilities of Bot1 v4 exposed by the data

1. **Win/loss metadata unreliable:** 44 replay-folder outcome mismatches, including games marked as losses where Bot1 won and vice versa. Any optimizer using folder labels will be biased.
2. **Early tempo collapses:** the largest deficits emerge well before round 200; investigate wrong first objective, delayed shards, and unproductive deaths.
3. **Elite PvP pressure:** in several high-loss matches enemies inflict far more champion damage, exploit multi-attacker focus and accumulate dozens of kills while Bot1 repeatedly respawns.
4. **Capture throughput gaps:** opponent objective-event volume dwarfs Bot1 in some large-objective matches; require event semantics verification.
5. **Objective decisions lack coordination with fight risk:** current `defend()` chooses nearby enemy from HP/bag/distance, without local numerical superiority, enemy cooldowns, protected ally carriers or response time. Prioritize local strength and safe gem conversion.
6. **Special map archetypes need separate models:** some late-score stalemates and 0–0 games must not be interpreted as ordinary camp farming failures without map-level breakdown.

## Controlled next experiments

| ID | Proposed change | Primary metric | Guardrail |
|---|---|---|---|
| E01 | Faster first investment and clear threshold optimization | round-100/200 scored gems, first shard, first reward | deaths, total score |
| E02 | Local strength / focused target tactical selector | net champion damage, net gold from kills | carrier death and gem loss |
| E03 | Adaptive durability vs pure damage purchasing | deaths before 250, damage efficiency | farming tempo |
| E04 | Camp capture recipient and immediate bank optimization | reward-to-tribute latency, stalled progress | duplicate captures |
| E05 | Map-archetype draft portfolios | paired map-specific win rate | never overfit elite-loss-only drafts |
| E06 | Week 2 gem cluster 120 HP and changed gem values | gems/round, travel cost | threat survivability |
| E07 | Contested-altar policy (lock and enemy carrier timing) | secured gems per visit | idle turns and deaths |

**Protocol:** keep frozen v4 and a frozen v5 base; run same maps and seeds from both team sides, record source SHA, engine version, illegal actions, fuel, wins and all major metrics. Analyze patches separately from archived v4. Prefer 50–100 paired games to screen changes, then more games before accepting marginal gains.

## Data work that remains before treating this as definitive

- Verify team identity and actual recorded winner for all 245 files; correct 44 label mismatches.
- Audit sampled extreme 0–0 and 1,932-turn episodes for trace semantics.
- Define event taxonomy for actual camp reward captures versus interim captures/progress.
- Run additional *case-level* reviews on wins and counterexamples, not just opponent-dominant losses.
- Fit map-stratified analyses so counts from big maps and long games are not equated with compact maps.
- Test on the post-20-October rules whenever a matching engine becomes available.

All links and numbers are from [REPORT.md](REPORT.md) and [TACTICS.md](TACTICS.md). This is a strategy backlog, not a statement that the tactics have been implemented or shown to improve v5.
