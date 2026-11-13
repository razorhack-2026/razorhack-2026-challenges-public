ICARUS COOLANT SUBSYSTEM -- ENGINEERING NOTES (RESTRICTED)
==========================================================

Maintenance override for the coolant interlock is gated in the RTU ladder
(coremelt_gate.st, PROGRAM maint_override). The interlock will not lift
without the maintenance authorization key entered at AUTH0..AUTH3.

I lost the key card again. The check is right there in the ladder -- it folds
each key word against the stored signature SIG, through the RTU SCRAMBLER and
the panel calibration constants. Work the check backwards from SIG and you can
recover the four key words, write them to the holding registers, and the panel
will unseal the maintenance payload to the readback registers.

  -- j.reyes, controls eng.
