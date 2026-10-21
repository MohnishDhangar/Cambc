# v6.22 collective boss raid — objective-only maps (experimental)

## Verified motivating diagnosis
Allowed map `00contest`: `objective_map=true` with two gem-bearing groups of 20,000 HP, 200 damage and 200 gems each. Pinned v6.8 records no tributed gems on either starting side, even after enough rounds for attempted siege; only some casters were activated individually, with no coordinated readiness. Source trace `research/v6-contest-siege-diagnostics`, SDK CAMBC 3.0.1.

## Isolated strategy hypothesis
Keep pinned v6.21 altar entrance clearance, ordinary farming and draft byte-identical at base `91ac83fb14a76c52d8eed6e0dfaf71a7ce97c911`. When objective_map is true and round>=350, recruit other healthy champions in addition to casters. Each hero converges at a ring 6–7 around a deterministic boss; wait until at least two healthy allies are within 8 tiles before engaging; otherwise stage safely outside the recorded range-5 boss. Melee frontliners use attack-range legal firing positions only when rally condition met; casters keep original firing-lane algorithm. Decline recruitment when carrying gems or with <65% HP.

**Risks:** staging can waste time when allies cannot reach; two bodies might still die against high DPS; positions chosen from static spawn centres, not a full collision-aware auction. This is a distinct structural ablation, not a completed general objective planner.

## Controlled test
CI must compile with CAMBC 3.0.1, run 102 games on 17 permitted maps both sides: v6.22-v4, exact pinned v6.21-v4, v6.22-pinned v6.21. Report objective-map gem delivery (especially `00contest`), ordinary-map win regressions, death and fuel, 0 engine faults/exceptions. Four sealed maps untouched. Promotion only on reproducible wins, not just better boss damage.
