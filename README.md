# RazorHack 2026 challenges

RazorHack 2026 was the University of Arkansas capture-the-flag competition hosted by the Ozark IEEE
Computer Society and the CyberHogs Cybersecurity Club, held in person on November 6-8, 2026. This
repository holds every challenge from the event with its source, handouts, flags and solutions.

**Story.** In 2074 the cargo ship KEEPER OF TOMORROW (KOT) carries terraforming technology to the
planet Novare, powered by the new energy source Kalium, when the lost probe ship ICARUS returns,
hostile, and the crew has to fight its sabotage system by system. The lore entries in
`challenges/lore/` tell the story in order.

**Categories:** AI, Cryptography, Forensics, ICS, Lore, Misc, OSINT, Pwn, Reverse Engineering, Steganography, VR Control Room, Web, Wi-Fi.

## Layout

Each challenge lives in `challenges/<category>/<name>/`:

- `README.md`: what players saw (description, files, connection info).
- `challenge.yml`: CTFd metadata (name, category, description, flags, files, hints). Multi-part
  challenges keep one file per part in `metadata/`.
- `dist/`: the handout files players downloaded.
- `src/` or `deploy/`: source and build files for anything that ran as a service.
- `solution/`: write-ups and solve scripts. Flags are in `challenge.yml` and the solutions, so read
  them only when you want the answers.

`infra/ai-stack/` runs a local LLM server for the AI challenges. `challenge.yml.example` documents
the metadata format.

## Challenges

179 entries (multi-part challenges list one row per part). "Needs Docker" means the challenge
was a live service; "No" means the files in `dist/` are all you need.

| Challenge | Category | Author | Folder | Needs Docker |
|---|---|---|---|---|
| Chain of Command | AI | Andy Roid | `challenges/ai/chain-of-command` | Yes + LLM endpoint |
| Echo Chamber | AI | Andy Roid | `challenges/ai/echo-chamber` | Yes (FLAG env) |
| Loose Lips | AI | Andy Roid | `challenges/ai/loose-lips` | Yes + LLM endpoint |
| Overprivileged Relay | AI | Andy Roid | `challenges/ai/overprivileged-relay` | Yes + LLM endpoint |
| Poisoned Telemetry | AI | Andy Roid & Voyager 2 | `challenges/ai/poisoned-telemetry` | Yes + LLM endpoint |
| Droning On | Cryptography | Lt. Niko Copernicus | `challenges/cryptography/Droning-On` | No |
| Employee of the Year - Kalium Collector | Cryptography | WALL-D | `challenges/cryptography/Employee-of-the-Year` | Yes (THE-DRILL in Remote-Mining) |
| Extended Authority | Cryptography | Lt. Rico Kopernicus | `challenges/cryptography/Extended-Authority` | Yes |
| High Value Deposit | Cryptography | WALL-D | `challenges/cryptography/High-Value-Deposit` | Yes (THE-DRILL in Remote-Mining) |
| Power-Trip | Cryptography | Voyager 2 | `challenges/cryptography/Power-Trip` | Yes |
| Remote Mining | Cryptography | WALL-D | `challenges/cryptography/Remote-Mining` | Yes |
| Report2074 | Cryptography | Davie Bowman | `challenges/cryptography/Report2074` | No |
| Ticket #1024 | Cryptography | Lt. Niko Copernicus | `challenges/cryptography/Ticket-1024` | Yes |
| Too Many Astronauts in the Station | Cryptography | Lt. Niko Copernicus | `challenges/cryptography/Too-Many-Astronauts` | No (in person only) |
| Wear Your Sunscreen | Cryptography | Lt. Niko Copernicus | `challenges/cryptography/Wear-Your-Sunscreen` | No |
| Are We There Yet? | Cryptography | Lt. Niko Copernicus | `challenges/cryptography/are-we-there-yet` | No |
| Course Correction | Cryptography | Lt. Niko Copernicus | `challenges/cryptography/course-correction` | No |
| Now We're Talking | Cryptography | Davie Bowman | `challenges/cryptography/nowweretalking` | No |
| Recalculating... Make a U-Turn | Cryptography | Lt. Niko Copernicus | `challenges/cryptography/recalculating-make-a-u-turn` | No |
| This broke again... | Cryptography | Tyrian Sol | `challenges/cryptography/shld` | No |
| Backtrace | Forensics | Voyager 1 | `challenges/forensics/Backtrace` | No |
| Dead Key | Forensics | Voyager 1 | `challenges/forensics/Dead_Key` | No |
| Adversarial Memory | Forensics | Andy Roid | `challenges/forensics/adversarial-memory` | Yes (FLAG env) |
| always use a VCS kids | Forensics | Grace | `challenges/forensics/always-use-a-VCS-kids` | No |
| Black Box Recovery | Forensics | Jebediah Kerman | `challenges/forensics/black-box-recovery` | No |
| Cargo Bay Forensics | Forensics | Murphy "Murph" Hall | `challenges/forensics/cargo_bay_forensics` | Yes |
| Can you hear me? | Forensics | Tyrian Sol | `challenges/forensics/comm` | No |
| Looking for a handout | Forensics | Tyrian Sol | `challenges/forensics/dock` | Yes |
| First Boot | Forensics | Andy Roid | `challenges/forensics/first-boot` | No |
| Ghost in the Cron | Forensics | Andy Roid | `challenges/forensics/ghost-in-the-cron` | No |
| hey edward where r my keys | Forensics | Grace | `challenges/forensics/hey-edward-where-r-my-keys` | Yes |
| Houston, We Have a Problem | Forensics | Jebediah Kerman | `challenges/forensics/houston-we-have-a-problem` | No |
| Light Curve | Forensics | Jebediah Kerman | `challenges/forensics/light-curve` | No |
| Many Masks | Forensics | Jebediah Kerman | `challenges/forensics/many-masks` | No |
| Name Resolution | Forensics | Andy Roid | `challenges/forensics/name-resolution` | No |
| Prompt Autopsy | Forensics | Andy Roid | `challenges/forensics/prompt-autopsy` | No |
| Proof of Life | Forensics | Andy Roid | `challenges/forensics/proof-of-life` | Yes (FLAG env) |
| Pulsar Dropbox | Forensics | Jebediah Kerman | `challenges/forensics/pulsar-dropbox` | No |
| Tool Call Trail | Forensics | Andy Roid | `challenges/forensics/tool-call-trail` | No (compose only regenerates the handout) |
| Black Box | Forensics | Lt. Rico Kopernicus | `challenges/wifi/metadata/challenge5.yml` | Yes + Linux VM with mac80211_hwsim |
| The Heap Never Let Go | Forensics | Lt. Rico Kopernicus | `challenges/wifi/metadata/challenge6.yml` | Yes + Linux VM with mac80211_hwsim |
| The Logs Never Forget | Forensics | Lt. Rico Kopernicus | `challenges/wifi/metadata/challenge3.yml` | Yes + Linux VM with mac80211_hwsim |
| Trust the Owner, Not the Caller | Forensics | Lt. Rico Kopernicus | `challenges/wifi/metadata/challenge4.yml` | Yes + Linux VM with mac80211_hwsim |
| Constellation | ICS | Voyager 1 | `challenges/ics/Constellation` | Yes |
| Containment Breach | ICS | Voyager 1 | `challenges/ics/Containment_Breach` | Yes |
| Ghost Command | ICS | Voyager 1 | `challenges/ics/Ghost_Command` | Yes |
| Last Mile | ICS | Voyager 1 | `challenges/ics/Last_Mile` | Yes (Lateral_Drift stack) |
| Lateral Drift | ICS | Voyager 1 | `challenges/ics/Lateral_Drift` | Yes |
| Silent Directive | ICS | Andy Roid | `challenges/ics/Silent-Directive` | No |
| These Things Still Run On Modbus | ICS | Voyager 1 | `challenges/ics/These_Things_Still_Run_On_Modbus` | Yes |
| Another Flashing Light | ICS | Murphy "Murph" Hall | `challenges/ics/another_flashing_light` | Yes |
| Door Stuck | ICS | Murphy "Murph" Hall | `challenges/ics/door_stuck` | Yes |
| ECLSS 1: Hailing frequencies | ICS | Definitely Not Dr. Rootkit | `challenges/ics/eclss/metadata/eclss-1.yml` | Yes (build first, src/README.md) |
| ECLSS 2: The ghost deck | ICS | Definitely Not Dr. Rootkit | `challenges/ics/eclss/metadata/eclss-2.yml` | Yes (build first, src/README.md) |
| ECLSS 3: Breathe easy | ICS | Definitely Not Dr. Rootkit | `challenges/ics/eclss/metadata/eclss-3.yml` | Yes (build first, src/README.md) |
| ECLSS 4: Scrub it out | ICS | Definitely Not Dr. Rootkit | `challenges/ics/eclss/metadata/eclss-4.yml` | Yes (build first, src/README.md) |
| ECLSS 5: Goldilocks | ICS | Definitely Not Dr. Rootkit | `challenges/ics/eclss/metadata/eclss-5.yml` | Yes (build first, src/README.md) |
| ECLSS 6: Exorcise the maintenance sync | ICS | Definitely Not Dr. Rootkit | `challenges/ics/eclss/metadata/eclss-6.yml` | Yes (build first, src/README.md) |
| ECLSS 7: All systems nominal | ICS | Definitely Not Dr. Rootkit | `challenges/ics/eclss/metadata/eclss-7.yml` | Yes (build first, src/README.md) |
| Training Bay IG1: Who Are You? | ICS | Definitely Not Dr. Rootkit | `challenges/ics/eclss/metadata/training-ig1.yml` | Yes (build first, src/README.md) |
| Training Bay IG2: Hidden in Plain Sight | ICS | Definitely Not Dr. Rootkit | `challenges/ics/eclss/metadata/training-ig2.yml` | Yes (build first, src/README.md) |
| Training Bay IG3: Tune the Beacon | ICS | Definitely Not Dr. Rootkit | `challenges/ics/eclss/metadata/training-ig3.yml` | Yes (build first, src/README.md) |
| Training Bay MB1: Roll Call | ICS | Definitely Not Dr. Rootkit | `challenges/ics/eclss/metadata/training-mb1.yml` | Yes (build first, src/README.md) |
| Training Bay MB2: Long Read | ICS | Definitely Not Dr. Rootkit | `challenges/ics/eclss/metadata/training-mb2.yml` | Yes (build first, src/README.md) |
| Training Bay MB3: The Vendor Manual | ICS | Definitely Not Dr. Rootkit | `challenges/ics/eclss/metadata/training-mb3.yml` | Yes (build first, src/README.md) |
| Training Bay MB4: Light the Beacon | ICS | Definitely Not Dr. Rootkit | `challenges/ics/eclss/metadata/training-mb4.yml` | Yes (build first, src/README.md) |
| Training Bay MB5: Big Number | ICS | Definitely Not Dr. Rootkit | `challenges/ics/eclss/metadata/training-mb5.yml` | Yes (build first, src/README.md) |
| Training Bay MB6: Floating Point | ICS | Definitely Not Dr. Rootkit | `challenges/ics/eclss/metadata/training-mb6.yml` | Yes (build first, src/README.md) |
| Training Bay MB7: Breaker Panel | ICS | Definitely Not Dr. Rootkit | `challenges/ics/eclss/metadata/training-mb7.yml` | Yes (build first, src/README.md) |
| Training Bay PL1: Airlock Cycle | ICS | Definitely Not Dr. Rootkit | `challenges/ics/eclss/metadata/training-pl1.yml` | Yes (build first, src/README.md) |
| Training Bay PL2: Hold to Confirm | ICS | Definitely Not Dr. Rootkit | `challenges/ics/eclss/metadata/training-pl2.yml` | Yes (build first, src/README.md) |
| Training Bay PL3: Count the Pulses | ICS | Definitely Not Dr. Rootkit | `challenges/ics/eclss/metadata/training-pl3.yml` | Yes (build first, src/README.md) |
| Training Bay PL4: Motor Starter | ICS | Definitely Not Dr. Rootkit | `challenges/ics/eclss/metadata/training-pl4.yml` | Yes (build first, src/README.md) |
| Training Bay PL5: Four to Twenty | ICS | Definitely Not Dr. Rootkit | `challenges/ics/eclss/metadata/training-pl5.yml` | Yes (build first, src/README.md) |
| Got That On Tape | ICS | Murphy "Murph" Hall | `challenges/ics/got_that_on_tape` | Yes |
| Off-Sun | ICS | Jebediah Kerman | `challenges/ics/off-sun` | No |
| Shadow Price: Brownout | ICS | Andy Roid | `challenges/ics/shadow-price-brownout` | Yes (FLAG env) |
| Shadow Price: Dead Weight | ICS | Andy Roid | `challenges/ics/shadow-price-dead-weight` | Yes (shadow-price-brownout stack) |
| Under Pressure | ICS | Murphy "Murph" Hall | `challenges/ics/under_pressure` | Yes |
| Who Turned The Lights Off | ICS | Murphy "Murph" Hall | `challenges/ics/who_turned_the_lights_off` | Yes |
| Coremelt: Core | ICS | Andy Roid | `challenges/web/coremelt/metadata/challenge4.yml` | Yes |
| Log 00: Mission Background | Lore | Voyager 2 | `challenges/lore/Log-00-Mission-Background` | No |
| Log 01: Welcome Aboard | Lore | Voyager 2 | `challenges/lore/Log-01-Welcome-Aboard` | No |
| Log 02: Anomalies Detected | Lore | Voyager 2 | `challenges/lore/Log-02-Anomalies-Detected` | No |
| Log 03: Out of Control | Lore | Voyager 2 | `challenges/lore/Log-03-Out-of-Control` | No |
| Blind Pilot | Misc | Tyrian Sol | `challenges/misc/Blind-Pilot` | Yes |
| Consensus-Drift | Misc | Voyager 2 | `challenges/misc/Consensus-Drift` | Yes (FLAG env) |
| Cosmic Calibration | Misc | WALL-D | `challenges/misc/Cosmic-Calibration` | Yes |
| Culture Shock: Adapt or Die | Misc | Lt. Niko Copernicus | `challenges/misc/Culture Shock - Adapt or Die` | Yes |
| Culture Shock - Nowhere to Grow | Misc | Lt. Niko Copernicus | `challenges/misc/Culture Shock - Nowhere to Grow` | Yes |
| Culture Shock - Patient Zero | Misc | Lt. Niko Copernicus | `challenges/misc/Culture Shock - Patient Zero` | Yes |
| Lockpicking Station | Misc | Davie Bowman | `challenges/misc/Lockpicking Station` | No |
| Singularity Upset | Misc | Lt. Niko Copernicus | `challenges/misc/Singularity-Upset` | No |
| VisionTest 20/20 | Misc | Tyrian Sol | `challenges/misc/VisionTest-20-20` | No |
| Who's That Protocol #1 | Misc | Davie Bowman | `challenges/misc/WTP #1` | No |
| Who's That Protocol #10 | Misc | Jebediah Kerman | `challenges/misc/WTP #10` | No |
| Who's That Protocol #2 | Misc | Davie Bowman | `challenges/misc/WTP #2` | No |
| Who's That Protocol #3 | Misc | Davie Bowman | `challenges/misc/WTP #3` | No |
| Who's That Protocol #4 | Misc | Davie Bowman | `challenges/misc/WTP #4` | No |
| Who's That Protocol #5 | Misc | Davie Bowman | `challenges/misc/WTP #5` | No |
| Who's That Protocol #6 | Misc | Davie Bowman | `challenges/misc/WTP #6` | No |
| Who's That Protocol #7 | Misc | Jebediah Kerman | `challenges/misc/WTP #7` | No |
| Who's That Protocol #8 | Misc | Jebediah Kerman | `challenges/misc/WTP #8` | No |
| Who's That Protocol #9 | Misc | Jebediah Kerman | `challenges/misc/WTP #9` | No |
| WaveCode 1 | Misc | Lt. Niko Copernicus | `challenges/misc/WaveCode-1` | No |
| WaveCode 2 | Misc | Lt. Niko Copernicus | `challenges/misc/WaveCode-2` | No |
| WaveCode 3 | Misc | Lt. Niko Copernicus | `challenges/misc/WaveCode-3` | No |
| Wanna Play A Game? | Misc | Tyrian Sol | `challenges/misc/core` | Yes |
| Minor Calculations | Misc | Tyrian Sol | `challenges/misc/life` | Yes |
| Wrong Direction | Misc | Tyrian Sol | `challenges/misc/nav` | No |
| Soldering Station | Misc | Davie Bowman | `challenges/misc/soldering station` | No |
| Know Your Mark | OSINT | Voyager 1 | `challenges/osint/Know_Your_Mark` | Yes |
| Blind Spot | Pwn | Voyager 1 | `challenges/pwn/Blind_Spot` | Yes |
| Rubber Stamp | Pwn | Lt. Rico Kopernicus | `challenges/pwn/Rubber-Stamp` | Yes |
| Hangman | Pwn | Grace | `challenges/pwn/hangman` | Yes |
| Jam Session | Pwn | Lt. Rico Kopernicus | `challenges/pwn/mcpjam/metadata/challenge1.yml` | Yes |
| Rollback | Pwn | Lt. Rico Kopernicus | `challenges/pwn/mcpjam/metadata/challenge2.yml` | Yes |
| Overburden | Pwn | Andy Roid | `challenges/pwn/overburden` | Yes (deploy/Dockerfile) |
| Overburden: Master Loop | Pwn | Andy Roid | `challenges/pwn/overburden-boss` | Yes (FLAG env) |
| Breaching the Core | Pwn | Lt. Rico Kopernicus | `challenges/wifi/metadata/challenge7.yml` | Yes + Linux VM with mac80211_hwsim |
| Swarm Key Shuffle | Reverse Engineering | Lt. Niko Copernicus | `challenges/cryptography/Swarm-Key-Shuffle` | Yes |
| Brailliant Minds | Reverse Engineering | Mort | `challenges/rev/BrailliantMinds` | No |
| R.U.B.I.K (Rocket Universal Bi-Axis Initial (K)alibration) | Reverse Engineering | WALL-D | `challenges/rev/RUBIK` | No (compose only rebuilds the handout) |
| XenoInstructions #1 | Reverse Engineering | Mort | `challenges/rev/XenoInstructions_1` | No |
| XenoInstructions #2 | Reverse Engineering | Mort | `challenges/rev/XenoInstructions_2` | No |
| XenoInstructions #3 | Reverse Engineering | Mort | `challenges/rev/XenoInstructions_3` | No |
| Crew Companion | Reverse Engineering | Andy Roid | `challenges/rev/crew-companion` | No |
| Encrypted Telemetry | Reverse Engineering | Andy Roid | `challenges/rev/encrypted-telemetry` | No |
| Enki's Tongue | Reverse Engineering | Andy Roid | `challenges/rev/enkis-tongue` | No |
| Field Diagnostic | Reverse Engineering | Andy Roid | `challenges/rev/field-diagnostic` | No |
| Flat Field | Reverse Engineering | Jebediah Kerman | `challenges/rev/flat-field` | No |
| Fried Readout | Reverse Engineering | Andy Roid | `challenges/rev/fried-readout` | No |
| Glossolalia | Reverse Engineering | Andy Roid | `challenges/rev/glossolalia` | No |
| Grace's SHA256 Hash Collision Project | Reverse Engineering | Grace | `challenges/rev/graces-sha256-hash-collision-project` | Yes |
| Hacking to the Binary I | Reverse Engineering | Grace | `challenges/rev/hacking-to-the-binary-i` | No |
| Hull Breach | Reverse Engineering | Andy Roid | `challenges/rev/hull-breach` | No |
| See You Space Cowboy | Reverse Engineering | Grace | `challenges/rev/see-you-space-cowboy` | No |
| Shifting Memory | Reverse Engineering | Andy Roid | `challenges/rev/shifting-memory` | No |
| Captain, we stopped | Reverse Engineering | Tyrian Sol | `challenges/rev/thrust` | No |
| 1 2 3 FOUR | Steganography | Mort | `challenges/sheet_music/123FOUR` | No |
| Directional Slopes | Steganography | Mort | `challenges/sheet_music/DirectionalSlopes` | No |
| Home Cweet Home 1 | Steganography | Mort | `challenges/sheet_music/HomeCweetHome1` | No |
| Home Cweet Home 2 | Steganography | Mort | `challenges/sheet_music/HomeCweetHome2` | No |
| Itty Bitty Differences | Steganography | Mort | `challenges/sheet_music/IttyBittyDifferences` | No |
| Learn Your 7 (or 12) ABCs #1 - Tutorial | Steganography | Mort | `challenges/sheet_music/LearnYour7(or12)ABCs_1` | No |
| Learn Your 7 (or 12) ABCs #2 - Shared Motif | Steganography | Mort | `challenges/sheet_music/LrnUrABCs_2-SharedMotif` | No |
| As Expected | Steganography | Voyager 1 | `challenges/stego/As_Expected` | No |
| Conditionally Visible | Steganography | Mort | `challenges/stego/ConditionallyVisible` | No |
| Expression of Regularity | Steganography | Mort | `challenges/stego/ExpressionOfRegularity` | No |
| Nothing to Report | Steganography | Voyager 1 | `challenges/stego/Nothing_to_Report` | No |
| Office Gossip | Steganography | Davie Bowman | `challenges/stego/Office_Gossip` | No |
| Where's Charles? | Steganography | Murphy "Murph" Hall | `challenges/stego/wheres_charles` | Yes |
| Out of Touch and Out of Time by Hall & Oats | VR Control Room | Murphy "Murph" Hall & Darryl Oats | `challenges/vr-control-room/hall-and-oats` | No |
| Deep Rooted Tissue | Web | Tyrian Sol | `challenges/web/3d-outlier` | Yes |
| Five By Five | Web | Voyager 1 | `challenges/web/Five_By_Five` | Yes |
| Keyboard Warrior | Web | Tyrian Sol | `challenges/web/Keyboard-Warrior` | Yes |
| Moonwalk | Web | Tyrian Sol | `challenges/web/Moonwalk` | Yes |
| One Key Fits All | Web | Voyager 1 | `challenges/web/One_Key_Fits_All` | Yes |
| Poisoned Cache | Web | Lt. Rico Kopernicus | `challenges/web/Poisoned-Cache` | Yes |
| Spill the Beans | Web | Lt. Rico Kopernicus | `challenges/web/Spill-the-Beans` | Yes |
| Zero-G Salvage | Web | Lt. Rico Kopernicus | `challenges/web/Zero-G-Salvage` | Yes |
| Zero Eccentricity | Web | Voyager 1 | `challenges/web/Zero_Eccentricity` | Yes |
| Coremelt: Deeper In | Web | Andy Roid | `challenges/web/coremelt/metadata/challenge3.yml` | Yes |
| Coremelt: Foothold | Web | Andy Roid | `challenges/web/coremelt/metadata/challenge1.yml` | Yes |
| Coremelt: Keys to the Kingdom | Web | Andy Roid | `challenges/web/coremelt/metadata/challenge2.yml` | Yes |
| Cryopod | Web | Tyrian Sol | `challenges/web/cryopod` | Yes (FLAG env) |
| The Gjallarhorn | Web | Lt. Rico Kopernicus | `challenges/web/gjallarhorn` | Yes |
| Odd Man Out | Web | Tyrian Sol | `challenges/web/odd-pixel` | Yes (FLAG env) |
| Reactor Access | Web | Tyrian Sol | `challenges/web/pwr` | Yes |
| Access Elevation | Web | WALL-D | `challenges/web/rasa-kiosk/metadata/challenge2.yml` | Yes |
| Getting Checked In | Web | WALL-D | `challenges/web/rasa-kiosk/metadata/challenge1.yml` | Yes |
| Uplink Login | Web | Murphy "Murph" Hall | `challenges/web/uplink_login` | Yes |
| Behind Enemy Lines | Wi-Fi | Lt. Rico Kopernicus | `challenges/wifi/metadata/challenge1.yml` | Yes + Linux VM with mac80211_hwsim |
| Breaking and Entering | Wi-Fi | Lt. Rico Kopernicus | `challenges/wifi/metadata/challenge2.yml` | Yes + Linux VM with mac80211_hwsim |
| Mailbox Shenanigans | Wi-Fi | Lt. Rico Kopernicus | `challenges/wifi/metadata/training2.yml` | Yes + Linux VM with mac80211_hwsim |
| RazorVault | Wi-Fi | Lt. Rico Kopernicus | `challenges/wifi/metadata/challenge9.yml` | Yes + Linux VM with mac80211_hwsim |
| Something in the Static | Wi-Fi | Lt. Rico Kopernicus | `challenges/wifi/metadata/challenge8.yml` | Yes + Linux VM with mac80211_hwsim |
| Systems Check | Wi-Fi | Lt. Rico Kopernicus | `challenges/wifi/metadata/training1.yml` | Yes + Linux VM with mac80211_hwsim |
| Yo, those are my packets, bro… | Wi-Fi | Lt. Rico Kopernicus | `challenges/wifi/metadata/training3.yml` | Yes + Linux VM with mac80211_hwsim |

## Running challenges locally

You need Docker with Compose v2. At the event, each team got its own copy of each service in the
cloud; locally, use `localhost` for `{host}` and the published port from the challenge's
`docker-compose.yml` for `{port}`.

```sh
cd challenges/web/Keyboard-Warrior
docker compose up -d --build
# play, then clean up:
docker compose down -v --rmi local
```

Challenges that need extra setup:

- **FLAG in the environment.** Some compose files refuse to start until you set `FLAG` (the value
  is in that challenge's `challenge.yml`): ai/echo-chamber, ai/poisoned-telemetry,
  forensics/adversarial-memory, forensics/proof-of-life, forensics/tool-call-trail (src),
  ics/shadow-price-brownout (`FLAG_I`, `FLAG_II`), misc/Consensus-Drift, pwn/overburden-boss,
  web/cryopod, web/odd-pixel. Several folders include a `run.sh` or `deploy.sh` that reads it for
  you.
- **AI challenges** (chain-of-command, loose-lips, overprivileged-relay, poisoned-telemetry) need an
  OpenAI-compatible model endpoint. The easiest is Ollama: `ollama pull qwen3:8b`, then set
  `LLM_BASE_URL=http://host.docker.internal:11434/v1`, `LLM_MODEL=qwen3:8b` and
  `LLM_BACKEND=ollama`. `infra/ai-stack/` runs all four against one vLLM server on a GPU
  (`docker compose -f docker-compose.yml -f model.yml up -d`; see the comments in those files, and
  run `init_flags.sh` first). The event used Qwen3-30B-A3B; a smaller model changes how hard
  they are. ai/echo-chamber runs on CPU (`setup.sh` / `setup.ps1`).
- **THE-DRILL** (cryptography/Remote-Mining, High-Value-Deposit, Employee-of-the-Year): run
  `docker compose up -d --build` in `challenges/cryptography/Remote-Mining`, then
  `ssh -p 2222 'TEAM#01@localhost'`. The accounts in `THE-DRILL/teams.txt` are placeholders; see
  `THE-DRILL/DEPLOYMENT.md`.
- **ECLSS** (ics/eclss, 22 parts): build with `docker compose run --rm builder` in
  `challenges/ics/eclss/src`, then follow `src/README.md`. Ignition runs in trial mode (it resets
  every 2 hours).
- **Last Mile** is played through the ics/Lateral_Drift stack (its `process-plc` service is the
  Modbus target). **Shadow Price: Dead Weight** uses the ics/shadow-price-brownout server.
- **Overburden** builds from `deploy/` (see `deploy/README.md`).
- **Wi-Fi** (`challenges/wifi`) needs a Linux VM (Debian or Kali) that can load the
  `mac80211_hwsim` kernel module: `./ctf install`, then `./ctf start` (see its README). Most cloud
  VMs can't load that module. Change the player SSH password in `build/Dockerfile` first.
- **Too Many Astronauts**, the lockpicking and soldering stations, the VR control room and some
  misc challenges were in-person activities; they are here for reference.

Some services are intentionally vulnerable (several give players remote code execution). Run them
only on a machine you control, and don't expose their ports to the internet.

## Issues and forks

This repository is archived (read-only), so GitHub issues and pull requests are closed. Forks
are welcome.

## Licence

MIT. See [LICENSE](LICENSE).

## Credits

Challenges by the RazorHack 2026 Gamemasters (credited by their in-story names in each
`challenge.yml`). Thanks to every team that played.
