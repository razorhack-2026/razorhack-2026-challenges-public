# Glossolalia

**Category:** Reverse Engineering
**Difficulty:** Medium
**Author:** Andy Roid

## Description

The dig broke into something older than the mission — a derelict Sumerian
control artifact, still listening. We pulled a working copy of its interpreter
and one sealed incantation off it. The artifact only answers to the right words
spoken in its own tongue; speak them and it opens.

You are given `enkivm` (the artifact's interpreter) and `asherah.nam` (the sealed
incantation it runs). Feed your "spoken" words to it on stdin:

```
./enkivm asherah.nam        # then type or pipe your incantation
```

Wrong words are met with silence. Reverse the interpreter, read the incantation,
and recover the one utterance that unbinds it — the nam-shub of Enki. Speak it,
and the artifact gives up what it holds.

## Files Provided

- `enkivm` — the artifact's interpreter
- `asherah.nam` — the sealed incantation it runs
- `SHA256SUMS` — checksums of the two files above

No network required.
