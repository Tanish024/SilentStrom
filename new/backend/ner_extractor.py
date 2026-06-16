"""
ner_extractor.py — Named-entity & pattern extraction for Indian fraud complaints.

Combines:
  • spaCy en_core_web_sm   → ORG, PERSON, MONEY entities
  • Custom regex patterns  → UPI IDs, Indian mobile numbers, URLs, fake APK names

Usage:
    from ner_extractor import extract_entities
    result = extract_entities("SBI KYC Verify app se ₹25,000 fraud hua via ravi.kyc@ybl")
    # {'upi_ids': ['ravi.kyc@ybl'], 'phones': [], 'urls': [], 'app_names': ['SBI KYC Verify'],
    #  'orgs': ['SBI'], 'persons': [], 'amounts': ['₹25,000']}

Run this file directly to execute the built-in test block:
    python ner_extractor.py
"""

from __future__ import annotations

import re
import sys
from typing import Any

import spacy

# ══════════════════════════════════════════════════════════════════════
# 1. Load spaCy model (once at import time)
# ══════════════════════════════════════════════════════════════════════

try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    print(
        "⚠  spaCy model 'en_core_web_sm' not found. Installing...",
        file=sys.stderr,
    )
    from spacy.cli import download as spacy_download

    spacy_download("en_core_web_sm")
    nlp = spacy.load("en_core_web_sm")


# ══════════════════════════════════════════════════════════════════════
# 2. Regex patterns for Indian fraud identifiers
# ══════════════════════════════════════════════════════════════════════

# --- UPI IDs ----------------------------------------------------------
# Handles: user@ybl, user@oksbi, user@okhdfcbank, user@paytm, etc.
_UPI_HANDLES = (
    r"okhdfc|okhdfcbank|oksbi|okaxis|okicici"
    r"|ybl|upi|paytm|icici|apl|axl|ibl|sbi|hdfcbank"
)
UPI_PATTERN = re.compile(
    rf"[a-zA-Z0-9][a-zA-Z0-9._\-]{{1,}}@(?:{_UPI_HANDLES})\b",
    re.IGNORECASE,
)

# --- Indian mobile numbers --------------------------------------------
# 10 digits starting with 6-9, optional +91 / 0 prefix
PHONE_PATTERN = re.compile(
    r"(?:\+91[\s\-]?|0)?([6-9]\d{9})\b"
)

# --- URLs -------------------------------------------------------------
URL_PATTERN = re.compile(
    r"(?:https?://|www\.)[^\s<>\"']+",
    re.IGNORECASE,
)

# --- Monetary amounts (₹ / Rs / INR) ----------------------------------
AMOUNT_PATTERN = re.compile(
    r"(?:₹|Rs\.?\s*|INR\s?)[\d,]+(?:\.\d{1,2})?",
    re.IGNORECASE,
)

# --- Fake APK / app names ---------------------------------------------
# Build every combination of (brand) + (suffix) that appears in Indian
# fraud campaigns.  The regex requires at least ONE brand keyword followed
# by at least ONE suffix keyword so we don't over-match single words.
_APP_BRANDS = (
    "SBI|HDFC|ICICI|Paytm|PhonePe|YONO|KYC|Loan|Stock|Trading|Easy"
    "|SEBI|PM|Amazon|Flipkart|Delivery|Profit|Investment"
)
_APP_SUFFIXES = (
    "App|APK|Update|Verify|Pro|Platform|Approval|Failed|Verification"
)
# Match "SBI KYC Verify", "Easy Loan Approval", "Stock Profit Pro", etc.
# Allows 1-3 brand words before the suffix.
_APP_PATTERN_STR = (
    rf"\b((?:(?:{_APP_BRANDS})\s?){{1,3}}"
    rf"(?:{_APP_SUFFIXES}))\b"
)
APP_PATTERN = re.compile(_APP_PATTERN_STR, re.IGNORECASE)


# ══════════════════════════════════════════════════════════════════════
# 3. Main extraction function
# ══════════════════════════════════════════════════════════════════════

def extract_entities(text: str) -> dict[str, list[str]]:
    """
    Extract fraud-relevant entities from a single complaint text.

    Returns a dict with keys:
        upi_ids    – UPI virtual payment addresses
        phones     – Indian mobile numbers (10 digits, normalised)
        urls       – HTTP/HTTPS/www URLs
        app_names  – Fraudulent app / APK names
        orgs       – Organisation names (via spaCy NER)
        persons    – Person names (via spaCy NER)
        amounts    – Monetary amounts (₹ / Rs / INR patterns)
    """
    # ── Regex-based extraction ────────────────────────────────────────
    upi_ids = _dedupe(UPI_PATTERN.findall(text))
    phones = _dedupe(PHONE_PATTERN.findall(text))
    urls = _dedupe(URL_PATTERN.findall(text))
    app_names = _dedupe(APP_PATTERN.findall(text))
    amounts = _dedupe(AMOUNT_PATTERN.findall(text))

    # ── spaCy NER ─────────────────────────────────────────────────────
    doc = nlp(text)
    orgs = _dedupe(ent.text for ent in doc.ents if ent.label_ == "ORG")
    persons = _dedupe(ent.text for ent in doc.ents if ent.label_ == "PERSON")
    # Also capture spaCy MONEY entities that regex may have missed
    spacy_money = [ent.text for ent in doc.ents if ent.label_ == "MONEY"]
    for m in spacy_money:
        if m not in amounts:
            amounts.append(m)

    return {
        "upi_ids": upi_ids,
        "phones": phones,
        "urls": urls,
        "app_names": app_names,
        "orgs": orgs,
        "persons": persons,
        "amounts": amounts,
    }


def extract_entities_batch(
    complaints: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Enrich a list of complaint dicts in-place, adding an 'entities' key.
    Also merges regex-extracted UPI/phone with the raw fields already
    present in each complaint dict.
    """
    for c in complaints:
        ents = extract_entities(c.get("text", ""))

        # Merge with pre-existing raw fields
        raw_upis = c.get("upi_ids_raw", [])
        raw_phones = c.get("phone_raw", [])
        ents["upi_ids"] = _dedupe(ents["upi_ids"] + raw_upis)
        ents["phones"] = _dedupe(ents["phones"] + raw_phones)

        c["entities"] = ents

    return complaints


# ══════════════════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════════════════

def _dedupe(seq) -> list[str]:
    """Return a list of unique strings, preserving first-seen order."""
    seen: set[str] = set()
    result: list[str] = []
    for item in seq:
        s = item.strip()
        if s and s not in seen:
            seen.add(s)
            result.append(s)
    return result


# ══════════════════════════════════════════════════════════════════════
# 4. Built-in test block
# ══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import json

    test_cases = [
        # ── Hindi complaint (Campaign A — KYC fraud) ──────────────────
        (
            "Hindi (KYC fraud)",
            "SBI se call aaya ki KYC expire ho gaya hai. SBI KYC Verify app "
            "download karke OTP diya, phir account se Rs 25,000 kat gaye. "
            "UPI ID ravi.kyc@ybl se transfer hua. Phone number tha +91-9876543210. "
            "HDFC Bank ka naam use kiya inhone.",
        ),
        # ── English complaint (Campaign B — Loan scam) ────────────────
        (
            "English (Loan scam)",
            "Applied for personal loan on Easy Loan Approval app. They asked for "
            "INR 8,000 processing fee via UPI to easyloan.proc@oksbi. After paying, "
            "the app stopped working. Customer care number 8877665544 is unreachable. "
            "The website https://easyloan-approval.in was also taken down.",
        ),
        # ── Mixed Hindi+English (Campaign D — Delivery fraud) ─────────
        (
            "Mixed (Delivery fraud)",
            "Amazon Delivery Failed ka SMS aaya, link tha www.amz-delivery-update.com. "
            "Form fill kiya with UPI PIN, account se ₹12,000 kat gaye via "
            "delivery.refund@ybl. Caller ID 09345678901 se call bhi aaya tha. "
            "Flipkart Delivery Failed ka bhi message aaya tha pehle.",
        ),
    ]

    print("=" * 72)
    print("  SilentStorm NER Extractor — Test Results")
    print("=" * 72)

    for label, text in test_cases:
        result = extract_entities(text)
        print(f"\n--- {label} ---")
        print(f"  Text: {text[:100]}...")
        print(f"  {json.dumps(result, indent=4, ensure_ascii=False)}")

    print("\n" + "=" * 72)
    print("  All tests complete.")
    print("=" * 72)
