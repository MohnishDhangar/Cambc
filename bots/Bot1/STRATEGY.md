# Bot1 v4 — cooperative captures and ranged objectives

Upload **[Bot1-v4.zip](Bot1-v4.zip)**. It contains the source for CAMBC SDK 2.2.5. The corresponding release build is `Bot1-v4.wasm`; historical v1/v2/v3 archives are preserved.

## What was retained after local comparisons

The starting design came from the [17 paired platform maps against lll](../../match-data/analysis/paired-v1-v3/REPORT.md). Implementation experiments showed that a wholesale replacement of v1's farming policy reduced income. V4 therefore combines its productive farming core with new capture allocation and a separate strategy for difficult scoring objectives.

- **Ordinary maps:** Tavi, Varg, Vendetta, Ryth, Vesper Vale; Varg takes the first pick when groups of three or more camps are common. Prioritize unclaimed work, then help claimed live groups. Claims are planning hints, not proof that an ally is already contributing.
- **One recipient per capture:** choose a nearby visible participant using distance, current occupancy, equipment investment, and stable slot order. Cache that choice through the capture. Helpers leave reward tiles and immediately seek other work. Lower investment receives preference so one farmer does not take every upgrade. Re-elect when the recipient disappears, dies, recalls, acquires gems, or abandons its claim. Limited individual vision can still cause disagreement; zero split captures is not guaranteed.
- **Actual camp threats:** only awake, living monsters contribute to camp danger. Missing health alone does not make a sleeping camp dangerous.
- **Runtime:** restore the smaller v1 navigation and decision loop, with two shared-purpose static distance fields rather than a full field for every altar. Keep existing action-fuel reserves. All 102 release-mode checks completed without exhaustion; this is evidence on the supplied maps, not a bound for every possible map.

## Difficult scoring objectives

If every gem-bearing group has at least 10,000 initial health, ordinary farming excludes those groups and a separate siege policy handles them. This covers both monoliths and the supplied six-elk/six-gem-cluster group. The classifier uses camp contents, not map hashes or opponent identity.

**Monolith draft:** Stellar, Prism, Tavi, Ren, Varg.

**Large non-monolith objective draft:** Varg, Ren, Stellar, Tavi, Ryth.

Casters first farm gold. They become eligible to siege with at least 180 Focus, or from round 400, provided they have at least 45% health. Completed gold captures are finished before switching jobs. Other farmers continue earning resources.

The siege computes positions outside the attack range of every remaining damaging monster in the target group, but within spell range of a living target. Monsters use Chebyshev range three; the relevant targeted spells use Euclidean range four. Against a single monster, only the four cardinal positions at distance four satisfy both constraints. Terrain and occupied tiles can reduce the available positions. As outer monsters die, new firing positions become available for the interior of a large group.

Casters hold those positions, spend available damage/control spells, and move when the target is obscured. Local replay reconstruction confirmed that damage persists when a monster sleeps. Clearing and capturing remain separate jobs: after the group dies, elect a recipient, collect the bag, and tribute it. Enemy champions can contest firing positions or steal a capture; safe monster range does not imply safety from opponents.

## Equipment and combat

Basic-attack farmers keep Monster Strength, Jungle Strength, spawn-purchased Health, then more Strength. Objective casters build Power Focus, with a Durability Health emblem after two Power Focus emblems when shopping at spawn. Tavi buys in the field; Health purchased there does not heal.

Nearby combat and reliable recall/tribute behavior use the v1 foundation. This intentionally avoids the first v4 prototype's over-cautious travel and repeated rallies, but leaves a measurable weakness in contested fights. The full suite includes substantial casualties against v1 on some maps. It is not the old v3 survival policy with a new version number.

## Evaluation and limitations

Release mode, SDK 2.2.5, engine 0.0.3, client-default fuel, all **17 distinct supplied maps**, both sides:

| Opponent | Wins | Games |
| --- | ---: | ---: |
| Frozen v1 | 19 | 34 |
| Frozen v3 | 32 | 34 |
| Local starter | 34 | 34 |
| Total | 85 | 102 |

**Zero caught errors, bot faults, and raw replay fuel-exhaustion events.** The monolith and large-elk cases won all eight comparisons against v1/v3 on both sides. Some games reach the round limit, where the game's normal score and gold tiebreaks apply.

See [the complete results and source manifest](../../replays/v4-release-evaluation/REPORT.md). These are deterministic local regression comparisons, not an estimated lobby win rate. The opponent lll's adaptive bot is unavailable locally; its recordings informed the design but were not treated as a reusable opponent.

Known weaknesses include the compact 30×30 map, contested routes on 100×100, side-dependent losses on rows and 80×80, partial-vision recipient disagreement, and optimistic estimates of help from a claimed camp. V4 is an improvement over v3 in this suite and a modest improvement over v1; it is not a universal replacement for v1 on every map.

## Reproduce

From the project root:

```bash
CAMBC_OFFLINE=1 CAMBC_NO_UPDATE_CHECK=1 python3 bots/Bot1/scripts/evaluate_v4.py \
  --opponents BaselineV1 BaselineV3 starter-cpp --sides A B \
  --output replays/v4-new-evaluation --jobs 2

CAMBC_OFFLINE=1 CAMBC_NO_UPDATE_CHECK=1 ./tools/cambc build Bot1 --release \
  --output bots/Bot1/Bot1-v4.wasm
```

Use a new evaluation output directory. Versioned ZIP files are deliberately not overwritten. Each run records source hashes, complete replay inputs, statistics, candidate stdout, and diagnostics.
