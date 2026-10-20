# Audit: what "fuel spill" actually counts (CAMBC Bot6)

**Source:** `bots/Bot6/src/main.cpp`, frozen v6.8 and experimental descendants. Code:
```cpp
const auto started = cambc::round_number();
// play_draft() or bot.play_turn()
if (!cambc::is_draft() && cambc::round_number() != started)
    std::cout << "fuel spill at " << bot.action << " from " << started << " to " << cambc::round_number() << '\n';
cambc::end_turn();
```

The replay count is **not a direct readout of `fuel_remaining()`**, an engine "out of fuel" status, or the engine's `diagnostics.botFaults` metric. It only counts rounds that changed while `play_turn()` was executing. A costly operation or implicit yield might produce such a transition, but the label alone cannot establish causation.

Preserved observations on 17 training maps (34 games per version vs frozen v4):
- v6.6: 399 logged round crossings; 21 wins; zero reported engine faults.
- v6.8: 52 logged round crossings; 21 wins; zero reported engine faults.
- v6.9 32k thresholds: 47 logged round crossings; 21 wins; gem margin worsened.
- v6.9 48k scouting guard: 46 logged round crossings; 20 wins; gem margin worsened.

Thus the improvement from v6.6 to v6.8 correlates with pathfinding optimization but is not itself conclusive proof of 87% fewer actual WASM fuel exhaustions. Previous experiment labels and dashboards should read **"round-crossing diagnostics"**, with the legacy event string retained for reproducibility.

Before further fuel-specific tuning, instrument actual `fuel_remaining()` at bounded checkpoints and correlate each event with SDK action/yield behavior and the engine's actual fault accounting. Avoid excessive logging that itself changes fuel usage. Keep source hash, map/side, opponent and seed fixed. Do not modify the four held-out maps `00lanes`, `01corridors`, `01hooks`, `01islands`.
