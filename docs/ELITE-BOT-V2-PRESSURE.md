# EliteBot v2: tactical pressure isolated from elite composition

Purpose: distinguish *behavioral* elite-replay hypothesis from the failed Cassi/Tavi/Varg draft transplant. Baseline is exact pinned v6.8 source `0ddd5338b94db824f9f53261a17f020490b7017f`. Nonobjective draft and five other source files are identical to it. C++ executor gains an isolated feature `ELITE_EARLY_PRESSURE=1`: one high-health, gem-free champion may move toward a visible vulnerable enemy in range 5-7 only if backed by nearby allies and not outnumbered. No hidden information, no private source copying.

Evidence source: elite opponents attempted +49.5% champion attacks vs v4, +71% during first 200 rounds on 161 unique permitted-map replay contents. **Attempted attacks do not prove successful combat or win causality**.

Test: 102 paired games v2 vs frozen v4, exact pinned v6.8 vs v4, and v2 vs pinned v6.8 across 17 approved maps both sides, CAMBC 3.0.1. Never use `00lanes`, `01corridors`, `01hooks`, `01islands` until final testing. Record faults, fuel, gems, wins. Not promoted without repeatable gain.
