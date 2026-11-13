# Know Your Mark

**Category:** OSINT
**Difficulty:** Medium
**Author:** Voyager 1

*(1/3 of the "Lateral Drift" sequence.)*

## Description

Ship security got into the personal email account Dr. Rootkit's been using this whole time.
They recovered one message and compiled a list of sites he might use. Sherlock could help us
search them—if only we knew what username he was using.

Once you know who he is, get him to click something. Security already has a tracking link ready
to go, but it's not subtle, so you'll have to hide it before he will.

## Files Provided

- `recovered_email.pdf` - one message pulled from the account's Sent folder
- A Sherlock site list, downloadable from the mail portal

Download the Sherlock site list from the mail portal, then run
`sherlock --json sherlock-sites.json <username>`.

The Kali image's system Sherlock install doesn't apply `--json` correctly and will scan the
normal internet-wide site list instead of just the two sites above. If that happens, install a
current copy and run that instead:
```
pip install --user --break-system-packages --ignore-installed --no-cache-dir sherlock-project
python3 -m sherlock_project --json sherlock-sites.json <username>
```

## The link

Here's the tracking link:

```
http://dangerouslink.com/notify?id=8841x
```

Yes, that's really the domain. Paste it in as-is and he (or a spam filter) will see exactly what
it is and ignore it. In the mail composer, select the text you want him to see and use
**Insert link** to attach the address. You can also use the button to enter the link text and
address together.

Don't spell the domain out in the link text, and don't leave a second, bare copy of it sitting
anywhere else in your message. Either slip-up and the disguise is pointless. And the link by
itself won't get you anywhere - he still has to buy the rest of the email first.

## Connection

Open your team's assigned mail portal URL in a
browser, write your message (you pick the `From:`), and watch the thread below the form for a
reply. One message, one response, so read whatever comes back carefully before sending another.
Replies can take a minute or two. Requests that reach Rootkit have a per-team cooldown; there is
no limit on the number of attempts.

The sites in the list live on the same host as the mail portal, on different ports.
