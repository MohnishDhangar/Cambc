# EliteBot v1: guarded early skirmish pressure

## Inspiration and attribution
On the strict 161-unique-replay elite training split, opponents attempted 49.5% more champion-targeted attacks per game, and 71% more such commands during the first 200 rounds than frozen v4. A real strong opponent's code is **not available**. This feature is an original hypothesis inspired by behavioral aggregates, not a reproduction of private code or proven source of strength.

## Algorithm
Preserve independent EliteBot v0 Cassi/Tavi/Varg composition at pinned commit `54ed0b2a1758b9eb696b5619c15274c8fb2cc074`. Only change match-time pressure behavior. A single champion (`slot==0`) may intercept a visible enemy at range 5–7 before round 650, only without gems, above 80% health, if at least two allies support the vicinity and nearby allies outnumber observed enemies; pursue high-carry enemies or enemies low enough to threaten. Ordinary farming and banking untouched, and no squad-wide suicidal chase.

## Test gate
Build with CAMBC 3.0.1. 102 games on 17 allowed maps mirrored A/B, pairings v1 vs v4, **exact v0** vs v4, v1 vs exact v0. Count wins, score, crashes, fuel, zero-tribute cases. Reject if worse; then measure against pinned v6.8 before any promotion. Never tune on held-out `00lanes`, `01corridors`, `01hooks`, `01islands` or quarantined linked replays.

## Status
Experimental code, no results claimed until CI succeeds. Baselines remain unchanged.
