# v6.23 navigation fuel preflight (controlled experiment)

Base: `13e96cb1c1e0e95c9ad14c49307b0d817852c9e3` (v6.22). Engine: CAMBC 3.0.1.

Hypothesis: deferring the navigation BFS when fewer than 45,000 fuel units remain will reduce turn suspension on large maps. Only the `navigate` preflight guard changes from 18,000 to 45,000. The candidate is generated from the pinned base by the benchmark script, not silently promoted.

Compare candidate, pinned v6.22, and archived frozen v4 in 102 paired games across the 17 training maps, both starting sides. Preserve hashes, scores, wins, errors, fuel spills, and match-level CSV. Do not load `00lanes`, `01corridors`, `01hooks`, or `01islands`.

This is an unvalidated experiment, not a performance claim.
