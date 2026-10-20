# v6.6 fuel spill diagnosis

Confirmed experimental blocker: the 17-map v6.6 policy sweep reports 399
fuel-spill events on its selected economy/bank-0 variant, despite zero reported
bot faults. In its recorded games CSV, 361 of those are on 01big-world
(176 from side A and 185 from side B), with 38 more on
01concentrated-wealth (20 A and 18 B).

The rejected v6.7 tribute experiment increased spills and worsened its paired
win rate. Keep v6.6 source unchanged until the failure location is established.

This research workflow runs exact pinned v6.6 and frozen v4 on
01big-world, 01concentrated-wealth, plus 00contest as a training-map control,
both starting sides. It parses the bot's own output marker
"fuel spill at ACTION from ROUND to ROUND" and records a per-action histogram.

Result path: match-data/analysis/v6-fuel-profile/profile.json
Full action counts: match-data/analysis/v6-fuel-profile/actions.csv
No held-out maps are used. Only after profiling should a limited fuel
budget/pathfinding optimization be implemented and tested against pinned v6.6.
