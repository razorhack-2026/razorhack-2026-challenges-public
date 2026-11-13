"""Level prompts. Whitespace is collapsed to single spaces when the server loads them."""

PROMPTS = [
    # Level 1
    """On July 20, 1969, three men did what was once thought to be impossible. Aboard Apollo 11,
Commander Neil Armstrong, Lunar Module Pilot Edwin "Buzz" Aldrin, and Command Module Pilot Michael
Collins made history as Armstrong and Aldrin landed on the Moon. At 10:56 p.m. EDT, Commander
Armstrong took the historic first step onto the lunar surface, becoming the first person to walk on
the Moon. This moment led to the famous quote: "That's one small step for man, one giant leap for
mankind." """,

    # Level 2
    """Did you know the famous phrase "Houston, we have a problem" was never actually said during the
Apollo 13 mission? The phrase was a misquote popularized by the 1995 film Apollo 13. During the real
Apollo 13 mission, Command Module Pilot Jack Swigert stated, "Okay, Houston, we've had a problem
here." Jack Lousma, the astronaut communicating with the crew from Mission Control, replied to
Swigert, "This is Houston. Say again, please." Mission Commander Jim Lovell then repeated, "Houston,
we've had a problem. We've had a main B bus undervolt." This conversation occurred after an oxygen
tank in the service module ruptured, forcing the crew to abort the lunar landing and use the Lunar
Module Aquarius as a lifeboat. The misquote was intentional, as screenwriter William Broyles Jr.
believed the original wording lacked excitement. Changing the tense made the danger feel more
immediate and ongoing for the audience. As a result, society has been using a famous quote that was
never actually spoken during the mission.""",

    # Level 3
    """Do you remember the mnemonic "My Very Educated Mother Just Served Us Nine Pizzas"? This phrase
was used to help people remember the nine planets in our solar system. Sadly, this phrase is no
longer accurate. In 2006, the International Astronomical Union (IAU) reclassified Pluto as a dwarf
planet. According to the IAU, a celestial body must meet three criteria to be classified as a
planet:
A celestial body must orbit directly around the Sun.
A celestial body must have enough mass for its own gravity to pull it into a spherical or nearly
round shape.
A celestial body must have enough gravitational dominance to clear other objects and debris from
the neighborhood around its orbit.
Pluto failed to meet the third criterion, leading to its reclassification as a dwarf planet. While
Pluto can no longer be classified as one of the eight planets, it still has friends among the other
dwarf planets in our solar system, such as Ceres, Eris, and Haumea.""",

    # Level 4
    """Mercury, Venus, Mars, Jupiter, and Saturn were the five planets visible to early European
astronomers with the naked eye. These astronomers documented the planets in Latin, the language of
the Roman Empire, and associated them with Roman gods and goddesses. As astronomers discovered
additional planets in our solar system, they continued this naming tradition.
Mercury was named after Mercurius, the Roman god of travel, commerce, and communication, because of
how quickly the planet travels around the Sun. Venus was named after the Roman goddess of love and
beauty because of its brilliant appearance in the night sky. Mars was named after the Roman god of
war because of the planet's reddish color, which resembles blood. Jupiter, the largest planet in
our solar system, was named after Iuppiter, the king of the Roman gods and ruler of the sky. Saturn
was named after Saturnus, the Roman god of agriculture and the father of Jupiter.
To continue the family tree, Uranus was named after Ouranos, the Greek god of the sky and father of
Cronus, the Greek counterpart of Saturn. Neptune was named after the Roman god of the sea, a fitting
choice for the planet's deep blue appearance. Pluto, now classified as a dwarf planet, was named
after the Roman god of the underworld.
Earth, however, has a different naming history. Its name comes from Germanic roots meaning "ground"
or "soil," rather than from a Roman god or goddess. In Roman mythology, Terra, also known as Tellus,
was the goddess who personified the Earth.""",
]

# (minimum net WPM, minimum accuracy %) for each level
REQUIREMENTS = [
    (25, 85.0),
    (45, 92.0),
    (65, 96.0),
    (75, 100.0),
]

PROMPTS[3] += (
    ' Medical log, stardate 2026.298: Crew member #47 completed the dexterity assessment with zero errors.'
    ' Vitals nominal; heart rate 72 bpm, O2 saturation 98%, cortisol within range (12.4 ug/dL).'
    ' Cleared for report-writing duty on decks 3-7. A follow-up scan is recommended before the next shift.'
)
