# v5 field-test plan — Cambridge Battlecode 2026a, Week 2

**Status:** Experimental candidate; submit to live ladder for controlled testing, not as a claim of improved win rate.

## Binary provenance and build

- Source branch: `develop/v5-week2`.
- Source of truth: the GitHub Actions `V5 compile with available CAMBC 2.2.5` workflow attached to the exact source commit.
- Download the `Bot1-v5-available-client` artifact, extract `Bot1-v5.wasm`, upload that module using the official CAMBC website.
- Never upload the old archived v4 `.wasm` or the pre-rollback v5 binary by mistake. Check the Actions run SHA and build output hash.
- Record the exact deployed git SHA and upload time in a field-test CSV. If the server rejects the module, do **not** continue testing; report the rejection and update the compatibility status.

## Rules caveat

The official downloadable client is `cambc 2.2.5` with the archived pre-Week-2 engine. The October 20 Week 2 patch adds Heart of Ruin and Golem and changes balance. Compilation and head-to-head tests with 2.2.5 are compatibility/regression tests **only**. Only ladder submissions and new match replays can measure performance under the new rules.

## Intended differences from frozen v4

1. Read camp baseline HP/Strength dynamically from the engine rather than indexing a five-entry type table, which would break on new Golem camp types.
2. Treat >=4500 HP gem-bearing groups as major targets for candidate selection (Golem and Monolith).
3. Use actual camp attack range in siege risk assessment.
4. When no zero-threat spellcasting position exists (Golem/longer-range Monolith), consider reachable positions within spell range rather than idling; existing recovery and health restrictions still apply.
5. Label stdout with `Bot1 strategy v5 Week2 (SDK 2.2.5)` to separate it from v4.

The original v4 farm, shopping, and combat policies are preserved after unsuccessful offline experiments. Additional high-Elo-inspired features must pass controlled tests before promotion.

## Match collection protocol

Start with at least **20 consecutive** live matches (do not curate winners/losers):
- Prefer roughly 10 at similar Elo and 10 versus distinctly stronger teams, when matchmaking allows.
- Record the exact git SHA, timestamp, opponent, Elo if shown, draft, map ID, match ID / website URL, result from the official website, gem scores, game length and visible faults.
- Save each raw replay, `team-a.stdout`, `team-a.debug`, `team-a.fuel`, and screenshots/notes if relevant.
- Keep all raw replays under `match-data/v5/field-001/` or externally if large. **Do not rely on win/loss directory labels for ground truth**: the old v4 collection contained 46 incorrect labels out of 245. Store the official result in the manifest and verify the replay's team identity and engine outcome when the decoder supports it.
- Stop immediately if the server reports invalid module, champion-draft errors, turn exceptions, or repeated fuel exhaustion.
- Compare early scoring at rounds 100/200, gem secured/collected, deaths and gold development against archived v4 statistics only as contextual indicators, not a fair win-rate head-to-head under different patch rules.

## Experiments already screened on released 2.2.5 engine

| Test | Paired maps/sides | Wins v5 | Gem margin mean | Decision |
| --- | ---: | ---: | ---: | --- |
| Patch-safe copy of v4 with only required compatibility changes | 18 | 9 | 0 | Baseline stable |
| Combined early-shop + changed combat + changed target utility | 18 | 0 | -385.89 | Rejected |
| E01: early 90-gold shopping near spawn | 18 | 8 | -38.44 | Rejected |
| E04: increase camp-to-altar penalty from 0.35 to 0.60 | 18 | 7 | -19.89 | Rejected |

These old-engine observations do **not** establish that the same changes would perform identically on the Week 2 server.

## Next actionable development goals

1. **Live compatibility smoke:** Does the latest source build upload and complete 5 matches without faults?
2. **Opening tempo:** On any live loss, identify the first 100/200-round score gap and the champion or camp decisions preceding it.
3. **Carrier survival and local PvP:** Compare deaths, gem losses, and allied focus opportunities versus opponents.
4. **Patch-specific camps:** Validate Golem 5000-HP combat and 5-range Monolith behavior on maps where they exist.
5. **Policy promotion:** Keep changes only after reproducible head-to-head evidence, or a documented live-specific compatibility necessity.

## Data field template

```csv
match_id,replay_path,match_url,played_at,bot_sha,opponent,opponent_elo,map_id,team_side,official_result,our_tributed,opponent_tributed,rounds,notes
```
