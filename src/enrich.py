"""Normalize raw Plaid transactions into clean rows for CSV / dashboard.

Pulls category and merchant out of Plaid's fields and adds a short account
code (initials) used to tag accounts compactly in the UI.
"""


def prettify_category(txn):
    """Turn Plaid's personal_finance_category into 'Food and drink' style text."""
    code = None
    pfc = txn.get("personal_finance_category")
    if isinstance(pfc, dict):
        code = pfc.get("primary")
    if not code:
        legacy = txn.get("category")
        if isinstance(legacy, (list, tuple)) and legacy:
            code = str(legacy[0])
    if not code:
        return "Uncategorized"
    words = [w for w in str(code).replace("-", "_").split("_") if w]
    s = " ".join(w.lower() for w in words)
    return (s[:1].upper() + s[1:]) if s else "Uncategorized"


def merchant_of(txn):
    return txn.get("merchant_name") or txn.get("name") or "Unknown"


# Category names used across the tracker. Keep in sync with config/budgets.yaml.
CATEGORIES = [
    "Travel", "Food and drink", "Merchandise", "Services",
    "Transportation", "Medical", "Entertainment", "Bank fees",
]

# Ordered (keyword -> category). First match wins, so put specific before broad.
_CATEGORY_KEYWORDS = [
    ("Entertainment", ["netflix", "spotify", "hulu", "disney+", "youtube premium", "prime video", "hbo", "max "]),
    ("Travel", ["delta air", "etihad", "united air", "american air", "airways", "airlines",
                "ritz", "marriott", "hilton", "hyatt", "hotel", "hertz", "enterprise",
                "avis", "airport", "cibo express", "breezeway", "station square",
                "prem car", "car rental", "mco ", "tsa", "amtrak"]),
    ("Food and drink", ["kroger", "lidl", "walmart", "whole foods", "trader joe", "aldi",
                         "publix", "safeway", "wegmans", "indifresh", "nuts.com",
                         "uber eats", "doordash", "grubhub", "starbucks", "friday",
                         "cafe", "restaurant", "chick-fil", "mcdonald", "chipotle",
                         "pizza", "canteen", "big peach", "breweries", "bar "]),
    ("Merchandise", ["amazon", "amzn", "ebay", "target", "best buy", "costco",
                     "home depot", "walgreens", "cvs", "rite aid", "ikea", "etsy"]),
    ("Transportation", ["shell", "bp ", "exxon", "chevron", "sunoco", "fuel", "gas station",
                        "uber ", "lyft", "mta", "transit", "parking", "toll", "hta-"]),
    ("Medical", ["allergy", "asthma", "pharmacy", "onemed", "medical", "clinic",
                 "doctor", "dental", "hospital", "id processing"]),
    ("Services", ["google", "parakeet", "cloud", "udacity", "preply", "coursera",
                  "microsoft", "apple.com", "dropbox", "zoom", "slack", "notion",
                  "github", "adobe", "canva", "figma", "openai", "vue*testing", "testing"]),
    ("Bank fees", ["return payment", "bank fee", "late fee", "annual fee",
                   "interest charge", "overdraft", "service charge", "atm fee"]),
]


def categorize(name):
    """Infer a spending category from a raw transaction/merchant name.

    Used as a fallback when Plaid's personal_finance_category is absent
    (e.g. a bare CSV). Returns one of CATEGORIES, defaulting to 'Services'.
    """
    n = (name or "").lower()
    for category, keywords in _CATEGORY_KEYWORDS:
        if any(k in n for k in keywords):
            return category
    return "Services"


# Known-messy raw descriptors -> clean display names.
_MERCHANT_MAP = {
    "AMAZON.COM AMZN.COM/BILL": "Amazon",
    "AMAZON MARKETPLACE NAMZN.COM/BILL": "Amazon Marketplace",
    "AMAZON ONEMED": "Amazon OneMed",
    "PARAKEET-AI DUBLIN CO": "Parakeet AI",
    "ETIHAD AIRWAYS MUMBAMUMBAI IN": "Etihad Airways",
    "AplPay LIDL #1441": "Lidl",
    "AplPay INDIFRESH 000CUMMING": "IndiFresh",
    "GOOGLE ONE G.CO/HELPPAY#": "Google One",
    "CLOUD F29JGN G.CO/HELPPAY#": "Google Cloud",
    "RETURN PAYMENT FEE": "Return payment fee",
    "AplPay PREPLY INC. 5BROOKLINE": "Preply",
    "WL *VUE*TESTING EXAMBLOOMINGTON": "Vue Testing",
    "ALLERGY AND ASTHMA CROSWELL": "Allergy & Asthma",
    "ENTERPRISE 411106CUMMING": "Enterprise Rent-A-Car",
    "SP NUTS.COM": "Nuts.com",
    "ID PROCESSING 014000": "ID Processing",
    "PREM CAR RENTAL PROTECTION": "Car Rental Protection",
}
_MERCHANT_PREFIX = [
    ("HERTZ", "Hertz"), ("CPI*CANTEEN", "Canteen Vending"), ("STELLIS", "Stellis News"),
    ("MCO CIBO", "Cibo Express"), ("BREEZEWAY", "Breezeway Cafe"),
    ("STATION SQUARE", "Station Square"), ("SP HTA", "HTA Atlanta"),
    ("AplPay BIG PEACH", "Big Peach Run"), ("T.G.I", "T.G.I. Friday's"),
]


def clean_merchant(name):
    """Turn a raw bank descriptor into a readable merchant name."""
    n = (name or "").strip()
    if not n:
        return "Unknown"
    if n in _MERCHANT_MAP:
        return _MERCHANT_MAP[n]
    for prefix, pretty in _MERCHANT_PREFIX:
        if n.upper().startswith(prefix.upper()):
            return pretty
    # Title-case ALL-CAPS descriptors; otherwise keep as-is, truncated.
    return (n[:28].title() if n.isupper() else n[:28])


def initials(name):
    parts = [p for p in str(name).split() if p]
    if len(parts) >= 2:
        return (parts[0][0] + parts[1][0]).upper()
    return (str(name)[:2]).upper() if name else "?"


# Map Plaid's prettified primary categories onto our canonical CATEGORIES.
_PLAID_TO_CANONICAL = {
    "Travel": "Travel",
    "Food and drink": "Food and drink",
    "General merchandise": "Merchandise",
    "General services": "Services",
    "Transportation": "Transportation",
    "Medical": "Medical",
    "Entertainment": "Entertainment",
    "Bank fees": "Bank fees",
    "Personal care": "Services",
    "Home improvement": "Merchandise",
    "Rent and utilities": "Services",
}


def canonical_category(txn):
    """Best category for a txn: Plaid's PFC mapped to our set, else inferred."""
    pc = prettify_category(txn)
    if pc in _PLAID_TO_CANONICAL:
        return _PLAID_TO_CANONICAL[pc]
    if pc != "Uncategorized":
        return pc  # some other Plaid label — keep it rather than lose info
    return categorize(txn.get("merchant_name") or txn.get("name") or "")


def normalize(txns):
    """Return clean row dicts: date, name, amount, account, category, merchant, id."""
    rows = []
    for t in txns:
        rows.append(
            {
                "date": t.get("date"),
                "name": t.get("name") or "",
                "amount": float(t.get("amount") or 0),
                "account": t.get("account") or "Unknown",
                "category": canonical_category(t),
                "merchant": clean_merchant(merchant_of(t)),
                "id": t.get("transaction_id") or "",
            }
        )
    return rows
