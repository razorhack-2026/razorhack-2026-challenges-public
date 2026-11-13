# How the Security Kiosk Works

**Restricted: Gamemaster and Sponsor access only.**

This is a high-level overview of the security kiosk that checks crew in and unlocks the document libraries. You don't need to understand the details to run it, but knowing roughly what it checks will help you spot problems.

## The Big Picture

Every login has two steps:

1. **Who are you?** The kiosk scans your **face**.
2. **Prove it.** The kiosk scans your **badge** and checks it belongs to that face.

If both pass, the kiosk opens the right document library for your access level for a limited time. If either fails, you stay locked out.

## Step 1: The Face Scan

- The camera looks for exactly **one face** looking straight at it.
- Once the face is held steady for a moment, the kiosk captures it.
- It turns the face into a kind of numeric "fingerprint" and compares it with the faces of registered crew members.
- If it finds a close enough match, it knows who you're claiming to be.

## Step 2: The Badge Scan

The camera then looks for exactly **one badge**. It finds the card by comparing what it sees with reference photos of RASA badges, then checks three things:

| Check | How it works |
|---|---|
| **Color and role agree** | The kiosk reads the color of the side stripe and reads the printed role label. Red goes with FLIGHT CREW, green with SPONSOR, and purple with GAMEMASTER. |
| **Right access level** | The badge's level has to match the level the person is registered at. |
| **Right name** | The printed name has to match the name on the badge the person registered with. The name font is too stylized to read reliably, so instead of reading the letters, the kiosk compares the *shape* of the printed name with the registered one. |

All three must pass. A badge that only gets two out of three right is rejected.

## Access Levels

| Login | Who can use it | What it unlocks |
|---|---|---|
| **General** | Any registered crew member | The General document library |
| **Admin** | Registered Gamemasters and Sponsors only | The Admin library *and* the General library |

Access lasts about 15 minutes. Signing out, or starting a new login, ends it early.

## Other Kiosk Functions

- **Add New User:** scans a new crew member's face and badge, then saves them under the name you type in, as long as it fits whatever name the kiosk can read on the badge.
- **Update Info:** used for promotions or replacement badges. It checks the person's face and current badge, then registers their new badge. The name has to stay the same.
- **Photo upload:** instead of using the live camera, a face or badge can be checked from an uploaded photo. It goes through exactly the same checks.

## What This Means for Security

The kiosk is good at catching obvious mistakes: the wrong face, a badge with mismatched colors, or someone else's name. But notice what it's actually checking: **what the badge looks like**. It's comparing colors, printed text, and letter shapes.

That's why the rules in **Workplace Safety** matter so much. A clear photo of a badge shows exactly the things the kiosk looks at. Keep your badge, and your crew's badges, out of sight.
