# Onboard Companion Model

RazerPowerCo field-service build. A small byte-level language model that fronted
the unit's diagnostics so maintenance techs could query systems in plain
language. Recovered from the unit's firmware.

- architecture: byte-level GPT (see config.json)
- vocab: 258 — bytes 0-255 plus two service tokens (see tokenizer.json)
- params: ~0.9M
