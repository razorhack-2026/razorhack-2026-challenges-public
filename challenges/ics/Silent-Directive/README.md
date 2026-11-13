# Silent Directive

**Category:** ICS · **Difficulty:** Medium · **Author:** Andy Roid

The extraction-control segment aboard **ICARUS** was never as quiet as its
operators thought. Dr. Rootkit slipped a "field-bus confidentiality shim"
between the engineering workstation and the extraction PLC — the value field of every setpoint write (S7comm Write Var) is re-encoded so that a passive tap sees only ciphertext, while
the PLC (which shares his key) decodes transparently.

The boarding team pulled three things off that segment:

- `extraction_bus.pcap` — a full capture off the extraction bus: mostly routine
  S7comm telemetry polling, with a handful of setpoint writes mixed in. The
  written values are the shim's ciphertext.
- `interceptor.py` — the recovered shim itself. The 16-byte director key it
  loaded at runtime is **not** in this copy.
- `workstation_console.log` — the engineering console's audit of the setpoints
  the crew believed they were pushing.

Every write on that bus lines up with a console entry — except one. Recover
what Dr. Rootkit actually told the extraction array to do.
