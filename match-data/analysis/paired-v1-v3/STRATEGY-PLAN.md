# Proposed next strategy: cooperative clearing, one capturer

Status: original evidence-based design. V4 has now been implemented and evaluated, with changes selected through local comparisons; see the [released strategy](../../../bots/Bot1/STRATEGY.md) and [102-game evaluation](../../../replays/v4-release-evaluation/REPORT.md). The implementation retained v1’s ordinary farming core and replaced failed melee rallies with ranged objective sieges. See the [paired analysis](REPORT.md) and [replay explorer](explorer.html) for the original opponent evidence.

## Objective

Maximize the team's rate of **submitted gems**. Gold, damage, kills, and safety are useful when they improve that rate. A map with one difficult gem group needs a different resource plan from a map with many ordinary wolves or free gem clusters.

The main change is to assign a camp to a small group with distinct jobs, rather than asking every champion to choose and complete its own entire farming cycle.

## Camp lifecycle

1. **Select:** score a job by travel, actual participating damage, capture time, delivery distance, current equipment needs, and enemy pressure. Choose participants who can arrive soon; a distant ally's claim is not usable support.
2. **Clear:** a suitable melee champion tanks; nearby helpers attack and cast from useful range. Use the group's combined power to decide whether the job is viable. Preserve the assignment until it finishes or a measurable failure condition occurs.
3. **Capture:** elect one healthy recipient. Other participants leave the reward tiles and begin the next job. If the recipient dies, retreats, or stops making progress, elect a replacement. A nearby occupant should be favored to avoid resetting capture progress.
4. **Deliver and reinvest:** the recipient banks and buys at a meaningful equipment threshold. Helpers continue producing resources. Tavi can reinvest in the field. Rotate recipients so the strongest potential farmer is funded without leaving every helper permanently unequipped.
5. **Repeat:** choose an available nearby group or a respawn whose timing justifies travel. Avoid sending several champions across the map to chase the same nearly completed job.

A single recipient does not create extra gold or gems. Its advantages to test are fewer redundant capture/altar trips, earlier equipment thresholds, and useful work by departing helpers. Keep recipient choice separate from who dealt the last hit.

## Shared state and fuel budget

Use the existing draft memory for static map analysis: camp layout, likely farming regions, role preferences, and compact opening assignments. Respect its 1,024-byte limit. Gameplay shared memory is only eight bytes, so do not assume it can hold a full global planner.

Reuse each champion's assignment byte for its camp claim. Determine the recipient by a deterministic rule from compatible claims and visible occupants, with short local commitment timers and a stable tie-break. Reserve the remaining bytes for one leased major objective, as the current implementation does. Cassi & Issac can create six bodies in a five-pick draft; include all six assignment slots. Release stale claims on death, recall, delivery, timeout, or completed capture. If a map has too many groups for a byte encoding, fall back explicitly rather than wrapping identifiers.

Avoid repeated full-map searches per decision. Spread initialization across turns or perform static work during draft; compute detailed altar fields only when needed. Cache static distances, bound live replanning, and check fuel before each expensive SDK operation. A fixed remaining-fuel threshold does not guarantee a search will finish; measure worst cases on the 18-altar map. Low-budget fallbacks must still make navigation progress.

## Draft and equipment candidates

| Map/job | Candidate roles | Evidence and qualification |
| --- | --- | --- |
| Ordinary mixed camps | Cassi & Issac, Ren, Stellar; add a farmer appropriate to remaining picks | The opponent repeatedly uses this composition; Cassi & Issac add a body but linked deaths require joint safety. |
| Dense wolf packs / rows | Varg and Vendetta for basic damage, Cassi & Issac for extra clearing support; Ryth if picks allow | Four opponent contributors open the first rows gem camp by round 34. Preserve v1's successful farming behavior as a control. |
| Spell/control-friendly contest | Focus caster support with an equipped melee farmer | The opponent builds Power Focus on Cassi, Stellar, Ren, and Tavi. Test each role rather than copying all purchases blindly. |
| Monolith-only | Gold farming first; compare damage/control composition with a healer variant | The opponent wins without Willow, but that alone does not prove healing is inferior in a competent implementation. |
| One large non-monolith gem group | Productive gold farmers plus a scheduled cooperative objective attempt | The 60×50 objective is six elks and six gem clusters; current monolith-only rally logic misses this map class. |
| Spacious ordinary farming | Keep a v1-derived independent farming option | Both versions beat this opponent on 80×80. Avoid sacrificing a demonstrated strength. |

Strength is the default for splash/basic-attack farmers. Focus is a candidate for a spell-support role. Tavi's Focus build should be compared with Strength when farming solo: the burst/stun benefit does not automatically imply higher sustained damage. Buy mitigation and health according to tanking and enemy exposure; preserve early Jungle as a test variant for heavy camp damage. Test Power-first against Monster-first, rather than declaring either universally optimal.

## Generalized scoring objectives

At draft, identify **all gem-bearing groups** and whether ordinary solo routes can score. A difficult non-monolith group must be eligible for cooperative planning. Support two levels of coordination:

- Small, nearby clearing groups for routine resource production.
- A bounded rally for objectives that require more of the team.

Readiness depends on nearby live participants, their damage, shields/control, tank health, and escape routes. Helpers do not count until they can contribute. While a rally is unavailable, assign productive gold work; avoid waiting at a staging point for allies that cannot become ready. Treat a long period of earning gold without any attempted scoring objective as a reason to reconsider assignments, not an instruction to attack recklessly.

## Delivery and combat

Keep reliable single-bag delivery as the initial control. The 31×31 evidence does not justify making large bags a universal rule: the opponent's bag duration is almost identical to ours. Later, test an extra nearby capture only when it saves a delivery trip, does not delay a possible win, and adds little exposure.

Fight to protect productive jobs, finish vulnerable carriers, or secure a scoring objective. Do not let all farming turn into pursuit, or all visible enemies trigger indefinite retreat. Keep v3's proven reduction in casualties while measuring whether retreated champions actually resume productive work. Tie capture commitment, retreat, and banking to separate progress timers.

## Implementation order and acceptance measurements

1. **Runtime repair only.** Compare with frozen v3 on 90×30 and 80×80. Require zero fuel exhaustion, caught errors, and bot faults at the platform's default budget. Check that eliminating fuel overruns does not introduce stationary carriers.
2. **One recipient and departing helpers, existing draft.** Use rows and 31×31, then 30×80 and 40×40. Measure first gem capture, groups completed by rounds 100/200/400, split captures, participant utilization, gold converted into equipment, and submitted gems. A zero-gem helper is acceptable if it materially accelerates teammate captures; assess its contribution, not its bag alone.
3. **Role-based equipment, then draft.** Change one component at a time. Compare Power/Monster starts and Focus/Strength by role. Include both sides and preserve the current 80×80 result.
4. **Generalized objective.** Test the 60×50 gem group and monolith-only map. Require completed gem captures and delivery, not merely more total gold or fewer deaths. Inspect failed attempts and the opportunity cost of rallying.
5. **Broader comparison.** Run the resulting candidate against frozen v1/v3 and a local opponent on all 17 embedded maps, both sides. Use a manageable targeted set during iteration, expanding when the targeted checks pass. Local baselines do not reproduce lll's strategy; they detect regressions.
6. **Platform validation.** Replay a small set of the diagnostic maps against lll, then a second strong opponent. Save versions, maps, sides, and full replays. Compare component-level improvements before interpreting a small win count as general strength.

The opponent's replay is a record of fixed actions, not a reusable adaptive opponent. Do not claim that replaying it against changed bot actions constitutes a fair head-to-head test. A locally reconstructed opponent would be an approximation and must be labeled as such.

Before packaging the next version, publish the measured results and known regressions with the archive. Compilation alone was insufficient for v2 and v3.
