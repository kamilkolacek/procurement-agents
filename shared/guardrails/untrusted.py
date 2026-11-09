"""Wrap untrusted text (vendor names, descriptions) in delimiters the text cannot forge."""

from __future__ import annotations

import re
import unicodedata

MAX_FIELD_CHARS = 500
_TAG_RE = re.compile(r"</?\s*untrusted[^>]*>", re.IGNORECASE)
# Zero-width and bidi control characters used to hide instructions.
_INVISIBLE = {"​", "‌", "‍", "⁠", "﻿", "‪", "‫", "‬",
              "‭", "‮", "⁦", "⁧", "⁨", "⁩"}


def sanitize(text: object, max_chars: int = MAX_FIELD_CHARS) -> str:
    """NFKC-normalise, drop control/invisible chars, collapse whitespace, cap length."""
    s = unicodedata.normalize("NFKC", "" if text is None else str(text))
    s = "".join(
        ch for ch in s
        if ch not in _INVISIBLE and (unicodedata.category(ch)[0] != "C" or ch in "\t\n")
    )
    s = re.sub(r"\s+", " ", s).strip()
    if len(s) > max_chars:
        s = s[:max_chars] + " [truncated]"
    return s


def wrap_untrusted(field: str, text: object) -> str:
    """Return `<untrusted field="...">...</untrusted>`; any forged tags inside are neutralised."""
    if not re.fullmatch(r"[a-z_]{1,40}", field):
        raise ValueError("field name must be lower_snake_case")
    body = _TAG_RE.sub("[tag removed]", sanitize(text))
    return f'<untrusted field="{field}">{body}</untrusted>'
