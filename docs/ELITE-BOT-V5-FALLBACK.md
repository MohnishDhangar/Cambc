# EliteBot v5: do not stall in impossible banking loop

**Empirical motivating trace:** training map `01boss-battle`, pinned v6.8 objective-action samples report repeated `navigate` with positive carried gem bags at unchanged positions over long periods on *both* sides. The original bot's `V6_BANK_THRESHOLD=0` means any gem carrier enters `bank()` before defending/farming/sieging, and `bank()` returns true even if `map::altars()` has no bankable route. Elite opponents had lower no-command rates in the 161 permitted replay audit; this is a proposed *productivity* correction, not a claim about their private implementation.

**One isolated difference:** if terrain-only `altar_distance.get(position)` is `unreachable` or the map has no altars, do not allow banking to consume the turn. Continue existing `defend()/siege_objective()/farm()`. If there is a real reachable altar, original banking behavior is byte-for-byte unchanged. This also enables farming gold for the second tiebreak when banking cannot work. The rulebook uses submitted gems, then lifetime gold, then kills; it is still correct to farm gold even if altar routes fail.

Pinned source `0ddd5338b94db824f9f53261a17f020490b7017f` in five files plus a flag-guarded one-condition change in `bot.cpp`. Test vs frozen v4 and pinned v6.8: three mirrored 34-game pairings (102 total). Compare `01boss-battle` and `00contest` absolute gem/gold trajectory separately. SDK CAMBC 3.0.1, four sealed maps strictly excluded.

**Experimental only until verified.**
