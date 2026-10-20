# v6.13 — Carrier threat evasion

Hypothesis: Pinned v6.8 goes to its altar via ordinary greedy distance routing unless health is already below 50%. A gem carrier exposed to nearby enemy interception may lose valuable unbanked gems. Only in `bank()`, when carrying at least three gems and a visible enemy is within their attack range plus two tiles, switch navigation to danger-weighted escape routing (SDK full path field). No other decision changes; legacy behavior retained under `#else`.

Potential regression: expensive full-grid path computation, route hesitation, fewer tributes. Controlled 102 games v6.13/v4, pinned v6.8/v4 and v6.13/v6.8 across 17 permitted training maps, sides A/B, SDK 3.0.1. No held-out maps permitted; user field replays excluded any known held-out maps. No promotion without objective evidence.
