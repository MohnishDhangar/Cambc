# EliteBot v6 — teammate-aware navigation, path planning through allies

## Evidence and mechanism
Elite opponents attempted +19.7% moves and had lower no-command turn rates than frozen v4 in 161 permitted replays, but not necessarily greater net progress. In pinned v6.8 objective trace on allowed `01boss-battle`, several carriers repeatedly logged `navigate` at unchanged positions for many sampled rounds, with no tribute. The previous v5 static altar reachability guard produced no solution. `Bot::navigate()` previously treats occupied **allied** tiles as permanently blocked while solving its distance field, even though teammates can move between turns.

## Isolated behavioral change
Plan the gradient using terrain+visible enemy/camp/teleport occupancy but **do not block visible friendly champion positions** during BFS. Enforce all original movement legality using the original `blocked`, `occupied()`, `terrain`, legal reachable masks and `move_absolute()`. Thus legal moves never land on occupied units, yet a narrow friendly-blocked passage may still have a gradient. The early-exit BFS guard and all other v6.8 policies remain unchanged; feature flag `ELITE_ALLY_THROUGH_PLANNING`.

## Required tests
Pinned v6.8 `0ddd5338b94db824f9f53261a17f020490b7017f`, frozen v4 zip hash checked, CAMBC 3.0.1, 17 development maps x 2 sides x 3 pairings (102). Check objective-map zero-tribute matches, all sides, score, fuel, exceptions, faults. May improve congestion but also risk chasing blocked routes; reject if not better. Four maps `00lanes`, `01corridors`, `01hooks`, `01islands` sealed.
