# Training Bay - basic Modbus / OpenPLC / Ignition warm-ups

Fifteen short challenges (1000 points) that teach the skills the ECLSS
challenge assumes. They run on their own OpenPLC runtime so warm-up traffic
never touches the ship.

| Track | Challenges | Teaches |
|-------|-----------|---------|
| Modbus | MB1-MB7 | reads, ASCII unpacking, Modicon addressing, coils, 32-bit words, floats, read-modify-write |
| OpenPLC | PL1-PL5 | reading interlocks, TON timers, edges vs levels & scan time, seal-in with NC contacts, 4-20 mA scaling |
| Ignition | IG1-IG3 | gateway fingerprinting, client-side hiding, HMI writes driving the PLC |

## Files

```
training/training_flags.json        secrets + flag text (edit per event)
training/plc/TRAIN_FBs.st.tmpl      one small FB per challenge (TON/CTU/R_TRIG)
training/plc/TRAIN_Main.st.tmpl     Modbus wiring + re-arm logic
training/test/test_training.st      20 STruC++ unit tests
training/tools/build_training.py    generator (run via the builder)
training/solver/solve_training.py   reference solution / health check
training/student/                   HAND THESE TO PLAYERS:
    TRAINING_GUIDE.md                 briefings
    REGISTER_MAP.md                   addresses (generated)
    TRAINING_LOGIC.st                 PLC source, secrets redacted (generated)
training/docs/HINTS.md              staff: tiered hints
training/docs/SOLUTIONS.md          staff: walkthrough, scoring, checklist
```

Give players `training/student/` plus `docs/MODBUS_PRIMER.md`.

## Run it

```bash
docker compose run --rm builder                 # builds + tests everything
docker compose up -d --build                    # training PLC on :5020, with ECLSS + Ignition
python3 ../solution/training/solve_training.py --host 127.0.0.1 --port 5020 --gateway http://127.0.0.1:8088
```

Each team gets its own copy at the event (`../../solution/README.md`). The
training PLC listens on 5020 itself, because it shares a network namespace
with the ECLSS PLC on 502.

## Verified

- All 20 function-block unit tests pass under STruC++ v0.7.0.
- The generated bundle compiles with OpenPLC Runtime v4.3.1's own
  `Makefile.strucpp`, and was provisioned onto a real v4.3.1 runtime through
  its REST API.
- On that runtime the reference solver captured all 12 Modbus/OpenPLC flags
  and the IG3 PLC lock, and the traps behaved as designed: a blind breaker
  write trips the panel, Modbus pulses faster than the 100 ms scan register
  zero counts, STOP-left-FALSE blocks the motor, naive scaling reads 53.1 %,
  the override keeps the door shut, and every challenge re-armed itself.
- 2026-11-04, on the event images: the Training HMI view and its tag
  bindings, IG1 on `/system/gwinfo`, IG2 in the DOM and IG3 through the HMI
  entry all checked in a browser (`../README.md`, "Verification status").
