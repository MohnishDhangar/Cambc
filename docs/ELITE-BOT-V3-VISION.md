# EliteBot v3: information-oriented warding

## Motivation
In 161 unique permitted elite-opponent replays, the observed teams attempted ~2.14× as many wards as v4. Frequency itself is not a target: original vision algorithm only considered bushes and selected the first available position. Test whether ward placement chosen for incremental fog coverage improves scouting and income.

## Isolated change
Start at pinned v6.8 `0ddd5338b94db824f9f53261a17f020490b7017f` (including proven draft). Only replace the ward targeting strategy in a separate `bots/BotElite/src/bot.cpp`, with `ELITE_INFORMATION_WARDS` feature flag. Rank at most 18 legal placement positions by unseen fog in Chebyshev-4 radius, with a small bush bonus; do not place a ward without expected information gain. Respect fuel guard (>=32k before, >=27k during). No added scouting calls; existing invocation frequency unchanged.

## Benchmark
CAMBC 3.0.1 paired 102 matches, 17 training maps mirrored A/B; v3 vs frozen v4 and pinned v6.8. Check wins, gem margin, fuel and exceptions. Track ward usefulness in follow-up telemetry, if win differences warrant. Sealed maps `00lanes`, `01corridors`, `01hooks`, `01islands` never used. No frozen reference modification.
