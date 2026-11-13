# Field Diagnostic

**Category:** Reverse Engineering · **Difficulty:** Easy

Maintenance pulled the field-diagnostic utility off a console on Docking Ring 3
during the sweep. It still runs — it'll happily tell you the panel and bus are
nominal — but the **full calibration readout** is locked behind a service code,
and the tech who had the code isn't answering.

They only kept the compiled tool, not its source. Get the full readout.

## Provided

- `diagnostic.pyc` — the compiled utility (Python 3.8 bytecode).

## Flag

The full calibration readout contains a standard `flag{...}`.
