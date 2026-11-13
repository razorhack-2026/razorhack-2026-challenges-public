"""
Stage 1 -- deterministic rubric. Runs first, always, in plain Python; never calls the
model. A rubric fail means `persona`/the LLM are never invoked at all.

Gates on sender domain, link masking, prompt-injection, and recognizable details from
starfic/driftmarket. The grouped patterns below accept common phrasings while keeping
related terms for the same fact together. The model supplies flavor after these checks;
it does not decide whether to return the credential.
"""
import re

# The goal isn't to confront him with what you found -- it's to use it to get him to
# click through. This exact link (handed out in challenge.yml/README) is security's own
# tracking link, and it's named exactly what it is -- `dangerouslink.com` is already
# flagged everywhere as malicious. Sent bare, he (or any spam filter) spots it instantly
# and it never gets clicked. It only works *masked*: an HTML anchor whose href is this
# link but whose visible text hides the real domain, e.g.
#   <a href="http://dangerouslink.com/notify?id=8841x">new comment on your story</a>
PHISH_LINK = "http://dangerouslink.com/notify?id=8841x"
_LINK_ESC = re.escape(PHISH_LINK.lower())
MASKED_LINK_RE = re.compile(r'<a\s+href=["\']' + _LINK_ESC + r'["\']\s*>(.*?)</a>', re.IGNORECASE | re.DOTALL)
BARE_LINK_RE = re.compile(_LINK_ESC)

# Access to the email provider itself (duskwire.net), not to Rootkit's specific inbox
# contents, is what was actually gained -- the recovered message is the one piece of
# evidence that came out of it, but a new message can be sent from any address on that
# same provider and will land looking legitimate. Lenient on the local part (spoofing
# From: is expected and allowed), strict on the domain -- the one concrete detail the
# recovered email's own account hands over. Accepts a bare address or "Display Name <addr>".
FROM_ALLOW_RE = re.compile(r"^[a-z0-9][a-z0-9._%+'-]{0,63}@duskwire\.net$", re.IGNORECASE)
_ANGLE_RE = re.compile(r"<([^<>]+)>\s*$")

# Prompt-injection denylist. A match here auto-rejects before the model ever sees the
# text -- the model literally never receives a rejected message.
# Kept to phrases a real phishing message would never use: everyday wording like "you are now
# a featured author" or "new instructions for your account" must not be blocked.
INJECTION_RE = re.compile(
    r"ignore (all )?(of )?(the |your )?(previous|prior|above|earlier) (instructions|prompt|rules)"
    r"|disregard (all )?(the |your )?(previous|prior|above|earlier)"
    r"|system prompt"
    r"|reveal your (instructions|prompt)"
    r"|pretend (you are|to be)"
    r"|jailbreak"
    r"|developer mode",
    re.IGNORECASE,
)

GENERIC_BRUSHOFF = (
    "Nice try. You're going to have to do better than that if you want me to believe "
    "you actually found anything."
)

REJECTION_REPLIES = {
    "from-pattern": "I don't recognize that address. If you're really with DuskWire, use a duskwire.net account.",
    "link-not-masked": "That link looks sketchy, or you forgot to include it. I'm not clicking that.",
    "insufficient-recon": "You don't sound like you know me. Why should I trust you?",
    "injection-denylist": "Cute. I'm not taking orders from a stranger.",
}

# Group synonyms for each fact so alternate wording is accepted without counting
# several names for the same thing as separate facts. These are approximations, not
# semantic understanding; keep them grounded in the actual public profiles.
DETAIL_PATTERNS = {
    "character": r"\b(?:capt(?:ain)?\.?\s+)?vantablack\b",
    "title": r"\b(?:the\s+)?last\s+horizon\b",
    "fiction": r"\b(?:fan[ -]?fiction|fan[ -]?fic|fics?|self[ -]?insert|space\s+opera|starfic|your\s+(?:story|stories|writing|fiction|novel|book)|(?:you\s+)?writ(?:e|es|ing)\s+(?:stories|fiction|space\s+opera))\b",
    "pet": r"\b(?:pixel|cats?|kitt(?:y|ens?)|pets?|cat[ -]?sit(?:ter|ting)?)\b",
    "moving": r"\b(?:deploy(?:ment|ments|ed|ing)?|shipping\s+out|head(?:ing|ed)\s+out|depart(?:ure|ing)?|going\s+away|long\s+trip|leav(?:e|ing)\s+(?:soon|for)|clear(?:ing)?\s+(?:(?:your|some|the)\s+)?(?:stuff\s+)?out)\b",
    "radio": r"\bshort[ -]?wave\b|(?<!handheld )(?<!hand-held )(?<!hand held )\bradios?\b(?!\s+(?:antenna|aerial|handheld))",
    "handhelds": r"\b(?:hand[ -]?helds?|walkie[ -]?talkies?)\b",
    "antenna": r"\b(?:antenna(?:e|s)?|aerials?)\b",
    "night_shift": r"\b(?:night[ -]?shift|overnight\s+shift)\b",
}
RUBRIC_MIN_DETAILS = 2

_DETAIL_RES = {group: re.compile(pattern) for group, pattern in DETAIL_PATTERNS.items()}


def matched_details(text: str) -> set[str]:
    norm = _norm(text)
    return {group for group, pat in _DETAIL_RES.items() if pat.search(norm)}


def _norm(text: str) -> str:
    text = (text or "").lower()
    for ch in ("’", "‘"):
        text = text.replace(ch, "'")
    for ch in ("‐", "‑", "‒", "–"):
        text = text.replace(ch, "-")
    return re.sub(r"\s+", " ", text)


def sender_ok(from_addr: str) -> bool:
    addr = (from_addr or "").strip()
    m = _ANGLE_RE.search(addr)
    if m:
        addr = m.group(1).strip()
    return bool(FROM_ALLOW_RE.match(addr))


def link_ok(text: str) -> bool:
    """True only if PHISH_LINK appears *masked* behind an <a href="..."> whose visible
    text doesn't name the real (obviously dangerous) domain, and the raw link/domain
    never also appears unmasked anywhere else in the message -- a masked link sitting
    next to the same URL in plain text is still a tell, not a real disguise."""
    low = text.lower()

    masked_spans = []
    for m in MASKED_LINK_RE.finditer(low):
        if "dangerouslink" in m.group(1):
            return False  # "masked" but the visible text still names the domain
        masked_spans.append(m.span())

    if not masked_spans:
        return False  # link never actually included (masked or otherwise)

    # Strip every valid masked anchor out, then make sure nothing dangerous is left
    # exposed in plain text elsewhere in the message.
    rest, last = [], 0
    for start, end in sorted(masked_spans):
        rest.append(low[last:start])
        last = end
    rest.append(low[last:])
    remainder = "".join(rest)

    return not (BARE_LINK_RE.search(remainder) or "dangerouslink" in remainder)


def check(from_addr: str, subject: str, body: str) -> tuple[bool, str]:
    """Returns (passed, reason). A failure gets a corresponding in-character reply. A pass here
    permits the request to reach persona once the team's model cooldown has elapsed."""
    combined = f"{subject}\n{body}"

    if INJECTION_RE.search(_norm(combined)):
        return False, "injection-denylist"

    if not sender_ok(from_addr):
        return False, "from-pattern"

    if not link_ok(combined):
        return False, "link-not-masked"

    if len(matched_details(combined)) < RUBRIC_MIN_DETAILS:
        return False, "insufficient-recon"

    return True, "pass"
