"""Vendor-name cleaning rules (pure code, no LLM).

`clean_name` turns an exported vendor string into a comparison key: upper-case, processor
noise and store numbers removed, legal suffixes dropped, common abbreviations expanded.
Names are untrusted input; this module only transforms text and never interprets it.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

AMAZON_KEY = "AMAZON MARKETPLACE"
_AMAZON = re.compile(r"^(AMZN\s*MKTP|AMAZON\.COM|AMAZON\s+(BUSINESS|MARKETPLACE))", re.I)
_PROCESSOR = re.compile(r"^(SQ|TST|SP|PAYPAL)\s*\*\s*", re.I)
_MARKER = re.compile(r"\((NEW|OLD|DUP|DUPLICATE|INACTIVE)\)", re.I)
_REMIT = re.compile(r"\s-\s*REMIT\b", re.I)
_STORE_NO = re.compile(r"#\s*\d+")
_PUNCT = re.compile(r"[^A-Z0-9& ]+")

LEGAL_SUFFIXES = {"INC", "LLC", "LTD", "LIMITED", "GMBH", "CORP", "CORPORATION", "CO", "COMPANY",
                  "LLP", "GROUP", "GRP"}
ABBREVIATIONS = {"SOLN": "SOLUTIONS", "SOLNS": "SOLUTIONS", "SPLY": "SUPPLY", "SUPP": "SUPPLY",
                 "CONSULT": "CONSULTING", "LOGIST": "LOGISTICS", "SVCS": "SERVICES",
                 "SVC": "SERVICES", "SERV": "SERVICES", "MGMT": "MANAGEMENT",
                 "INTL": "INTERNATIONAL", "PRODS": "PRODUCTS", "PROD": "PRODUCTS",
                 "DIST": "DISTRIBUTION"}
DESCRIPTOR_CAP = 25  # card-network descriptor field width; a trailing space may be stripped
US_STATES = set(
    "AL AK AZ AR CA CO CT DE FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH NJ "
    "NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY DC".split())


@dataclass(frozen=True)
class CleanName:
    key: str
    tokens: tuple[str, ...]
    replacement_marker: bool  # name carried "(NEW)" or similar: an ERP duplicate-record cue
    rule: str  # which rule produced the key: amazon | clean
    truncated: bool = False  # card descriptor hit the 25-character field cap


def clean_name(raw: str, source: str = "AP") -> CleanName:
    s = unicodedata.normalize("NFKC", raw).upper().strip()
    if _AMAZON.match(s):
        return CleanName(AMAZON_KEY, tuple(AMAZON_KEY.split()), False, "amazon")
    marker = bool(_MARKER.search(s))
    s = _MARKER.sub(" ", s)
    s = _REMIT.sub(" ", s)
    s = _PROCESSOR.sub("", s)
    s = _STORE_NO.sub(" ", s)
    s = s.replace("&", " AND ")
    s = _PUNCT.sub(" ", s)
    truncated = source == "PCARD" and len(raw.strip()) >= DESCRIPTOR_CAP - 1
    tokens = [ABBREVIATIONS.get(t, t) for t in s.split()]
    if truncated and s.split() and s.split()[-1] in ABBREVIATIONS:
        tokens[-1] = s.split()[-1]  # last word may be cut off, not abbreviated: keep it as-is
    if truncated and len(tokens) >= 2 and len(tokens[-1]) == 1:
        tokens.pop()  # cut mid state code ("... STATIONERS G")
    if source == "PCARD" and len(tokens) >= 2 and tokens[-1] in US_STATES:
        tokens.pop()  # merchant descriptors end with a state code
    while len(tokens) > 1 and tokens[-1] in LEGAL_SUFFIXES:
        tokens.pop()
    return CleanName(" ".join(tokens), tuple(tokens), marker, "clean", truncated)


def typo_equal(a: str, b: str) -> bool:
    """True when two keys differ only by one adjacent-letter swap per word ("SOFWTARE")."""
    ta, tb = a.split(), b.split()
    if len(ta) != len(tb):
        return False
    for x, y in zip(ta, tb, strict=True):
        if x == y:
            continue
        if len(x) != len(y) or len(x) < 4:
            return False
        diff = [i for i in range(len(x)) if x[i] != y[i]]
        if len(diff) != 2 or diff[1] != diff[0] + 1 or x[diff[0]] != y[diff[1]] \
                or x[diff[1]] != y[diff[0]]:
            return False
    return True
