"""Fraud / scam detection lexicon."""

HIGH_RISK_KEYWORDS = [
    "send money to unlock", "mpesa pin share", "your account suspended send",
    "lottery winner send fee", "safaricom promotion pin",
    "western union claim code", "inheritance million share details",
]

MEDIUM_RISK_KEYWORDS = [
    "guaranteed profit", "double your money", "risk free investment",
    "act now limited offer", "secret investment scheme",
    "forex signal guaranteed", "pyramid opportunity",
    "send airtime to verify",
]

KEYWORD_CONTEXTS = {
    "mpesa pin share": "M-Pesa PIN phishing — a common mobile-money scam in Kenya.",
    "safaricom promotion pin": "Impersonates Safaricom promotions to steal PINs.",
}
