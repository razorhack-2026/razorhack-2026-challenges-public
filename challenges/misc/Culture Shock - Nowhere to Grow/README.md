# Culture Shock - Nowhere to Grow

**Category:** Misc
**Difficulty:** Medium
**Author:** Lt. Niko Copernicus

## Description (what the competitor will see)

By analyzing the growth behavior of the seed colony you submitted, the biologists were able to measure the average rate at which it will grow. Unfortunately, simulations using this average rate have shown that the colony will soon grow out of containment! Luckily, the Keeper of Tomorrow is stocked with an emergency supply of a substance called SCP-9516. Experimentation has shown that any organic matter that comes into contact with SCP-9516 will immediately be relocated to an unknown location in the universe. You need to use this substance to prevent the exobacteria colony from breaching containment by removing cells such that no living cells are found in a 2-cell margin from the grid border for 20 generations. We have 16 doses of SCP-9516 on the ship and each dose can only remove 1 cell, so choose carefully... The fate of the ship may be at stake!

## Files provided

- `colony.txt` - the starting colony (34×34)

## Connecting

The board editor and the submission service are served together at `http://<host>:40818`. Import `colony.txt`, remove cells, then press **Submit**. The given colony is rendered underneath for reference, and the service reports the first generation that breaches containment.

