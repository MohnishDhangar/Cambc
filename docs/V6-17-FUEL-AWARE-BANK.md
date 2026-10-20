# v6.17 fuel-aware banking recovery

## Prior validated hypothesis
Pinned `v6.16` commit `3d611d14a27863e50fe4fc32269b53127851dfc5` fixed a confirmed `NAVEMPTY` bank deadlock and measured 24/34 wins vs frozen v4 (+129.03 average submitted-gem margin) versus v6.8's 21/34 (+91.47) on 17 development maps A/B. However replay fuel spill events rose 52 -> 62, mostly on large camp maps. v6.16 is NOT certified dominant or release-ready.

## Change
Keep the successful v6.16 nonblocking banking: when `navigate(goals)` does not advance, permit `defend()` / `farm()` on the same turn. But use `V6_BANK_FUEL_GUARD=1` to require >=45,000 remaining Wasmtime fuel for this additional potentially costly work. The legacy v6.16 return policy remains under `#else`. Hypothesis: preserve small-map gains while reducing stalls and runtime suspension on large maps. Risk: some productive turns suppressed with too little fuel.

## Reproducibility
CAMBC 3.0.1. Fixed v6.16 pinned source as control; frozen v4 archive SHA256 `b296e83d43e8b16709e655ee4470a526e9e84160ee02fbad0e8c483661e1a062`. 102 games: candidate vs frozen v4, control vs frozen v4, candidate vs control; 17 allowed development maps, both sides. Held-out 00lanes, 01corridors, 01hooks, 01islands never accessed. No automatic promotion on CI success.
