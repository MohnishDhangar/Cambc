# V5 Week 2 development log — 20 October 2026

> **Submission format correction:** The CAMBC website accepts a source ZIP containing exactly six files under `src/`, not a WASM module. The uploadable file is [`submissions/Bot1-v5-week2.zip`](../submissions/Bot1-v5-week2.zip) (SHA-256 `b57209629cbdbcdec3123e6db87bb43d5c7c037d951259da36e52c0597727c37`). This ZIP is generated from the last regression-tested source commit. See [V5-FIELD-TEST.md](V5-FIELD-TEST.md). The WASM artifact below is for internal compilation/testing only.

## Field candidate built and ready (20 October, 12:00 UTC)

**Stable source commit:** `a07672eab23dfb5b956e5426b32ccb09e5dff7ac`

**Build/test run:** https://github.com/MohnishDhangar/Cambc/actions/runs/39418781975

**WASM download:** https://github.com/MohnishDhangar/Cambc/actions/runs/39418781975/artifacts/12263131345

**Binary SHA256:** `33a6fb5cb5ae058527ffc15d9b4afa53be83b9fc39336cec45bba53e7e5428ee`

The binary comes from released CAMBC 2.2.5 + WASI SDK 33.0. The nine-map, both-sides regression suite completed **18/18 matches**, **9 v5 wins**, **zero bot faults**, **mean gem margin 0.0** against the archived v4 executable/source. The 9–9 symmetry indicates no evidence of a gain or loss on the old engine.

Experiments that were rejected and reverted: mixed early-shop/combat/camp utility (0/18, -385.89 average margin), E01 early 90-gold shopping near home (8/18, -38.44), E04 increased altar-return penalty (7/18, -19.89). Do not include those changes in a field upload.

Current field candidate retains v4 strategic selection, plus dynamic camp HP/damage, major camp classification, actual camp attack range, and a fallback when no risk-free spellcasting tile exists (the latter is needed for Golem/Monolith on Week 2 maps, but cannot be validated under old 0.0.3 maps). Stdout marker now says `Bot1 strategy v5 Week2 (SDK 2.2.5)`.

**Next gate:** upload the verified source ZIP to the live 2026a website and collect at least 20 consecutive games, preserving exact match IDs and replay data. See [V5-FIELD-TEST.md](V5-FIELD-TEST.md).



## Basis and compatibility

Primary source: **Patch Notes – Week 2**, posted 20 October 2026. Do not use previous rules or pre-patch replay outcomes as proof of patched-game performance.

The repository's existing SDK and supplied CLI identify as `cambc 2.2.5`. **That installed SDK does not expose `camp_type::golem` or `champion_draft::heart_of_ruin`**, so it predates the breaking enum changes described in the patch. A true patched-engine compilation and match evaluation has **not yet been completed**.

## Patch changes to account for

- Cassi: base HP 700→600; HP growth 71.25→65; Strength growth 3.5→3; Focus growth 15→13.
- Issac: HP growth 95→80; Strength growth 4.75→3.
- Stellar: Focus 100→85; Strength 35→30; Focus growth 10→9.
- Varg: Strength 50→40.
- Ren: Strength 40→35; Focus growth 10→9.
- Ryth: Strength 50→45.
- Marcella: 2 gold per gem tributed, stun immunity retained; Focus 50→60, Focus growth 10→15.
- Willow: Strength 45→55, Focus 105→120.
- Vesper Vale: gold passive 20%→33%, Strength 45→50.
- Vendetta: Strength growth 5→6.
- Prism: carried-gem Focus bonus 0.2→1 per gem; Health growth 75→60, Strength growth 3.5→2.5, Focus growth 10→8.
- Tavi: ability S2 multiplier 2.2→1.4× Focus; Strength 35→45.
- Heart of Ruin: new melee champion (1000 HP, 40 Strength, 100 Focus, growths +100/+5/+15), missing-health damage passive, self shield, dash AoE stun.
- Wolf gems 22→4 and gold 90→40; Elk gems 36→15, gold 160→90, range 3→4; gem cluster HP 500→120 and gems 24→7; gold cluster HP 500→120 and gold 35→20; monolith range 3→5.
- Golem: new camp (5000 HP, 120 Strength, attack range 4, 160 gold, 36 gems, respawn 80).
- Champion-kill gold 50→100; ward cooldown 1→10; altar-lock durability 3→5.
- Breaking API changes: new camp/champion enums and dash ability payload changes.

## Initial v5 changes in this branch

1. Remove the five-element hard-coded camp HP / damage arrays. Use engine-provided camp design stats instead to prevent out-of-bounds access with a new camp enum and stale reward difficulty estimates.
2. Determine large-objective thresholds from engine-reported health instead of fixed old camp-type HP constants.
3. Use each camp's actual attack range in siege safety computation. If no zero-damage firing tile exists, allow a candidate tile while applying the existing danger-aware movement (still needs battle testing).
4. Protect gem carriers by prioritizing banking before discretionary fights.
5. Give attack-reset champions an opportunity for a second hit against enemy altar locks.
6. Add a bank-stall fallback to seek lower-danger altar approach or recall.
7. Record planning version 5 in draft memory.

## Available-client compile and smoke results — 20 October 2026

The complete v5 branch compiled successfully with the released CAMBC 2.2.5 client and WASI SDK 33 in GitHub Actions **run 39401603392**. Build artifact: `Bot1-v5-available-client`. This is source compatibility with the available (pre-patch) SDK, **not** confirmation of compatibility with a future/updated patched server API.

A subsequent run, **39401800786**, again compiled v5 and also built the frozen `bots/Bot1/Bot1-v4.zip` source as a separate `BaselineV4` opponent. Full release-mode games on the repository's `maps/packs.map26a`, using the released 2.2.5 engine:

| Candidate side | v5 tributed gems | v4 tributed gems | Winner | Rounds | Bot faults |
| --- | ---: | ---: | --- | ---: | ---: |
| A | 804 | 1,032 | v4 | 457 | 0 both sides |
| B | 984 | 1,032 | v4 | 479 | 0 both sides |

Both matches completed; their statistics and replay bundles were uploaded as the `Bot1-v5-smoke-vs-v4` workflow artifact. The v5 WASM was uploaded as `Bot1-v5-available-client`.

**Interpretation:** the candidate does not yet outperform v4 on this old map. These two games are too few to estimate a win rate and use the *pre-Week 2 engine*, so they must not be treated as evidence for the patched competitive metagame. Before deciding on v5 changes, diagnose the lost points on these replays and collect matches with the updated server rules when possible.

## Required next checks (not claimed complete)

- Obtain the refreshed post-patch `cambc` binary/SDK/engine and run `cambc init` in a **separate test project**. Confirm `golem`, `heart_of_ruin` and revised dash payload are present in the generated SDK.
- **Completed with available client 2.2.5:** built frozen v4 separately as `BaselineV4` and compiled v5. Repeat with the actual Week 2 engine when possible; never overwrite archived v4 artifacts.
- Inspect and correct new-champion handling in the draft. The current draft remains the proven v4 ordering and does not yet pick Heart of Ruin.
- Revisit all siege objective rules: range-five monoliths invalidate risk-free range-four caster cheese.
- Validate `cam[b]c::camp::base_stats` remains valid for the updated SDK and update any renamed APIs.
- Run head-to-head paired seeds/maps, both team sides; collect results and first-failure examples.
- For pre-patch archived replay analysis, tag as `engine-0.0.3 / pre-week2`; never mix with post-patch score averages.
- Test lock removal, team claims, bank-stall escape, capture behavior, min fuel, and no-error execution on several maps.

## Commands after updating the client

```sh
./tools/cambc --version
./tools/cambc init
./tools/cambc build Bot1 --release
./tools/cambc run Bot1 starter-cpp --release --map maps/packs.map26a --out-dir results/v5-smoke
```

The `tools/cambc` wrapper requires the ignored `.cambc/client/cambc` binary. Store match data under a unique results directory to prevent overwriting history.
