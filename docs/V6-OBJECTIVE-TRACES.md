# Objective-map trace profile

Read-only telemetry applied to temporary recompilations of pinned v6.8 and v6.14; the release sources themselves are unmodified. Both trace against frozen v4 in eight games total: `00contest` and `01boss-battle`, starting A and B. Sample champion state/action every 25 rounds and in first 20 rounds to test the hypothesis of early siege inactivity. The extra printing may alter per-turn fuel consumption and match play, so these traces are **diagnostic**, not a fair competitive comparison or promotion gate.

Do not read or tune on 00lanes, 01corridors, 01hooks, or 01islands. All output restricted to the named two development maps, no user-supplied opponent data.

Run GitHub Actions `CAMBC permitted objective-map action tracing`; inspect `match-data/analysis/v6-objective-traces/summary.json`. 
