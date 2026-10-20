# V6 empirical optimization log — 21 October 2026

## Status
**Dominant edge over frozen v4 is NOT established.** This is a completed/ongoing
classical strategy-search program, not a tournament-ready promotion. V4 and V5
are archived under `frozen/*`, unchanged.

**Engine and controls:** CAMBC 3.0.1 CLI and current SDK; reference
`bots/Bot1/Bot1-v4.zip` verified by SHA-256. Tests use both team sides and only
17 training maps in `v6-map-split.json`. Four held-out maps
`00lanes`, `01corridors`, `01hooks`, `01islands` remain sealed.

## Baseline restoration
V6.0 implemented a separate modular macro controller but went 0/6 against
frozen v4. Rebuilding v6.1 around frozen v4's tactical executor (while preserving
macro score overrides) gave 6/6 against starter, 2/6 vs frozen v4, 1/2 vs v5
on a small three-map smoke suite. The historical initial log filter missed
inherited `bot error` and `fuel spill` prefixes; later CI found at least
one `fuel spill at navigate walk` diagnostic. Thus early claims of "zero
exceptions" require corrected checking. Engine-reported `botFaults` were 0.

## Strategy ablations (all local)

| Experiment | Candidate(s) | Maps | Results |
|---|---|---|---|
| Macro weighting | 6 fixed/adaptive modes | 17 train, both sides; 204 games | Best **economy** 11/34 vs frozen v4 (32.4%), average margin -136.6; adaptive 8/34 |
| Banking thresholds | 0,4,8,12,16,24,32 gems, fixed economy | 17 train, both sides; 238 games | Thresholds 0,4,8 tied at 11/34; 8 gems improved mean score margin (-97 vs -136) but did not improve wins |
| Draft first screen | 7 composition archetypes | First 8 train maps, both sides; 112 games | Stellar/Prism/Tavi **10/16**, +234.5 mean gem margin; old roster 5/16 |
| Draft internal validation | 4 candidates from screen | Remaining 9 train maps, both sides; 72 games | Stellar/Prism/Tavi **8/18**, Heart of Ruin/Vesper Vale/Tavi **11/18** |
| Draft pooled | Same 17 train maps, but separate selection and internal validation subsets | 34 games per finalist | Stellar/Prism/Tavi **18/34 (52.9%)**, Heart/Vesper/Tavi **17/34 (50%)**, original v4-style draft **8/34 (23.5%)** |

The early Stellar/Prism/Tavi screening signal did **not** replicate
at the same magnitude on later development maps. This illustrates why tiny
smoke tests cannot justify promotion. The other branch
`develop/v6.3-integrated-roster` separately ran 34 paired matches with
Heart/Vesper/Tavi and reported 17/34 against frozen v4 (not dominant).

### Read-only reproducible reports
- `match-data/analysis/v6-macro-search/{games.csv,summary.json}`
- `match-data/analysis/v6-bank-search/{games.csv,summary.json}`
- `match-data/analysis/v6-draft-search/{games.csv,summary.json}`
- `match-data/analysis/v6-draft-validation/{games.csv,summary.json}`
- `tools/{search_bot6_macro,search_bot6_banking,search_bot6_draft,validate_bot6_drafts}.py`
- GitHub Actions run IDs: macros 39491894673; banking 39493817161;
  draft search 39493129650; draft validation 39494025403.

## Next: combinatorial roster search
`tools/search_bot6_rosters.py` screens 22 compositional policies on 6
development maps (both sides), then validates top five plus forced baselines on
11 remaining development maps. It pins economy macro mode 1 and immediate
banking threshold 0. It checks `botFaults`, caught exception messages, and
logs but does not automatically promote on win rate.

## Predeclared promotion gate
1. Winning at least **26 of 34** paired development-map matches (≥76.5%),
   positive mean gem margin of at least 100, and at least 11/17 wins from
   each starting side.
2. Zero recorded engine bot faults and caught bot exceptions; investigate
   fuel-spill warnings rather than silently omitting them.
3. Improved consistency across multiple opponent archetypes, not just v4.
4. **Only then** unlock one final held-out evaluation on the four reserved
   maps. The user should not be told any candidate is proven superior
   until these checks support the claim.

The main lessons are that static macro multipliers and larger gem carry
thresholds alone are not enough, while draft composition can materially change
results. Search over joint structure (composition, team allocation, economy),
not solely local numeric weights.
