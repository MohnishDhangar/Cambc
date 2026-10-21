# v6.18 bank-progress recovery experiment (not promoted)

## Data and hypothesis
User field uploads: 50 distinct v3 and 60 distinct v5 replays; recorded local bot output contains 68 and 97 fuel-spill markers respectively, with no caught errors in either set. These are **not labelled against the full match outcomes**, and must not be used as a substitute for official score decoding. Training-only earlier replay traces on `01boss-battle` indicate champions holding bags >0 while staying stuck in `navigate`; camp bodies can block the walking route to an altar. Code audit confirms `bank()` historically returns `true` regardless of `navigate()` progress, indefinitely preempting farm or siege.

## Change
Preserve six pinned v6.8 files except `bot.h` (two watchdog fields) and `bot.cpp` (feature flag). On three consecutive bank navigation attempts without movement, enter a 22-round temporary detour to resume productive `farm/defend/siege`, retaining carried gems. Immediate altar, threat, and low-health requests override detour. Successful navigation resets stall count. This is a *fallback*, not a complete solution to blocking camps; 22 rounds is an unoptimized initial hypothesis.

## Controlled evaluation
CAMBC 3.0.1, v4 archive verified SHA256, exact pinned v6.8 `0ddd5338b94db824f9f53261a17f020490b7017f`. Three 34-game pairings, all 17 approved maps mirrored A/B = 102. Report wins, tributed gems, exceptions, fuel spills and objective-map zero-tribute subset. No held-out maps `00lanes`, `01corridors`, `01hooks`, `01islands`. No source modifications to frozen v4/v5.

## Promotion gate
Only retain if the change improves multiple objective maps and general v4 win performance without increased zero-gem failures, caught errors or fuel spills. CI success alone is not proof.
