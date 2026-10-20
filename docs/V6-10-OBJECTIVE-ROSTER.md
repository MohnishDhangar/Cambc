# v6.10: objective-only roster activity ablation

## Hypothesis
When `objective_map` is true, `select_camp()` skips major camps while `siege_objective()` rejects all non-caster champions. This leaves non-casters without productive objectives on sparse maps and may explain games with severely limited tributed gems. Enable non-caster objective assistance only on objective-only maps, preserving all caster behavior.

## Isolation and held-out exclusion
Base exact v6.8 commit `0ddd5338b94db824f9f53261a17f020490b7017f`. Feature flag `V6_OBJECTIVE_ROSTER_FIX` keeps the old behavior available. No modifications to frozen v4/v5. Only the 17 approved development maps may be run; `00lanes`, `01corridors`, `01hooks`, `01islands` stay sealed. User uploaded field replays were audited separately; no held-out map replays are used to select this fix.

## Required evidence
Paired 102 games: v6.10 vs frozen v4, pinned v6.8 vs frozen v4, v6.10 vs pinned v6.8; both sides on all 17 approved development maps. Inspect 0-gem and objective-only results separately, not just aggregate wins. Reject on regression or continuing fuel faults. **Experimental pending CI.**
