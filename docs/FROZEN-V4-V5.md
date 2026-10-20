# Frozen CAMBC baselines — v6 development boundary

**Freeze date:** 21 October 2026. V4 and V5 are **read-only historical baselines**. No further edits or releases from their source directories are authorized as part of v6 development.

## Frozen revisions and artifacts

| Baseline | Frozen reference | Source/artifact identity |
|---|---|---|
| v4 | `frozen/v4-baseline-20261021` at `333bc334fa7c5eeac8bf99c79f99e5fffb4543b4` | `bots/Bot1/Bot1-v4.zip` (SHA256 `b296e83d43e8b16709e655ee4470a526e9e84160ee02fbad0e8c483661e1a062`) and `bots/Bot1/Bot1-v4-manifest.json` |
| v5 final runtime hotfix | `frozen/v5-hotfix-20261021` at `48c72e9a1edf71b1697d0ce90709f6d65602c8bd` | Six files in `bots/Bot1/src/` from this immutable commit; tested hotfix source ZIP archived at `fix/v5-live-runtime-20261020:submissions/Bot1-v5-hotfix.zip` (SHA256 `69ce6ce76f288d00f48347aabc8a8494ffa4d02c2f6200f845a3f46ade571f24`) |

**Caveat:** The v4 artifact is an archived ZIP; the `Bot1/src` directory at the v4 freeze branch's main-derived commit may contain later development. Reconstruct the v4 source from `bots/Bot1/Bot1-v4.zip`, **not** by copying the working `Bot1/src`.

The v5 hotfix was compiled and tested against the older CAMBC 2.2.5 local engine, completing 18 matches (10 wins against frozen v4, 0 reported faults); this did **not** establish a live Week 2 win-rate advantage. Preserve that evaluation as historical evidence only.

## New v6 source of truth

- `bots/Bot6/src/` is the **only** active bot source tree for new development.
- `develop/v6-macro-v0` contains modular macro-policy experiments and is **not automatically a ranked competitive upgrade**.
- `docs/V6-ELITE-STRATEGY-RESEARCH.md` and `match-data/analysis/v6-elite-research/v6-map-split.json` set the research protocol.
- Test/training maps: 17 mapped by the split manifest. **Never** use `00lanes`, `01corridors`, `01hooks`, or `01islands` in strategy development benchmarks, including smoke tests.
- We do not modify source ZIPs, branches, archived matches, or experimental scores belonging to v4/v5; additional fixes must enter v6.
- Frozen branch refs are archival conventions, **not GitHub branch-protection settings**; only the immutable commit SHAs / archive hashes guarantee exact reproduction. Do not force-push these branches.

## Release gate

Before promotion: compile on CAMBC 3.0.1 or pinned compatible current patch engine, complete reproducible non-held-out paired matches, verify no runtime exceptions/fuel faults, test task coordination in multi-champion games, and establish win-rate or score improvement over the frozen baseline on the currently supported engine. Do not interpret old 2.2.5 results as patched-engine evidence.
