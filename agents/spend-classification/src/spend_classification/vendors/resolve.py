"""Stage 1: resolve raw vendor strings to vendor entities (rules, then fuzzy; no LLM yet).

Order: approved aliases -> ERP supplier ID -> cleaned-name rules -> fuzzy match. Anything not
clearly one vendor goes to the review queue as a proposal instead of being merged.
The LLM step for ambiguous clusters is deliberately absent: it waits for the Phase 3
injection filter. This module never reads the golden answer key.

Merge policy:
- Same ERP supplier ID is the same vendor (AP, PO).
- Two different ERP IDs merge automatically only when a name carries an explicit
  replacement marker such as "(NEW)" and the cleaned names are near-identical. Near-identical
  names without that cue become a POSSIBLE_DUPLICATE proposal: confusable vendors ("Solutions"
  vs "Services") look the same to any string metric, so a human decides.
- A P-card descriptor attaches to a vendor only on an exact key, an adjacent-letter typo, or (when
  it hit the 25-character descriptor cap) a prefix match with a unique candidate; otherwise it
  is an AMBIGUOUS_MATCH proposal and stays separate.
"""

from __future__ import annotations

import csv
from collections import defaultdict
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from pathlib import Path

from spend_classification.ingest import Line

from .clean import CleanName, clean_name, typo_equal

DUPLICATE_RATIO = 0.90  # cross-ERP-ID similarity needed even with a replacement marker
PROPOSE_RATIO = 0.85  # similarity at which a non-merge is still shown to a reviewer
MIN_PREFIX_CHARS = 8  # a truncated descriptor shorter than this is too weak to match on

AliasKey = tuple[str, str, str]  # (source, raw_name, erp_vendor_id)


@dataclass
class Entity:
    entity_id: str = ""
    erp_ids: set[str] = field(default_factory=set)
    keys: set[str] = field(default_factory=set)
    marker: bool = False
    aliases: dict[AliasKey, tuple[str, str]] = field(default_factory=dict)  # key -> (method, why)


@dataclass(frozen=True)
class ReviewItem:
    reason: str  # AMBIGUOUS_MATCH | POSSIBLE_DUPLICATE
    subject: str
    candidates: str
    evidence: str


@dataclass(frozen=True)
class Resolution:
    entities: list[Entity]
    alias_to_entity: dict[AliasKey, str]
    review: list[ReviewItem]
    lines_entity: dict[str, str]  # line_key -> entity_id


def _ratio(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


def load_approved_aliases(path: Path) -> dict[AliasKey, str]:
    """Human-approved aliases (data/labels/vendor_aliases.csv): exact lookup, always wins."""
    if not path.exists():
        return {}
    with path.open(newline="", encoding="utf-8") as fh:
        return {(r["source"], r["raw"], r.get("erp_vendor_id", "")): r["golden_id"]
                for r in csv.DictReader(fh) if r.get("approved_by")}


def _pcard_match(key: str, truncated: bool,
                 pool: list[Entity]) -> tuple[Entity | None, str, str]:
    """Return (entity, method, why); entity None means no match, why explains a near miss."""
    exact = [e for e in pool if key in e.keys]
    if len(exact) == 1:
        return exact[0], "rule", "exact cleaned name"
    if len(exact) > 1:
        return None, "review", "cleaned name equals several vendors"
    typo = [e for e in pool if any(typo_equal(key, k) for k in e.keys)]
    if len(typo) == 1:
        return typo[0], "rule", "adjacent-letter typo of a known name"
    if truncated and len(key) >= MIN_PREFIX_CHARS:
        pref = [e for e in pool if any(k.startswith(key) for k in e.keys)]
        if len(pref) == 1:
            return pref[0], "rule", "truncated descriptor (unique prefix)"
        if len(pref) > 1:
            return None, "review", "truncated descriptor fits several vendors"
    best = max(((max(_ratio(key, k) for k in e.keys), e) for e in pool), default=(0.0, None),
               key=lambda t: t[0])
    if best[1] is not None and best[0] >= PROPOSE_RATIO:
        return None, "review", f"closest vendor ratio {best[0]:.2f}"
    return None, "none", ""


def resolve(lines: list[Line], approved: dict[AliasKey, str] | None = None) -> Resolution:
    approved = approved or {}
    # 1. ERP-ID clusters from AP and PO.
    by_erp: dict[str, Entity] = {}
    pcard_keys: dict[str, set[str]] = defaultdict(set)  # cleaned key -> raw descriptors
    key_truncated: dict[str, bool] = {}  # prefix matching needs every raw to be capped
    cleaned: dict[AliasKey, CleanName] = {}
    for ln in lines:
        ak: AliasKey = (ln.source, ln.vendor_raw, ln.erp_vendor_id)
        if ak not in cleaned:
            cleaned[ak] = clean_name(ln.vendor_raw, ln.source)
        c = cleaned[ak]
        if ln.erp_vendor_id:
            e = by_erp.setdefault(ln.erp_vendor_id, Entity(erp_ids={ln.erp_vendor_id}))
            e.keys.add(c.key)
            e.marker |= c.replacement_marker
            e.aliases.setdefault(ak, ("rule", "same ERP supplier ID"))
        else:
            pcard_keys[c.key].add(ln.vendor_raw)
            key_truncated[c.key] = key_truncated.get(c.key, True) and c.truncated

    review: list[ReviewItem] = []
    entities = list(by_erp.values())

    # 2. Cross-ERP-ID duplicates: merge only on an explicit marker, otherwise propose.
    ids = sorted(by_erp)
    merged_into: dict[str, str] = {}
    for i, a in enumerate(ids):
        for b in ids[i + 1:]:
            ea, eb = by_erp[a], by_erp[b]
            ratio = max(_ratio(x, y) for x in ea.keys for y in eb.keys)
            if ratio < PROPOSE_RATIO:
                continue
            if ratio >= DUPLICATE_RATIO and (ea.marker != eb.marker):
                new, old = (b, a) if eb.marker else (a, b)
                merged_into[new] = old
            else:
                review.append(ReviewItem(
                    "POSSIBLE_DUPLICATE", f"{a} / {b}", f"{sorted(ea.keys)} | {sorted(eb.keys)}",
                    f"cleaned-name ratio {ratio:.2f}, no replacement marker: kept separate"))
    for new, old in merged_into.items():
        keep, drop = by_erp[old], by_erp[new]
        keep.erp_ids |= drop.erp_ids
        keep.keys |= drop.keys
        keep.aliases.update({k: ("rule", f"replacement marker, merged {new} into {old}")
                             for k in drop.aliases})
        entities.remove(drop)

    # 3. P-card descriptors, longest first so full names exist before truncated ones.
    for key in sorted(pcard_keys, key=lambda k: (-len(k), k)):
        ent, method, why = _pcard_match(key, key_truncated[key], entities)
        raws = sorted(pcard_keys[key])
        if ent is None:
            ent = Entity(keys={key})
            entities.append(ent)
            if method == "review":
                review.append(ReviewItem("AMBIGUOUS_MATCH", key, " | ".join(raws), why))
            how = ("review", why) if method == "review" else ("rule", "new card-only vendor")
        else:
            ent.keys.add(key)
            how = (method, why)
        for raw in raws:
            ent.aliases[("PCARD", raw, "")] = how

    # 4. Stable entity IDs and lookup tables.
    for n, e in enumerate(sorted(entities, key=lambda e: sorted(e.keys)[0]), start=1):
        e.entity_id = f"V{n:04d}"
    alias_to_entity: dict[AliasKey, str] = {}
    for e in entities:
        for ak in e.aliases:
            alias_to_entity[ak] = e.entity_id
    for ak, vid in approved.items():  # approved aliases win over everything above
        if ak in alias_to_entity:
            alias_to_entity[ak] = vid
    lines_entity = {ln.line_key: alias_to_entity[(ln.source, ln.vendor_raw, ln.erp_vendor_id)]
                    for ln in lines}
    return Resolution(entities, alias_to_entity, review, lines_entity)
