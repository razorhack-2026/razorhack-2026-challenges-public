# ECLSS - Spaceship Life-Support ICS Challenge (RazorHack)

> **In the razorhack-2026 repo** this folder is the author's kit (by Anon),
> run from here (`cd src`). The solvers and staff docs are in `../solution/`,
> the player handouts in `../dist/`, and the 22 CTFd challenges in
> `../metadata/`. GM notes: `../solution/README.md`.

An intentionally-vulnerable ICS capture-the-flag scenario built around a
spaceship **Environmental Control & Life Support System**: oxygen generation,
CO2 scrubbing, and cabin temperature control. The logic runs on **OpenPLC
Runtime v4** and is monitored through an **Inductive Automation Ignition**
Perspective HMI. Players reach it over **Modbus TCP** and the **Ignition web
UI**; the real control logic, including the fault that keeps undoing their
fixes, lives in the PLC.

- **Training Bay** (`training/`): 15 short warm-ups across Modbus (MB1-7),
  OpenPLC logic (PL1-5), and Ignition (IG1-3).
- **ECLSS challenge**: seven flags spanning PLC recon, an unlinked HMI page,
  three process recoveries (O2 / CO2 / temperature), disarming a
  "maintenance sync" routine found through the HMI, and a nominal-hold capstone.

> Safety: deliberately insecure (no Modbus auth, hidden maintenance pages).
> Isolated range only. Everything it models is fictional game state.

## How it runs

Each team gets its own copy: one Fargate task (`instance:eclss`, Razorhack-Infra
`lib/challenges.json`) of three images that share one network namespace.

| Image | Listens on | What's baked in |
|-------|-----------|-----------------|
| `images/plc-eclss` | Modbus 502 | OpenPLC v4.3.1 with the ECLSS program compiled and set to run |
| `images/plc-train` | Modbus 5020 | OpenPLC v4.3.1 with the Training Bay program compiled and set to run |
| `images/ignition` | HTTP 8088 | Ignition 8.3.9 with both Perspective projects, both Modbus devices (`127.0.0.1`) and every tag |

- **Ready in under a minute after the images are pulled.** Each PLC answers in
  about 3 s, and the gateway reaches RUNNING in about 40 s on 1 vCPU. There is
  no upload, compile, Designer or Script Console step at start.
- **Nothing internal is reachable.** Every port in the task is reachable from
  the team's Kali box, so each runtime's REST API (which can download the
  running program, flags and all) listens on `127.0.0.1` only (8443 / 8444),
  and the OpenPLC LAN discovery responder is off (`images/plc/bake.sh`).
- **The Ignition gateway is unlicensed** (2-hour trial). `images/ignition/rh-entrypoint.sh`
  sets a random admin password per copy and resets the trial whenever it
  expires.
- **The gateway config is files.** Ignition 8.3 keeps devices and tags under
  `data/config/resources/`. `tools/ignition_config.py` writes them to
  `ignition/config/`, and the image copies that into the `external` collection
  (a fresh gateway refuses to start if `core/` already exists).

`docker-compose.yml` runs the same three images the same way for local testing.

## Build and run locally

```bash
docker compose run --rm builder   # rebuild programs + HMI + gateway config, run all PLC unit tests
docker compose up -d --build      # ECLSS :502, Training :5020, Ignition :8088
```

The builder is only needed after changing flags or PLC/HMI source: `build/`,
`ignition/` and `training/student/` are committed. It needs internet (it
clones STruC++ and runs `npm ci`).

### Why a builder container?

OpenPLC Runtime v4 does **not** compile Structured Text on the device. It
expects the C++ that STruC++ generates, plus the STruC++ runtime headers and
a `defines.h`, exactly as the OpenPLC Editor packages them. The builder pins
STruC++ **v0.7.0** (the version the Editor ships for runtime **v4.3.1**) and
runs `tools/strucpp_bundle.mjs`, so the only host requirement is Docker.

## Layout

```
flags.json                     ECLSS secrets (disarm code, flags)
plc/src/*.st.tmpl              ECLSS plant + control + puzzle, Modbus wiring
plc/test/test_eclss.st         15 STruC++ unit tests
training/                      Training Bay (see training/README.md)
tools/build_challenge.py       ECLSS generator (program, register map, tags, HMI views)
tools/ignition_config.py       Ignition 8.3 config resources: devices + tags
tools/strucpp_bundle.mjs       ST -> OpenPLC v4 upload bundle (mirrors the Editor)
tools/bundle.py, hmi_theme.py  shared bundling helper, HMI view generator
builder/                       pinned build image (Node 22 + STruC++ v0.7.0)
build/                         generated programs (program.zip) and sources
ignition/                      projects (eclss, training), tag exports, config/
images/                        the three event images (see "How it runs")
docker-compose.yml             builder + the three images, one namespace
```

## Authoring new flags

1. Edit `flags.json` and/or `training/training_flags.json`. If you change
   `gateway_name`, change `IGN_GATEWAY_NAME` in `images/ignition/Dockerfile`
   to match (it is IG1's flag).
2. `docker compose run --rm builder`: regenerates both PLC programs, register
   maps, tag exports, the gateway config, the secret-bearing HMI views, and
   re-runs the tests.
3. Copy `training/student/*` to `../dist/training/`, and update `flags:` in
   `../metadata/*.yml`.
4. Rebuild and push the images (`../solution/README.md`).

## Verification status (2026-11-04)

Run locally on the three images with no added capabilities (as on Fargate):

- Unit tests: 15 ECLSS + 20 Training, all passing under STruC++ v0.7.0.
- A fresh copy publishes only the always-on recon flag; flags 3-7 read zero
  until earned.
- `../solution/eclss/solve.py` captured all six ECLSS Modbus flags (237 s from a
  ship left sabotaged ~5 min), and `../solution/training/solve_training.py`
  all 12 Training Modbus/OpenPLC flags plus IG1 and IG3's PLC side.
- In a browser: ECLSS 2 on `/crew-manifest`, IG2 in the DOM, IG3 after typing
  1420 into the HMI; `/maint` shows the code but not flag 6.
- Every flag matches `../metadata/*.yml`.

## Component versions

- OpenPLC Runtime `ghcr.io/autonomy-logic/openplc-runtime:v4.3.1`
- STruC++ `v0.7.0` (builder image)
- Ignition `inductiveautomation/ignition:8.3.9`
