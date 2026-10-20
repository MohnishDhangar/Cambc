# v6.16 — Nonblocking bank failure recovery

## Root cause supported by traced simulations
On permitted `01boss-battle`, the pinned v6.8 team scored 0 gem tributes although champion endgame states showed bags between 8 and 29. Temporary instrumented v6.8 copies logged repeated `NAVEMPTY` at many rounds while holding gems. This signal appears in `navigate()` when the altar-adjacent goal bitboard becomes empty after removing `terrain | occupied()`. The prior `bank()` called `navigate(goals,...)` and returned `true` even if navigation returned `false`, blocking `defend()`, `siege_objective()`, and `farm()` for the turn. Tracing run: https://github.com/MohnishDhangar/Cambc/actions/runs/39512618795.

## Fix / hypothesis
A one-line behavioral change behind `V6_NONBLOCKING_BANK=1`: return the result of `navigate(goals,...)` instead of blindly returning `true`. If no move is performed, fall through to defending and productive farming rather than no-op. Successful movement or completed tribute retains the existing return behavior. Pinned control v6.8 commit `0ddd5338b94db824f9f53261a17f020490b7017f` is preserved.

This is **not** a general solution for inaccessible altars. If all reachable altars are sealed by terrain, a bot may never submit; this fix aims to prevent deadlock and improve fallback economic actions, especially gold tiebreaks. Risk: if a champion temporarily cannot move during an otherwise viable bank trip, it may waste actions on other objectives or expose a bag.

## Test & control
CAMBC 3.0.1, three pairings 34 games each, 17 allowed development maps both sides: candidate vs frozen v4, pinned v6.8 vs frozen v4, candidate vs pinned v6.8. The four heldout maps `00lanes`, `01corridors`, `01hooks`, `01islands` remain completely excluded. Source + benchmark + CI isolated to `develop/v6.16-nonblocking-bank-fallback`. No promotion without reproducible higher win counts, better tribute margin, and no runtime/fuel faults.
