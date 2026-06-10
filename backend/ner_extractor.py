"""
ner_extractor.py — Named-entity and pattern extraction from complaint text.

Extracts:
  • UPI IDs   (regex: user@handle)
  • Phone numbers (regex: Indian 10-digit with optional +91/0 prefix)
  • App names  (keyword match against known fraudulent app names)
  • Monetary amounts (₹ / Rs / INR patterns)
"""

from __future__ import annotations

import re
from typing import Any

# ── Regex patterns ────────────────────────────────────────────────────
UPI_PATTERN = re.compile(r"[a-zA-Z0-9.\-_]{2,}@[a-zA-Z]{2,}")
PHONE_PATTERN = re.compile(r"(?:\+91[\s-]?|0)?[6-9]\d{9}")
AMOUNT_PATTERN = re.compile(r"(?:₹|Rs\.?|INR)\s?[\d,]+(?:\.\d{1,2})?")

# Known fraudulent app names (extend as campaigns are discovered)
KNOWN_APPS: list[str] = [
    "SBI KYC Verify",
    "HDFC KYC Verify",
    "Easy Loan Approval",
    "PM Loan App",
    "Stock Profit Pro",
    "SEBI Trading",
    "Amazon Delivery Failed",
    "Flipkart Delivery Failed",
]


def extract_entities(complaints: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Enrich each complaint dict with extracted entity fields:
      - upi_ids:  list[str]
      - phones:   list[str]
      - apps:     list[str]
      - amounts:  list[str]
    """
    for c in complaints:
        text = c.get("text", "")
        c["upi_ids"] = _extract_upi_ids(text, c.get("upi_ids_raw", []))
        c["phones"] = _extract_phones(text, c.get("phone_raw", []))
        c["apps"] = _extract_apps(text)
        c["amounts"] = AMOUNT_PATTERN.findall(text)
    return complaints


def _extract_upi_ids(text: str, raw_list: list[str]) -> list[str]:
    """Combine regex-found UPI IDs with the raw field."""
    found = set(UPI_PATTERN.findall(text))
    found.update(raw_list)
    return sorted(found)


def _extract_phones(text: str, raw_list: list[str]) -> list[str]:
    """Combine regex-found phones with the raw field."""
    found = set(PHONE_PATTERN.findall(text))
    found.update(raw_list)
    return sorted(found)


def _extract_apps(text: str) -> list[str]:
    """Match known fraudulent app names in the text (case-insensitive)."""
    text_lower = text.lower()
    return [app for app in KNOWN_APPS if app.lower() in text_lower]
