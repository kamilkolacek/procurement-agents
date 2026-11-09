"""Secret and PII scan of git-tracked (and staged) files. Exit 1 on any finding.

Add `scan-ok` on a line to allowlist a known false positive (reviewers should question it).
CI also runs gitleaks; this script adds PII patterns relevant to spend data.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKIP_SUFFIXES = {".parquet", ".png", ".jpg", ".pdf", ".xlsx", ".docx", ".zip", ".lock"}

PATTERNS: dict[str, re.Pattern[str]] = {
    "anthropic_key": re.compile(r"sk-ant-[A-Za-z0-9_\-]{20,}"),
    "openai_key": re.compile(r"\bsk-[A-Za-z0-9]{32,}\b"),
    "aws_access_key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "github_token": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b"),
    "private_key": re.compile("-----BEGIN [A-Z ]*" + "PRIVATE KEY-----"),
    "generic_secret": re.compile(
        r"(?i)\b(api[_-]?key|secret|password|token)\b\s*[:=]\s*['\"][^'\"\s]{12,}['\"]"
    ),
    "us_ssn": re.compile(r"\b(?!000|666|9\d\d)\d{3}-(?!00)\d{2}-(?!0000)\d{4}\b"),
    "iban": re.compile(r"\b[A-Z]{2}\d{2}(?: ?[A-Z0-9]{4}){3,7}(?: ?[A-Z0-9]{1,4})?\b"),
}
CARD_RE = re.compile(r"\b(?:\d[ -]?){13,19}\b")


def luhn_ok(digits: str) -> bool:
    total, alt = 0, False
    for ch in reversed(digits):
        d = int(ch)
        if alt:
            d = d * 2 - 9 if d > 4 else d * 2
        total, alt = total + d, not alt
    return total % 10 == 0


def scan_text(text: str) -> list[tuple[int, str]]:
    findings = []
    for lineno, line in enumerate(text.splitlines(), 1):
        if "scan-ok" in line:
            continue
        for name, pat in PATTERNS.items():
            if pat.search(line):
                findings.append((lineno, name))
        for m in CARD_RE.finditer(line):
            digits = re.sub(r"\D", "", m.group())
            if 13 <= len(digits) <= 19 and luhn_ok(digits) and len(set(digits)) > 1:
                findings.append((lineno, "payment_card"))
    return findings


def tracked_files() -> list[Path]:
    out = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=ROOT, capture_output=True, text=True, check=True,
    ).stdout
    return [ROOT / p for p in out.splitlines() if p]


def main() -> int:
    bad = 0
    for path in tracked_files():
        if path.suffix in SKIP_SUFFIXES or not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for lineno, name in scan_text(text):
            print(f"{path.relative_to(ROOT)}:{lineno}: possible {name}", file=sys.stderr)
            bad += 1
    if bad:
        print(f"\nsecret/PII scan: {bad} finding(s)", file=sys.stderr)
        return 1
    print("secret/PII scan: clean")
    return 0


if __name__ == "__main__":
    sys.exit(main())
