# v6.19 bank-route camp clearing: controlled ablation

**Source and control**: exact compiled v6.18 bank-progress source `7eef7a7fb031a62161d23decb832361484df535c`. It scored 21/34 vs v4 and +103.53 mean submitted-gem margin; still zero on `00contest` and `01boss-battle` and 53 fuel-spill events. v6.18 is itself experimental and not promoted.

**Hypothesis**: v6.18's economic detour often selects arbitrary farming targets rather than camp groups physically obstructing the shortest terrain-only approach to an altar. When the bank watchdog detects three failed navigation attempts, prefer a *visible*, alive, non-major and locally survivable camp group within 12 tiles whose static altar gradient is smaller than the carrier's current gradient. Release the bank claim and farm that camp for the watchdog's 22-turn detour. Existing legal movement/ability checks remain untouched. Group selection is heuristic and not a proof it lies on the exact route.

**Isolation and safety**: new compile-time flag `V6_ROUTE_CLEARING=1` alters only `bots/Bot6/src/bot.cpp`; five other source files remain byte-identical to pinned v6.18. No hidden information. SDK CAMBC 3.0.1. Frozen v4/v5 unchanged. 17 development maps both sides, 34 games candidate-v4, 34 exact v6.18-v4, 34 candidate-v6.18 (102 total). The four sealed maps never touched.

**Acceptance**: wins and absolute gems on `00contest` and `01boss-battle`, general win rate, mean margin, zero-tribute games, engine faults, fuel spills and exceptions. No claim of success before results.
