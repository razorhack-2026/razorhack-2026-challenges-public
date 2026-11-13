# How To Read

That title might sound silly. You already know how to read. But reading *carefully* is a skill, and it's one of the most valuable ones you can have at RASA.

## Read Everything. Thoroughly.

Important information doesn't always come with a big red label. It hides in:

- **The bottom of a document** that most people stop reading halfway through
- **Tables and footnotes** that get skimmed
- **Odd-looking text**: a strange string of letters or numbers that doesn't seem to belong
- **Small details**: a name, a date, a color, a number that shows up in more than one place

A few habits that help:

1. **Read the whole document before acting on any of it.** The answer to your question might be in the last paragraph.
2. **Read it twice.** The first pass tells you what it says. The second pass tells you what it *means*.
3. **Take notes.** Write down anything that seems unusual, even if you don't know why yet.
4. **Connect the dots.** Information in one document often explains something in another.
5. **Question things.** If something looks out of place, it probably is.

## Encoding vs. Encryption

Sometimes text isn't meant to be read at a glance. It's important to know the difference between two ideas:

- **Encoding** changes how data is *represented* so it can be stored or transmitted. Anyone who knows the format can reverse it. There's no secret.
- **Encryption** scrambles data using a *key*. Without the key, it should be very hard to reverse.

Most of the "secret" text you'll run into around the station is actually just encoded, or uses a very simple cipher. Once you can recognize what you're looking at, decoding it is usually easy.

## Common Formats and What They Look Like

### Decimal, Hexadecimal, Binary, and Octal

These are all ways of writing the same number in different bases.

| Format | Base | Digits used | The number 42 |
|---|---|---|---|
| Decimal | 10 | 0-9 | `42` |
| Hexadecimal (hex) | 16 | 0-9, A-F | `2A` (often written `0x2A`) |
| Binary | 2 | 0, 1 | `101010` (often written `00101010`) |
| Octal | 8 | 0-7 | `52` (sometimes written `0o52`) |

Text can be written this way too, since every character has a number. The letters `RASA` look like this:

- **ASCII decimal:** `82 65 83 65`
- **Hex:** `52 41 53 41` (or `52415341`)
- **Binary:** `01010010 01000001 01010011 01000001`

**How to spot them:**

- Hex only uses `0-9` and `A-F`, often comes in pairs, and sometimes starts with `0x`.
- Binary is long strings of only `0` and `1`, usually in groups of 8.
- ASCII decimal is usually numbers between 32 and 126 separated by spaces.

### Base64

Base64 turns any data into letters, numbers, `+`, and `/`. It's everywhere: emails, web pages, config files.

- `RASA` → `UkFTQQ==`
- `Hello, cadet!` → `SGVsbG8sIGNhZGV0IQ==`

**How to spot it:** a mix of upper- and lowercase letters and numbers that looks like gibberish, and it often (but not always) ends with one or two `=` signs.

### Caesar Cipher and ROT13

One of the oldest ciphers there is: shift every letter forward in the alphabet by a fixed amount.

- With a shift of 3, `RASA` becomes `UDVD`.
- **ROT13** is a shift of 13. Since the alphabet has 26 letters, applying ROT13 twice gets you back where you started. `Hello, cadet!` becomes `Uryyb, pnqrg!`

**How to spot it:** looks like words, with normal spacing and punctuation, but the words are nonsense. Short words like `gur` (ROT13 for `the`) are a giveaway.

### URL Encoding

Used in web addresses. Special characters get replaced with `%` and their hex value.

- `mine the belt!` → `mine%20the%20belt%21`

**How to spot it:** lots of `%` followed by two hex characters. `%20` (a space) is the most common.

### Other Things to Watch For

- **Reversed text:** `tlbe eht enim` is just `mine the belt` backwards.
- **Morse code:** dots and dashes, like `.-. .- ... .-` (RASA).
- **Leetspeak:** letters swapped for look-alike numbers and symbols, like `3` for `E`, `0` for `O`, `@` for `A`, or `!` for `I`.
- **Layers:** sometimes something is encoded *more than once*. If you decode it and get more gibberish, try decoding that too.

## A Useful Tool: CyberChef

**CyberChef** is a free, browser-based tool (made by GCHQ, the UK's intelligence and security agency) often called "the Cyber Swiss Army Knife." You can find it by searching for "CyberChef" or going to `gchq.github.io/CyberChef`.

It lets you chain together "recipes" of operations, such as *From Hex*, *From Base64*, *ROT13*, *From Binary*, and hundreds more, and see the result instantly. Some features worth knowing:

- **Drag and drop operations** into the recipe to stack them in order.
- **The "Magic" operation** tries to automatically detect what encoding something is in. It's a great starting point when you have no idea what you're looking at.
- **Everything runs in your browser**, so nothing you paste in is sent anywhere.

A word of advice: CyberChef is a fantastic tool, but try to understand *why* a recipe works, not just that it does. Recognizing base64 or hex on sight is a skill that will serve you well long after this onboarding is over.

## Summary

- Read every document, all the way to the end.
- Notice what looks out of place.
- Learn to recognize common encodings.
- Use tools like CyberChef to decode, and understand what you decoded.
