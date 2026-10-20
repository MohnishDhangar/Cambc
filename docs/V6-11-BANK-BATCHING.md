# v6.11 — Adaptive banking throughput experiment

## Hypothesis
Pinned v6.8's `V6_BANK_THRESHOLD=0` makes `should_bank` true upon acquiring even one gem. Champions can repeatedly travel long distances to altars rather than collecting several camps per trip. For distant camps, adaptively batching 4–10 gems may improve farm/capture-to-tribute throughput and reduce travel time; near altars, retained `altar_distance<=2` immediately banks, and the final 400 rounds flush any bag.

## Isolation and risks
Changes only banking threshold in `play_turn` using optional `V6_ADAPTIVE_BANK_BATCH`. Legacy threshold remains in `#else`. v6.8 baseline pinned at `0ddd5338b94db824f9f53261a17f020490b7017f`. Potential costs: bigger bags may be stolen or lost, and a channel can become longer. Competing against elite opponents requires separate validation.

## Prespecified benchmarks
CAMBC 3.0.1, frozen v4 plus pinned v6.8 controls, three 34-game pairings across 17 permitted maps and both starting sides. Source replays from public field opponents remain private. Never train on `00lanes`, `01corridors`, `01hooks`, or `01islands`. Record failures and do not promote without reproducible superiority.
