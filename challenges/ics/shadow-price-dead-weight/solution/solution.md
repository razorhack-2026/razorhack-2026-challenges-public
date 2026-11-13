# Shadow Price: Dead Weight — solution (GM-only)

**Flag:** see `../challenge.yml`. **Reference solver:** `../../shadow-price-brownout/solution/solve.py` (solves both parts against the shared server). **Server and deployment:** `../../shadow-price-brownout/` (`deploy.sh`, `docker-compose.yml`, `src/`).

## Intended solve

Starts from the Brownout solution: life-support sense fixed, dispatch at 87.50 %.

1. **Get the shadow prices** from the corrected LP. With `linprog(..., method="highs")`, `res.ineqlin.marginals` are the sensitivities of the *minimized* objective. For the maximization, shadow price = `-marginal`. Keep the floors as explicit constraint rows (not variable bounds) so each floor gets its own shadow price.
2. **Answer the chief engineer's question:** which floor costs the most? For each binding aux floor, cost = shadow price × floor (by LP duality, how much objective that floor is holding down).

   | Bus | Shadow price | Floor | Cost |
   |---|---|---|---|
   | **aux_bus_7** | 4.478 | 5.5 | **24.63** |
   | aux_bus_2 | 2.450 | 6.5 | 15.93 |
   | aux_bus_11 | 2.550 | 4.0 | 10.20 |
   | aux_bus_6 | 2.500 | 3.5 | 8.75 |
   | aux_bus_10 | 4.022 | 2.0 | 8.04 |

   `aux_bus_7` is also first on shadow price alone (4.478 against 4.022). It's expensive because it sits on coolant loop B, which is saturated and shared with the shields, and each of its MW costs 1.0 MWth of that loop.
3. **Relieve it:** drop `aux_bus_7`'s floor to 0 and re-solve.
4. **Apply it.** `ApplyDispatch(x)` → efficiency **100.00 %** and flag II. The report shows `aux_bus_7 ALARM short 5.50 MW`, then the reveal: the bus's downstream device has no asset tag, so it's an unregistered load. That's `ICARUS`'s hidden mining rig; see the vault *Lost in Space Story Arc*, cryptojacking layer.

## Accepted alternative (slower, same skill)

Brute force: drop each of the 10 non-zero aux floors in turn, re-solve and apply. Only `aux_bus_7` reaches 100 %. Every wrong drop browns that bus out and awards nothing. Each try still needs a full LP solve.

## Why it isn't trivially solvable

- **No diff target:** aux buses aren't in the mission spec, and there's only one served model.
- **Camouflage:** `aux_bus_7`'s floor (5.5) isn't the largest aux floor (hydroponics is 6.5), its coolant coefficient isn't the largest, and its weight is tied for lowest.
- **Probe resistance:** the report's alarms use physical demand (the rig really draws 5.5 MW), so zeroing `aux_bus_7` alarms exactly like zeroing a legitimate bus. Flags are judged against the true model.
- **Timestamps and access levels** are uniform across all model nodes.

## Verification record

Shared with Brownout; see `../../shadow-price-brownout/solution/solution.md`.
