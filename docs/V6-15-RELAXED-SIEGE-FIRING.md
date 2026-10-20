# v6.15 — objective siege safe-firing fallback

## Baseline and hypothesis
Preserve pinned v6.14 experiment commit `4aaefa0b79c5fa661c7ef64f2d93cf29c6c1b353`, which advances objective sieges earlier. When all firing tiles in range 4 are covered by the union of Chebyshev radius-3 monster danger zones, `firing.is_empty()` causes `siege_objective()` to bail. On objective-only maps this can prevent any major-camp attack. v6.15 allows a fallback firing location in radius 4 if none were safe, only for healthy (HP>80%) and empty-handed casters. `V6_RELAXED_SIEGE_FIRING` preserves legacy routine under flag. This does not change ordinary maps or any frozen reference.

## Risks and test
Attacking in range of high-damage monsters can cause premature deaths; this must be measured. Three 34-game pairings: candidate vs v4, pinned v6.14 vs v4, candidate vs v6.14, across 17 unsealed development maps both sides, CAMBC 3.0.1; 102 games. Candidate needs better wins, margin and zero computational faults and fuel spills before any promotion. Four held-out maps excluded by explicit map manifest checks.
