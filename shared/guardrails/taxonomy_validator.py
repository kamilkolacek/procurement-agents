"""Validate LLM labels against the taxonomy enum. Anything off-enum is rejected, never coerced."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

ESCAPE_CODE = "UNCLASSIFIED.REVIEW"


class TaxonomyError(ValueError):
    """The taxonomy file itself is malformed."""


@dataclass(frozen=True)
class Category:
    code: str
    l1: str
    name: str
    risk: str


@dataclass(frozen=True)
class LabelCheck:
    ok: bool
    code: str
    reason: str = ""
    category: Category | None = None


class Taxonomy:
    def __init__(self, data: dict[str, Any]) -> None:
        self.version = str(data.get("version") or "")
        if not self.version:
            raise TaxonomyError("taxonomy has no version")
        cats: dict[str, Category] = {}
        for l1 in data.get("categories") or []:
            l1_code = str(l1.get("l1") or "")
            if not l1_code:
                raise TaxonomyError("L1 entry without 'l1' code")
            for l2 in l1.get("l2") or []:
                code = str(l2.get("code") or "")
                if not code.startswith(l1_code + "."):
                    raise TaxonomyError(f"L2 code '{code}' does not start with '{l1_code}.'")
                if code in cats:
                    raise TaxonomyError(f"duplicate L2 code '{code}'")
                risk = str(l2.get("risk") or "")
                if risk not in {"low", "high"}:
                    raise TaxonomyError(f"L2 '{code}' risk must be low|high, got '{risk}'")
                if not l2.get("retired"):
                    cats[code] = Category(code, l1_code, str(l2.get("name") or code), risk)
        if ESCAPE_CODE not in cats:
            raise TaxonomyError(f"taxonomy must include {ESCAPE_CODE}")
        self.categories = cats

    @classmethod
    def from_yaml(cls, path: str | Path) -> Taxonomy:
        with Path(path).open(encoding="utf-8") as fh:
            return cls(yaml.safe_load(fh) or {})

    @property
    def codes(self) -> list[str]:
        return sorted(self.categories)

    def check(self, code: object) -> LabelCheck:
        if not isinstance(code, str):
            return LabelCheck(False, repr(code), "label is not a string")
        if code not in self.categories:  # exact match only: no case folding, no trimming
            return LabelCheck(False, code, "label not in taxonomy enum")
        return LabelCheck(True, code, category=self.categories[code])

    def is_high_risk(self, code: str) -> bool:
        cat = self.categories.get(code)
        return cat is None or cat.risk == "high"
