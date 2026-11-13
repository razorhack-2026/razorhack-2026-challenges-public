# Shadow Price: Brownout — solution (GM-only)

**Flag:** see `../challenge.yml`. **Reference solver:** `solve.py` (solves both parts).

## Intended solve

1. **Connect and browse.** `opc.tcp://<host>:4840/pmc7/`, anonymous, SecurityPolicy None. Everything is under `Objects/PMC7`:
   - `Reactor/RatedOutput_MW`, `BusSegments/{FWD,AFT}/Capacity_MW`, `CoolantLoops/{A,B}/Capacity_MWth`
   - `Loads/<load>/` with `BusSegment`, `CoolantLoop`, `CoolantPerMW`, `DispatchWeight`, `Floor_MW`, `FloorSense`, `Cap_MW`, `Description` (17 loads)
   - `Info/Objective` and `Info/Constraints`, which spell out the LP in words
   - `LoadOrder` (the argument order for the method), `CurrentDispatch/*`, and the `ApplyDispatch` method
   - `Info/LastModelChange` says the model was written by an anonymous session (SecurityPolicy None) with no operator login. Combined with the brief's "The model changed during that lockout. Nobody on the crew changed it.", that tells players to suspect the model itself. It never names which node changed.
2. **Replay the controller's own dispatch** (optional, but it's what a player does first). Calling `ApplyDispatch` with `CurrentDispatch` in `LoadOrder` order gives `life_support ALARM short 15.94 MW` at 98.50 % efficiency.
3. **Diff the primary floors against the mission spec** in the brief. Every value matches, but `life_support.FloorSense` is `LE`: the model says life support may draw *at most* 18 MW. Life support has a tiny `DispatchWeight` (0.2), so the optimizer drains it to feed higher-value loads. Flip the sense to `GE`.
4. **Solve the corrected LP.** Maximize Σ weight·x subject to reactor ≤ 100, segment caps, loop caps (Σ coolant·x), floors (`GE`), and caps. 17 variables. Any LP solver works (`scipy.optimize.linprog` with `method="highs"`, PuLP, a spreadsheet solver).
5. **Apply it.** `ApplyDispatch(x)` → 0 alarms, efficiency **87.50 %**, and flag I. A player who clears the alarm by hand without re-optimizing gets "dispatch is safe but below the model's optimum" instead. That line appears only when there are no alarms and no flag I, and it never says where or by how much.

**How players find the flipped floor** (three independent routes): the report names `life_support` as short 15.94 MW, which implies an 18 MW floor; life support is the only `LE` among the 17 `FloorSense` values; and the brief's spec table says ≥ 18.

The 87.50 % (rather than 100 %) is the handoff into Shadow Price: Dead Weight.

## Why it isn't trivially solvable

- The flag needs the *optimum* of the corrected model (within 0.2 %), not just any feasible dispatch. Putting every load at its floor with life support at 18 clears the alarm but only reaches 48.6 %, so no flag.
- The model is read-only (anonymous writes get `BadUserAccessDenied`), and there's no optimize method, so the controller can't solve it for you.
- Full shortcut audit: vault note *Shadow Price*, section "Shortcut audit". Machine checks: `src/shadow_price_lp.py` (28 design checks) and `src/test_server.py` (37 end-to-end checks against a live server, including the `dist/pmc7.py` helper and a leak scan of it) and `src/blackbox_check.py` (generic optimizers on the report feedback reach neither flag).

## Player helper (`dist/pmc7.py`)

Plumbing only: `connect`, `tree`, `kids`, `val`, `model` (the whole model as dicts) and `apply` (takes a dict {load: MW} or a list in `LoadOrder` order). It removes the OPC UA friction (browse paths, method argument order, float conversion) so the challenge tests the LP. It never compares the model with the spec, builds the LP, or reads shadow prices. `test_server.py` checks it works and scans it for flags and solve hints.

## Deployment

- One shared server for both challenges: `./deploy.sh` (Docker), `./deploy.sh down`, or `./deploy.sh local` (no Docker; uses uv). `deploy.sh` takes each flag from `FLAG_I`/`FLAG_II` if set, otherwise from that challenge's own `challenge.yml`, so the server can't drift from CTFd. Brownout-only review (Dead Weight not checked out): `FLAG_II=unused ./deploy.sh local`.
- `ApplyDispatch` is stateless: results come back as method outputs only, so teams can't see each other's solves. No per-team instances needed.
- Behind Docker NAT the server advertises the endpoint URL the client connected to (checked on CT 300).
- Server log: one INFO line per `ApplyDispatch` call, with efficiency and the flags awarded. Use it to confirm real solves.

## Verification record

- 2026-09-22, MacBook, `./deploy.sh local` with the real flags: `solve.py` recovered both flags exactly as in the two `challenge.yml` files. `test_server.py` 24/24 (after the NodeId and application-URI polish), `shadow_price_lp.py` 28/28.
- 2026-09-22, CT 300 `ctf-build`, Docker image built from `b4fe0a5` (with test flags): `solve.py` over the LAN recovered both, `test_server.py` 23/23.
