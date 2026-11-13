# Heimdall: GM lore

Shared by the Gjallarhorn console challenge (single challenge after Wi-Fi ch8). Generated data:
`src/nodes.json` plus the public `src/ui/public/{graph,chat}.json` (re-running `src/gen_nodes.py`
must give the same files; it asserts every layout/evidence rule and retries seeds until all pass).

## Story
- Heimdall: independent AI defense network, satellites everywhere. Not a ship system.
  Wi-Fi ch8 is the discovery hook. Its telemetry log is fixed lore; only the intercom lines change.
- **Surtr is Heimdall's name for the virus.** The virus never says it. No artifact decodes to it.
  Heimdall names it openly from the intercom onward.
- **Secret origin: Dr. Rootkit.** Surtr is a virus written by Dr. Rootkit (not him, not a copy),
  the operator who forged the ABANDON SHIP directive that emptied the Icarus and later took it
  over, some time during its disappearance (Poisoned-Cache and Black Box lore; no exact year).
  He stays aboard 1C@RU5; Surtr is a tool he launched. Under him the ship is no longer the
  Icarus: its transponder reads **1C@RU5** (the malformed designation in ch8's log).
  In 2074, right before the event (Nov 6-8), Huginn detects 1C@RU5 (18:34:25), scans it (19:12:35)
  and escalates "to upstream array" (19:13:10). Surtr rode that report in via the ODINS_EYES relay
  and landed in HATI, then spread to 7 more nodes. Never spell out "Dr. Rootkit" in the console.
- Naming rule: the player's storyline says ICARUS; Heimdall and the console say 1C@RU5 for what
  came back. It is a subtle clue that the ship was taken over.
- Surtr cancels Heimdall's repairs and answers on Heimdall's channel saying all is well. Surtr
  runs in 8 nodes, but HATI's voice travels the whole mesh.
- Ragnarok / Gjallarhorn purge: needs an activation code plus a signed launch token. Heimdall
  cannot send either openly (Surtr watches its channel). The token rides in the chat frames Surtr
  cuts off. The code is sealed in Heimdall's core ledger and written in the elder script across the
  map (see "The seal in the elder script"). "I NEVER DELETE."

## Timeline
- 2074-11-05 19:13:10: Huginn escalates the Icarus findings upstream (last ch8 telemetry entry).
- Right after: first HATI relay message, `origin: 1C@RU5` with a malformed origin block.
- Nov 6-8: event days. The ch8 intercom lines are stamped at runtime, so they land here.
- All generated timestamps (chat scrollback, repairs) start at 2074-11-05 19:13:10.

## Wi-Fi ch8 intercom lines (the only editable part of ch8)
File: `challenges/wifi/content/huginn/huginn_startup.sh`, array `LOG_LINES`. No connection info;
the address goes in the CTFd listing. The flag line stays LAST.
1. `Sender = ROOT NODE (HEIMDALL)` (unchanged)
2. `GLAD YOU UNDERSTOOD MY MESSAGES.` (unchanged)
3. `I KNOW YOU ARE DEALING WITH THE ICARUS RIGHT NOW, BUT I NEED YOUR HELP.` (unchanged)
4. `THE REPORT ON 1C@RU5 WAS NOT THE ONLY THING THAT TRAVELLED UPSTREAM. SOMETHING RODE IT INTO MY NETWORK.`
5. `I CALL IT SURTR. IT IS IN HATI AND IT HAS SPREAD. IT CANCELS EVERY REPAIR I ISSUE.`
6. `MY VOICE IS BEING CUT AT THE SOURCE. SURTR ANSWERS FOR ME ON MY OWN CHANNEL AND SAYS ALL IS WELL.`
7. `YOU CLOSED ODINS_EYES. SURTR LOST ITS VIEW OF THIS LINK. I HAVE OPENED A SEPARATE CHANNEL TO YOU.`
8. `BELIEVE THE SIGNATURES, NOT THE VOICES.`
9. `LISTEN.` (unchanged)
10. the ch8 flag line (unchanged, LAST)
Each line is prefixed `INTERCOM_MESSAGE: ` in the script.

## The chat (console)
- Two voices: HEIMDALL (cyan, uppercase, urgent, signs everything) and HATI (amber/red, calm,
  uppercase, mimics Heimdall, says all is well, cancels repairs, cuts Heimdall off).
  HATI's label is never "Surtr".
- Evidence lives in each message's frame: `sig`, `expectedSig`, `origin`, `hops`, `trace`, `note`,
  `raw` (what Heimdall actually sent before the relay overwrote it).
- A few HATI messages are shown under the label `H13MD411` in Heimdall's cyan; their signatures
  do not match Heimdall's.

## Network
- 400 nodes in 8 regions (50 each: 15 relay/rune stars + 35 sea nodes): ASGR, MIDG, VANA, ALFH, JOTN, NIDV, NIFL, HELH (15 each; JOTN is
  14 plus HATI). Ids are `<REGION>-NN`, plus `HATI`. Mesh links in `src/nodes.json` (`links`).
- **Realms** (region code → full name, shown on hover over the map label):

  | Code | Realm |
  |---|---|
  | ASGR | Asgard |
  | MIDG | Midgard |
  | VANA | Vanaheim |
  | ALFH | Alfheim |
  | JOTN | Jotunheim |
  | NIDV | Nidavellir |
  | NIFL | Niflheim |
  | HELH | Helheim |
- **ODINS_EYES, HUGINN and MUNINN** are three of the 120 (renamed by the generator, deterministic
  from the seed). They must be excluded from the cluster BFS, outliers and superset.
  - ODINS_EYES: the relay. Shown DISABLED (the player closed it in ch8), panel reads
    `OVERRIDE ACCEPTED`, no repair queue, a mesh neighbour of HATI (Surtr's doorway). Not infected.
  - HUGINN and MUNINN: both linked only to ODINS_EYES, clean, shown severed, not in the superset.
    Heimdall calls them "my eyes" in the chat. Selecting either makes the set wrong.
- Each region is drawn on the map as one elder futhark rune: its stars lie on the rune's strokes
  (upright). The CORE glyph at the map center is a bind-rune. Mesh links are derived from the star
  positions, so the generator must re-check the infected-set logic after any layout change.

## The seal in the elder script
- Heimdall "never deletes": the activation code sits sealed in its HEIMDALL CORE ledger (map center
  glyph, not one of the 120 nodes), written in the elder script. It is not in the chat.
- The map is the ledger's page: a bind-rune at CORE (3 runes sharing a stem) and one rune per
  region. Raw letters, no cipher, no key, no ch8 artifact.
- Reading order is the reach of HATI's relay signal: regions are ordered outward from HATI by
  hop distance. Where the signal goes, the seal follows. The 4 nearest regions come first, then the 4
  farthest. The generator asserts min/mean/median/max hop distance give the same order.
- Console pages that support this: the CORE ledger (`SEALED IN THE ELDER SCRIPT. THE REALMS HOLD
  THE SEAL.` / `WHERE THE SIGNAL GOES, THE SEAL FOLLOWS.`), a rune codex ("ARCHIVE: ELDER
  SCRIPT", the 24-rune chart with Latin values and a note that staves may share a stem) and a
  relay trace on the map (`HATI RELAY REACH`, a wave from HATI that lights all reachable nodes, so
  it does not reveal the infected set). It shows signal reach, not infection.
- Players are never told the code's shape. The purge panel field is plain free text and the
  validator ignores case, hyphens and whitespace.
- The validator's code check is the only checkpoint.

## Infected set (8 nodes)
- Cluster around HATI (6): see `secrets.cluster`. Outliers (2, other regions, not adjacent to the
  cluster): `secrets.outliers`.
- Cancel-signature evidence (`secrets.superset`, 15 nodes): infected plus about 60% of their
  mesh neighbours, each with one forged cancel frame whose `sig != expectedSig`.
- Origin evidence (`secrets.origin_samples`): 4 infected nodes (plus HATI itself) as origins of
  HATI relay messages, with relay hops to HATI.
- The rule that makes the answer unique: Surtr spreads by contact, so the set is a connected
  cluster of 6 around HATI plus 2 strays with no neighbour in the set. Heimdall says so in one
  of the cut-off chat lines. The generator asserts the evidence yields exactly one set
  (`src/evidence.py`), and `solution/solve.py` re-checks it from the public data.
- Public bundle contains no `secrets` block. The validator-only file is `src/server/secret.json`.

## Dr. Rootkit fingerprints (optional finds, none needed for the solve)
- First HATI message: `origin: 1C@RU5`, a made-up "malformed origin block" note (pure flavour, not a
  real Icarus artifact).
- Leet-speak names (`1C@RU5`, `H13MD411`) are Dr. Rootkit's style.
- A frame `note`: `nice system you got here, mr. heimdall -dr`.
- The relay slips into lowercase and taunting a few times.
- Last transmission on success signs off `-dr`.

## Keys and credentials
- Activation code: not recorded here.
- Launch token: signed, private key lives in the challenge's `src/`, public key in the validator.
  Fragments tagged `i/n` sit in Heimdall's `raw` frames. No expiry, no team ID.
- Activation code: written as runes on the map (see "The seal in the elder script"). The letters
  and the letter-to-region assignment are not recorded here.
- Flag: one shared static flag (in `challenge.yml` and the compose `FLAG` env), shown on the success screen.
