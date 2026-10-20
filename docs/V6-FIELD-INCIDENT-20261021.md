# CAMBC v6.8/v6.9 field replay incident — 2026-10-21

## Inputs and integrity
Two nested user-provided ZIP archives: 24 deduplicated v6.8 replays and 25 v6.9 replays. One v6.8 group export was duplicated. Binary replays were fingerprinted by SHA-256; embedded map files were fingerprinted using Git blob hashes against repository maps, **before** selecting training observations. **Three v6.8 and two v6.9 replays were on held-out maps (00lanes, 01hooks, 01islands) and were excluded from all non-held-out statistics.** 01corridors was not present among recognized files. Unrecognized external map hashes are not asserted to be controlled test cases.

User's original replays and opponent data are confidential and remain off GitHub. Official v3.0.1 replay simulation is required to reconstruct victory, captured gems, tributed gems and per-round positions; uploaded archives contain game inputs and team-A fuel/stdout logs, not human-readable scores. We must **not** claim a specific score, win rate or choke cause from these archives alone.

## Permitted/non-sealed runtime observations
| Metric | v6.8 | v6.9 |
|---|---:|---:|
| Deduplicated recordings | 24 | 25 |
| Excluded held-out recordings | 3 | 2 |
| Remaining field recordings | 21 | 23 |
| Recorded fuel-spill messages | 30 | 31 |
| Matches with fuel spills | 3 | 4 |
| Navigate walk last-action markers | 15 | 28 |
| Ward scout last-action markers | 14 | 2 |
| Navigate crystal last-action markers | 1 | 1 |

Thirteen non-sealed replay payloads match byte-for-byte across versions. Last-action markers identify the action most recently entered before suspension, not necessarily the exact instruction responsible for fuel exhaustion. Logs contain no demonstrated caught exception on these samples.

## Verified source-level bottleneck hypotheses
1. At an altar, `bank()` can reject a tribute due to a conservative danger comparison, then call `navigate(goals)` when already in those goals, returning without useful action. This is a real code-path risk, but frequency in ladder matches is unconfirmed without replaying with the SDK.
2. With `V6_BANK_THRESHOLD=0`, carriers can return even with only one gem, paying potentially long travel costs and interrupting farming.
3. When all camps fail the strict expected-damage test, `select_camp()` may return -1; `farm()` may return to spawn and remain inactive if still healthy.
4. Banking navigation only switches to danger-aware escape movement when health is below 50%, exposing carriers to interceptions; source-level hypothesis, not measured death counts.

## Controlled ablations — 17 development maps, both sides, CAMBC 3.0.1
Reference pinned v6.8: 21/34 wins vs frozen v4, +91.47 average tributed gem margin, 52 recorded fuel-spill events in this pairing.

- **v6.10** unconditionally submit at adjacent altar; 20/34 vs v4, +32.32 margin, 47 spills; direct v6.10 vs pinned v6.8 18/34. Rejected despite remedying the stalled code path; likely danger from exposing carriers, a hypothesis.
- **v6.11** bank 4–10 gems using return distance; 19/34 vs v4, +50.06 margin, 28 spills; direct vs pinned v6.8 17/34. Rejected. Fewer fuel events alone are insufficient.
- **v6.12** guarded moderately riskier farming only when no safe targets; 20/34 vs v4, +66.53 margin, 52 spills; direct vs pinned v6.8 17/34. Rejected.
- **v6.13** carrier danger-aware evasion: benchmark pending at initial report authoring; inspect `develop/v6.13-carrier-threat-evasion`.

Each branch retains baseline in its comparison script and compiles a pinned v6.8 control plus frozen v4. CI passing simply means complete games and successful compilation, **not** candidate promotion. No branch above was merged into frozen references or the v6.8 field-test line.

## Next measurements
Decode full field-match replays through the **exact matching official CAMBC v3.0.1 simulation engine** to obtain per-round scores, captures, death-associated gem loss, contested altar time, no-op turns, and farm trip distances. Then run controlled tournaments against a diverse opponent pool using held-out-safe maps and multiple seeds. Stronger-than-v4 competitive edge is not yet established.

**Never tune or train on 00lanes, 01corridors, 01hooks, or 01islands.**
