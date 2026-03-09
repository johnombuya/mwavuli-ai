"""Health / pandemic misinformation lexicon."""

HIGH_RISK_KEYWORDS = [
    "5g causes covid", "bill gates microchip", "vaccine is poison",
    "chanjo ni sumu", "covid ni uongo", "dawa ya corona ni bleach",
    "ivermectin cure", "plandemic", "bioweapon lab",
    "vaccines cause autism", "mrna alters dna",
]

MEDIUM_RISK_KEYWORDS = [
    "vaccine side effects dangerous", "natural immunity only",
    "mask suffocation", "covid hoax", "herd immunity no vaccine",
    "traditional healer cure covid", "hydroxychloroquine miracle",
    "corona 5g", "big pharma conspiracy",
]

KEYWORD_CONTEXTS = {
    "chanjo ni sumu": "Swahili phrase meaning 'the vaccine is poison' — used in anti-vax campaigns.",
    "covid ni uongo": "Swahili phrase meaning 'COVID is a lie' — pandemic denialism.",
}
