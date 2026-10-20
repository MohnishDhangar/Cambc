# v6.14 — Earlier objective-map siege hypothesis

Source issue: if an objective map has only major gem camps, the v6.8 siege routine refuses to act before round 400 when a caster's focus is below 180. The farming routine's safe-target filters can leave champions inactive. In v6.14 ONLY for objective maps we permit siege after round 120 or when focus >=125, still requiring health >=45% and a caster. Legacy timing preserved behind `V6_EARLY_SIEGE` flag; pinned reference v6.8 SHA `0ddd5338b94db824f9f53261a17f020490b7017f`. This is a testable attempt to restore gem throughput on boss-heavy maps; early deaths are a major risk.

Benchmark 102 games across 17 training maps both starting sides, comparing v6.14 vs frozen v4, pinned v6.8 vs frozen v4 and v6.14 vs pinned v6.8. No reserved maps `00lanes`, `01corridors`, `01hooks`, `01islands` are used in optimization. Do not promote until proven.
