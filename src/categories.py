"""Keyword classification of tender descriptions.

Edit CATEGORY_KEYWORDS to change the rules. Categories are tried in the
order listed and the first match wins, so put the more specific category
first (a consultancy for a building project is "consultancy", not
"construction"). Keywords match whole words, case-insensitive; a keyword
may be a phrase. Descriptions matching nothing are "other".
"""

from __future__ import annotations

import re

import pandas as pd

OTHER = "other"

CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "consultancy": [
        "consultancy", "consultant", "consultants", "consulting", "advisory", "quantity surveying",
        "feasibility study", "professional services",
    ],
    "IT": [
        "software", "ict", "information technology", "it system", "it systems", "server", "servers",
        "cloud", "data centre", "database", "cyber", "cybersecurity", "computer", "computers", "laptop",
        "laptops", "website", "web portal", "portal", "mobile app", "mobile application",
        "application maintenance", "application development", "application support", "erp", "crm",
        "licence", "licences", "license", "licenses", "hosting", "helpdesk", "end user computing",
        "digital platform", "network infrastructure",
    ],
    "construction": [
        "construction", "erection", "addition and alteration", "addition & alteration", "a&a",
        "upgrading works", "renovation", "redevelopment", "demolition", "civil engineering", "civil works", "piling",
        "tunnel", "tunnels", "viaduct", "drainage", "road works", "building works", "reinstatement works",
        "retrofitting", "retrofit", "interchange", "expressway", "bridge", "footbridge",
    ],
    "cleaning/facilities": [
        "cleaning", "cleansing", "pest control", "horticulture", "arboriculture", "landscape",
        "landscaping", "turf", "facilities management", "facility management", "maintenance",
        "security services", "security guard", "lift", "lifts", "air-conditioning", "acmv",
        "mechanical and electrical", "m&e", "waste", "refuse", "conservancy", "managing agent",
    ],
    "training": [
        "training", "course", "courses", "coaching", "trainer", "trainers",
    ],
    "supplies": [
        "supply", "purchase", "procurement of", "equipment", "furniture", "uniform", "uniforms",
        "vehicle", "vehicles", "consumables", "stationery", "reagents", "spare parts", "delivery",
    ],
}


def _pattern(keywords: list[str]) -> re.Pattern:
    alternatives = sorted((re.escape(k) for k in keywords), key=len, reverse=True)
    return re.compile(r"(?<![A-Za-z0-9])(?:" + "|".join(alternatives) + r")(?![A-Za-z0-9])", re.IGNORECASE)


_PATTERNS = {category: _pattern(words) for category, words in CATEGORY_KEYWORDS.items()}


def classify_descriptions(descriptions: pd.Series) -> pd.DataFrame:
    """category (first match in dictionary order, else "other"), n_categories_matched, matched."""
    text = descriptions.fillna("").astype(str)
    hits = pd.DataFrame({category: text.str.contains(pattern) for category, pattern in _PATTERNS.items()})
    matched = hits.apply(lambda row: ", ".join(c for c, hit in row.items() if hit), axis=1)
    category = hits.idxmax(axis=1).where(hits.any(axis=1), OTHER)
    return pd.DataFrame({"category": category, "n_categories_matched": hits.sum(axis=1), "matched": matched})
