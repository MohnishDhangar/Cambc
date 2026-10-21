# V6.21 — camp-blocked altar entrance clearing (isolated experiment)

## Reproduced permitted-map root cause
Pinned v6.8 on approved development map `01boss-battle` repeatedly produced `NAVEMPTY` for gem-carrying champions. Cause probe `research/v6-altar-goal-blockers` on both sides: **9 raw altar goals, 8 in permanently blocked terrain, 1 occupied by a visible living camp, no champion or teleport occupant**, in 73 sampled empty-goal incidents. The original `navigate()` removes all occupied destination goals and returns false without BFS. The caller `bank()` then returns true, preempting productive activity. Untargeted bank watchdog (v6.18) and approximate route clearing (v6.19) did not alter zero-tribute outcomes.

## Patch
Pinned reference `0ddd5338b94db824f9f53261a17f020490b7017f`, source only `bots/Bot6/src/bot.cpp` altered, feature-flagged `V6_ALTAR_ENTRANCE_CLEAR`. When a carrier's altar approach has no free tile, seek a camp whose static spawn position occupies that approach. Fight it if visible and in range; otherwise navigate toward a terrain-legal ranged attack position, preserving actual occupation/SDK move legality. If unable to act, return false and permit farming/defense instead of infinite blocked banking. All ordinary-map behavior, draft, equipment, and other functions remain pinned.

## Gates
CAMBC 3.0.1; 102 games against frozen v4 and exact v6.8 on 17 development maps mirrored both sides, plus separate focus metrics for `01boss-battle`. Report absolute tributed gems, win count, mean score margin, runtime faults, fuel and caught errors. Never train/tune on `00lanes`, `01corridors`, `01hooks`, `01islands`. Not promoted unless a repeatable advantage is shown.
