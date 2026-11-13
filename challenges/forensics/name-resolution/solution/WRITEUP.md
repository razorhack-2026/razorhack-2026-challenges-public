# Name Resolution — solution (GM-only)

**Flag:** `flag{just_a_d1fferent_kind_of_lookup}`

## Mechanism

The console exfiltrates a payload over **DNS**. There is no file transfer and
nothing on a watched port — the data rides the one protocol that is allowed to
leave almost any network: name resolution.

Most DNS in the capture is ordinary internal resolution of `*.kot.rpc`. The
exfil is a run of lookups to a single off-manifest **vessel beacon** domain,
`uplink.hull-kx9.beacon` (hull KX9 is on no convoy roster — an unidentified
ship), each resolving to the same off-ship relay address `100.64.9.9`. The
leftmost subdomain label on each query is `<seq>-<chunk>`: a two-digit sequence
counter and a base32 chunk of the payload.

The decoded dump names the destination as an off-manifest vessel and tags the
`handler` as `"the helper"` — the same friendly onboarding helper from
[[Day One]] (i.e. Dr. Rootkit). That is a soft arc fingerprint for players who
have done the onboarding chain; it deliberately stops short of naming ICARUS, so
it doesn't pre-empt the Icarus-cover-up reveal in Lt. Rico Kopernicus's chain.

## Intended solve

1. Open `capture.pcap` in Wireshark (or scapy). Filter to DNS. The internal
   `*.kot.rpc` lookups are expected; the repeated lookups to the off-manifest
   `*.uplink.hull-kx9.beacon` with random-looking subdomains — all resolving to
   the same off-ship address — are the tell of a DNS covert channel to an
   unidentified vessel.
2. Collect those query names, order them by the leading `<seq>` number, strip
   the `<seq>-` prefix, and concatenate the remaining base32 chunks.
3. base32-decode the concatenation (pad to a multiple of 8). The decoded blob is
   a short text dump that contains the flag.

## Reference solver

`solve.py` does exactly this, reading only `dist/capture.pcap`:

```
python3 solve.py dist/capture.pcap
```

It imports nothing from the build script and hardcodes no answer. Verified
2026-11-02: recovers the flag from the shipped `dist/` artifact alone.

## Rebuild

`python3 src/build.py` regenerates `dist/capture.pcap` deterministically
(`random.seed(20261102)`, fixed Ethernet MACs), byte-for-byte on any host.
`src/build.py` holds the flag and must never ship.
