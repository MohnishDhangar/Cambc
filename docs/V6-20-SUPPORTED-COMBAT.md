# v6.20 supported-combat ablation

## Source-grounded motivation
The user-provided `V6-STRATEGY.md` notes observed elite teams' damaging actions supported by allies in 82–92% of traced cases, versus 25–44% for v4, with a documented multi-champion focus-fire sequence. These are observational frequencies, not causal evidence. The earlier aggressive pursuit v6.2 elite prototype lost 18/34 versus v4; encouraging *more chases* without sound safety conditions is not acceptable.

## Isolated change
Pinned v6.8 `0ddd5338b94db824f9f53261a17f020490b7017f`. Change only `defend()`'s enemy target valuation. Count nearby **visible living** allied vs opposing bodies (no access to invisible ally positions); skip a non-gem-bearing strong enemy when locally outnumbered, or when at <60% HP without a numbers advantage. Prefer low-health targets with reachable allied support. No new approach/chase behavior and all farming, banking, draft, movement and shopping code unchanged.

## Test
CAMBC 3.0.1, frozen v4 archive SHA verified. Three mirrored 34-match pairings (102 total) across only 17 permitted training maps. Report win rate, gem margin, fuel and caught exceptions and direct vs pinned v6.8. No held-out maps `00lanes`, `01corridors`, `01hooks`, `01islands`. Version is an experimental hypothesis unless reproducible advantage shown.
