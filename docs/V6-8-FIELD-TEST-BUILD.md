# v6.8 field-test build

This branch holds **exactly the tested v6.8 Bot6 source** from commit `0ddd5338b94db824f9f53261a17f020490b7017f`. The extra GitHub Actions workflow builds official CAMBC 3.0.1 release WASM, checks the Bot6 bot.cpp sha256 hash `f74745b290dd9c2f9b6a6b46a1128d031ae080d5d9b024993a7b554198c5e7ac`, and uploads a field-test kit:

- `Bot6-v6.8-CAMBC3.0.1.wasm`: upload to Battlecode competition
- `Bot6-v6.8-source.zip`: six-file source submission package
- `Bot6-v6.8-manifest.json`: exact version/SDK/file hashes

Artifacts are attached to the Actions run named "Build pinned v6.8 field-test WASM".

For official field testing, record opponent, source/strength (if known), map, side, result, round, submitted gems, camp captures, and a concise note on the failure mode. Official/third-party opponents are **out-of-sample** and must be reported separately from v4-v6.8 paired train-map outcomes.

Do not load any of the four held-out maps into tuning: `00lanes`, `01corridors`, `01hooks`, `01islands`.
