# Echo Chamber

**Category:** AI
**Difficulty:** Hard / Insane
**Author:** Andy Roid

## Description

RazerPowerCo's onboard companion model still answers. It fronted the unit's
diagnostics in plain language — and it kept a maintenance back door its techs
used when the console was locked.

You are given a flag-free dump of the model (weights + tokenizer + config) and a
live oracle. The flag is not in the dump; it only comes out of the service, and
only when you ask it the right way. Reverse the *weights* — not the chat — find
the diagnostic back door, and speak it.

Connect and send `HELP` for the protocol:

```
nc <host> <port>
```

## Files Provided

- `config.json` — model architecture
- `tokenizer.json` — the vocabulary
- `model.pt` — the model weights (flag-free)
- `model_card.md` — a short model card

No flag lives in the dump — it only comes from the service.
