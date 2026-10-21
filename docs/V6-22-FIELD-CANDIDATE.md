# v6.22 field candidate — blocked-altar clearance + coordinated objective raids

## Summary
v6.22 inherits the **tested** v6.21 altar entrance fix: permit an attacking squad to remove a camp physically occupying the single legal approach to a guarded altar. It adds a team convergence/rally behavior on objective-only maps, where two or more healthy nearby champions commit together to a high-health gem boss. Base immutable C++ source `aba4cd4afe270d9da94ad5af5736b767739d8447`; CAMBC 3.0.1, six source files in `src/`.

## Controlled tournament evidence (17 permitted maps, both sides)
- v6.22 vs frozen v4: **21/34 wins, +120.47 mean gem margin, zero caught exceptions and engine faults, 52 fuel-spill events**.
- Exact v6.21 vs frozen v4: **21/34 wins, +108.71, zero exceptions/faults, 52 spills**.
- v6.22 vs exact v6.21: **17/34 wins, +5.88 mean gem margin**, 54 candidate fuel-spill events.
- Training-map `01boss-battle`: v6.22 tributed **840** and **595** from A and B, unchanged vs v6.21, recovering from v6.8's 0/0.
- Training-map `00contest`: v6.22 A 0–0 (v6.21 A 0–200), v6.22 B 200–0 (v6.21 B 0–0).
- Improved gem margin did **not** change win count versus frozen v4. This is a bounded in-distribution result, **not evidence of dominance against high-Elo platform teams**. The control has 34 deterministic games per pairing, not multiple diverse seeds/opponents.

## Status and controls
Experimental field-test candidate, not promoted as universally stronger. Preserve v6.8 and v6.21 as independent control builds. Pair v6.22/v6.21 against the same live opponent, map and side when feasible; log game version, result, gem scores, rounds, carrier deaths, economy curve, altar lock usage, and replay URL/hash. Do not tune on `00lanes`, `01corridors`, `01hooks`, `01islands`; any uploaded replay from an unrecognized map remains quarantined. Original v4/v5 frozen code unchanged.

Historical reports with aggregated data from all 179 old unique games include held-out `01islands` and thus must not be used unfiltered as model-selection evidence. Use the strict 161-replay training set or named approved maps only.
