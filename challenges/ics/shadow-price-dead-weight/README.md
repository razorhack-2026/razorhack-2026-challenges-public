# Shadow Price: Dead Weight

**Category:** ICS · **Difficulty:** easy

Life support is back, but the dispatch only reaches 87.5 % of what this plant should deliver, and the shields are paying for the difference. Somewhere in the model, a floor is holding power it has no business holding.

The auxiliary buses aren't in the mission spec. They're ship-internal loads configured on the controller, and most of their floors are real: pull the wrong one and something on the ship goes dark. The chief engineer can spare the time to walk the decks and inspect exactly one bus:

> "Find me the floor that's costing us the most, and I'll go look at it."

Find it, relieve it, and apply the dispatch that gets the ship to full efficiency.

**Connect:** `opc.tcp://<host>:4840/pmc7/`, the same live controller as Shadow Price: Brownout.

**Files:** none. The `pmc7.py` helper from Shadow Price: Brownout works here too.

Part 2 of the Shadow Price chain. Requires: Shadow Price: Brownout.
