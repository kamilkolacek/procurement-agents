"""Fictional vendor universe with messy name variants per source.

Each golden vendor has one canonical name, one or more ERP supplier IDs (AP/PO), a few ERP
name variants (case, punctuation, suffix, abbreviation, typo), and card-descriptor variants for
P-card lines (processor prefixes, truncation, store numbers).
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

PREFIXES = (
    "Apex",
    "Blue Harbor",
    "Cedar Ridge",
    "Summit",
    "Ironclad",
    "Brightline",
    "Granite",
    "Keystone",
    "Lakeshore",
    "Northfield",
    "Oakmont",
    "Pinecrest",
    "Redwood",
    "Silverline",
    "Stonebridge",
    "Trident",
    "Westbrook",
    "Clearwater",
    "Evergreen",
    "Falcon",
    "Golden Gate",
    "Harborview",
    "Juniper",
    "Lighthouse",
    "Maple Leaf",
    "Meridian",
    "Northstar",
    "Orchard",
    "Pioneer",
    "Prairie",
    "Quarry",
    "Riverbend",
    "Sagebrush",
    "Sterling",
    "Tidewater",
    "Union Square",
    "Vantage",
    "Willow Creek",
    "Copperfield",
    "Driftwood",
    "Elmhurst",
    "Foxglove",
    "Highpoint",
    "Ivory Coast",
    "Kingsley",
    "Larkspur",
    "Moraine",
    "Nimbus",
    "Obsidian",
    "Palisade",
    "Quill",
    "Ravenwood",
    "Saltbox",
    "Thornbury",
    "Upland",
    "Verdant",
    "Wexford",
    "Yellowstone",
    "Zephyr",
    "Alder",
    "Bramble",
    "Cobalt",
    "Delta Bay",
    "Ember",
    "Fairhaven",
    "Glacier",
    "Hollis",
    "Inkwell",
    "Jasper",
    "Kestrel",
    "Linden",
    "Marlow",
    "Nautilus",
    "Oriel",
    "Peregrine",
    "Quayside",
    "Rook",
    "Sable",
    "Tamarack",
    "Ursa",
    "Vesper",
    "Whitlock",
    "Yardley",
    "Zenith",
    "Arbor",
    "Beacon",
    "Crescent",
    "Dunmore",
    "Easton",
    "Fenwick",
    "Gilded",
    "Halcyon",
)
SURNAMES = (
    "Hartwell",
    "Pryce",
    "Okafor",
    "Lindqvist",
    "Moreno",
    "Castellanos",
    "Whitaker",
    "Nakamura",
    "Brennan",
    "Delacroix",
    "Ferreira",
    "Gallagher",
    "Haddad",
    "Iverson",
    "Jablonski",
    "Kowalczyk",
    "Lachance",
    "Mbeki",
    "Novak",
    "Osei",
    "Petrov",
    "Quintero",
    "Rasmussen",
    "Sorensen",
    "Takahashi",
    "Underwood",
    "Vasquez",
    "Wainwright",
    "Yilmaz",
    "Zielinski",
)
FIRST_NAMES = (
    "Avery",
    "Jordan",
    "Riley",
    "Morgan",
    "Casey",
    "Taylor",
    "Jamie",
    "Quinn",
    "Rowan",
    "Sasha",
    "Dakota",
    "Emerson",
    "Finley",
    "Hayden",
    "Kendall",
    "Logan",
    "Parker",
    "Reese",
    "Skyler",
    "Drew",
)

DOMAINS: dict[str, tuple[str, ...]] = {
    "IT.SAAS": ("Software", "Cloud Apps", "Labs", "Systems", "Analytics", "Digital"),
    "IT.CLOUD": ("Cloud", "Hosting", "Compute"),
    "IT.HARDWARE": ("Technology Supply", "Computer Supply", "Tech Distributors"),
    "IT.TELECOM": ("Telecom", "Communications", "Wireless", "Networks"),
    "IT.SERVICES": ("IT Solutions", "Tech Services", "Managed IT"),
    "IT.SECURITY": ("Security Labs", "Cyber Defense", "SecureOps"),
    "PROF.LEGAL": ("@law",),
    "PROF.CONSULT": ("Advisors", "Consulting Group", "Partners"),
    "PROF.AUDIT": ("@cpa",),
    "PROF.CONTRACT_LABOR": ("Staffing", "Talent", "Workforce Solutions"),
    "PROF.RECRUIT": ("Recruiting", "Search Partners", "Talent Search"),
    "MKT.ADS": ("Media", "Ad Network", "Advertising"),
    "MKT.AGENCY": ("Creative", "Agency", "Brand Studio"),
    "MKT.EVENTS": ("Events", "Expo Services", "Promotions"),
    "MKT.PRINT": ("Printing", "Print & Graphics", "Press"),
    "FAC.RENT": ("Properties", "Realty", "Real Estate Holdings"),
    "FAC.UTIL": ("Power & Light", "Water Utility", "Energy", "Waste Services"),
    "FAC.CLEAN": ("Cleaning Services", "Janitorial", "Facility Care"),
    "FAC.MAINT": ("Mechanical", "Building Services", "HVAC", "Plumbing"),
    "FAC.SECURITY": ("Security Services", "Protective Services", "Alarm"),
    "OFF.SUPPLIES": ("Office Supply", "Office Products", "Stationers"),
    "OFF.FURNITURE": ("Furniture", "Interiors", "Workspace"),
    "OFF.KITCHEN": ("Coffee Service", "Refreshments", "Pantry"),
    "TRV.AIR": ("Airlines", "Air", "Airways"),
    "TRV.LODGING": ("Hotel", "Inn & Suites", "Resort", "Lodge"),
    "TRV.GROUND": ("Taxi", "Car Rental", "Rides", "Parking", "Rail"),
    "TRV.MEALS": ("@food",),
    "LOG.FREIGHT": ("Freight", "Trucking", "Transport", "Logistics"),
    "LOG.COURIER": ("Courier", "Express", "Parcel"),
    "LOG.WAREHOUSE": ("Warehousing", "Distribution Center", "Fulfillment"),
    "LOG.PACKAGING": ("Packaging", "Container", "Box"),
    "LOG.FLEET": ("Fleet Services", "Auto Leasing", "Fleet"),
    "DIR.RAW_MATERIALS": ("Polymers", "Metals", "Steel", "Plastics", "Alloys"),
    "DIR.COMPONENTS": ("Components", "Fasteners", "Bearing", "Electronics", "Motion"),
    "DIR.MRO": ("Industrial Supply", "Safety Supply", "Tool & Supply"),
    "FIN.INSURANCE": ("Insurance", "Mutual", "Assurance"),
    "FIN.BANK_FEES": ("Bank", "Payments", "Merchant Services"),
    "FIN.DONATIONS": ("Foundation", "Community Fund", "Charities"),
    "HR.BENEFITS": ("Benefits", "Benefit Administrators", "Wellness"),
    "HR.TRAINING": ("Academy", "Learning", "Training Institute"),
}
FOOD = ("Grill", "Bistro", "Kitchen", "Cafe", "Catering", "Tavern", "Noodle Bar", "Deli")
SUFFIXES = ("Inc", "LLC", "Co", "Corp", "Ltd", "Group", "")
SUFFIX_VARIANTS = {
    "Inc": ("Inc.", ", Inc.", "INC", "Incorporated", ""),
    "LLC": ("L.L.C.", ", LLC", "llc", ""),
    "Co": ("Co.", "Company", "& Co", ""),
    "Corp": ("Corp.", "Corporation", "CORP", ""),
    "Ltd": ("Ltd.", "Limited", ""),
    "Group": ("Grp", "Group Inc", ""),
    "LLP": ("L.L.P.", ", LLP", ""),
    "": ("",),
}
ABBREV = (
    ("Services", "Svcs"),
    ("Solutions", "Soln"),
    ("Technology", "Tech"),
    ("International", "Intl"),
    ("Logistics", "Logist."),
    ("Supply", "Sply"),
    ("Consulting", "Consult."),
    ("Management", "Mgmt"),
    ("Communications", "Comms"),
)
PROCESSORS = ("SQ *", "TST* ", "PAYPAL *", "SP * ", "")
STATES = ("IL", "TX", "CO", "MA", "WA", "GA", "AZ", "NJ", "OH", "NC", "OR")


@dataclass
class Vendor:
    golden_id: str
    canonical: str
    l2: str
    suffix: str
    erp_ids: list[str] = field(default_factory=list)
    erp_names: list[str] = field(default_factory=list)  # name variants for erp_ids[0]
    alt_erp_names: list[str] = field(default_factory=list)  # for erp_ids[1] (duplicate record)
    card_names: list[str] = field(default_factory=list)
    kind: str = "standard"  # standard | tail | multi | confusable | related
    related_to: str = ""
    skus: dict[str, tuple[str, object]] = field(default_factory=dict)  # code -> (name, price)

    @property
    def base(self) -> str:
        return self.canonical[: -len(self.suffix)].strip() if self.suffix else self.canonical


def _typo(rng: random.Random, s: str) -> str:
    words = s.split()
    idx = [i for i, w in enumerate(words) if len(w) > 4]
    if not idx:
        return s
    i = rng.choice(idx)
    w = words[i]
    j = rng.randrange(1, len(w) - 2)
    words[i] = w[:j] + w[j + 1] + w[j] + w[j + 2 :]
    return " ".join(words)


def erp_variants(rng: random.Random, v: Vendor, k: int) -> list[str]:
    """Primary ERP name first, then up to k-1 messy variants (deduplicated, stable order)."""
    out = [v.canonical]
    pool = []
    for sv in SUFFIX_VARIANTS.get(v.suffix, ("",)):
        name = (v.base + (sv if sv.startswith(",") else (" " + sv if sv else ""))).strip()
        pool.append(name)
    pool.append(v.canonical.upper())
    abbr = v.canonical
    for a, b in ABBREV:
        abbr = abbr.replace(a, b)
    if abbr != v.canonical:
        pool.append(abbr)
    pool.append(_typo(rng, v.canonical))
    pool.append(v.canonical.upper() + " - REMIT")
    rng.shuffle(pool)
    for name in pool:
        if len(out) >= k:
            break
        if name not in out:
            out.append(name)
    return out


def card_variants(rng: random.Random, v: Vendor, k: int) -> list[str]:
    """Card statement descriptors: upper case, processor prefix, store number, truncation."""
    out: list[str] = []
    attempts = 0
    while len(out) < k and attempts < 20:
        attempts += 1
        base = v.base.upper().replace("&", "AND").replace(",", "")
        prefix = rng.choice(PROCESSORS)
        style = rng.randrange(3)
        if style == 0:
            s = f"{prefix}{base}"
        elif style == 1:
            s = f"{prefix}{base} #{rng.randrange(100, 9999)}"
        else:
            s = f"{prefix}{base} {rng.choice(STATES)}"
        s = s[:25].rstrip()
        if s not in out:
            out.append(s)
    return out


class VendorFactory:
    def __init__(self, rng: random.Random) -> None:
        self.rng = rng
        self.used: set[str] = set()
        self.vendors: list[Vendor] = []
        self._next_erp = rng.randrange(10000, 20000)

    def _new_gid(self) -> str:
        return f"GV{len(self.vendors) + 1:04d}"

    def new_erp_id(self) -> str:
        self._next_erp += self.rng.randrange(3, 40)
        return f"S{self._next_erp:05d}"

    def _name(self, l2: str) -> tuple[str, str]:
        rng = self.rng
        dom = DOMAINS[l2]
        for _ in range(200):
            d = rng.choice(dom)
            if d == "@law":
                a, b = rng.sample(SURNAMES, 2)
                core, suffix = rng.choice(((f"{a} & {b}", "LLP"), (f"{a} {b} Law Group", "LLP")))
            elif d == "@cpa":
                a, b = rng.sample(SURNAMES, 2)
                core, suffix = rng.choice(((f"{a} {b} CPAs", "LLP"), (f"{a} & Co Accountants", "")))
            elif d == "@food":
                core, suffix = f"{rng.choice(PREFIXES)} {rng.choice(FOOD)}", rng.choice(("", "LLC"))
            else:
                core, suffix = f"{rng.choice(PREFIXES)} {d}", rng.choice(SUFFIXES)
            name = f"{core} {suffix}".strip()
            if core not in self.used:
                self.used.add(core)
                return name, suffix
        raise RuntimeError(f"could not generate a unique vendor name for {l2}")

    def add(
        self,
        l2: str,
        kind: str = "standard",
        name: tuple[str, str] | None = None,
        n_erp_names: int | None = None,
    ) -> Vendor:
        canonical, suffix = name or self._name(l2)
        self.used.add(canonical[: -len(suffix)].strip() if suffix else canonical)
        v = Vendor(self._new_gid(), canonical, l2, suffix, kind=kind)
        v.erp_ids = [self.new_erp_id()]
        k = n_erp_names if n_erp_names is not None else self.rng.choice((1, 2, 2, 3, 3, 4))
        v.erp_names = erp_variants(self.rng, v, k)
        v.card_names = card_variants(self.rng, v, self.rng.choice((1, 2, 3)))
        self.vendors.append(v)
        return v

    def confusable_of(self, v: Vendor) -> Vendor:
        """A distinct vendor whose name differs from `v` by one word (must NOT be merged)."""
        swaps = {
            "Services": "Solutions",
            "Group": "Partners",
            "Supply": "Source",
            "Logistics": "Logistix",
            "Systems": "Systemworks",
        }
        base = v.base
        for a, b in swaps.items():
            if a in base:
                new_base = base.replace(a, b)
                break
        else:
            new_base = base + " West"
        suffix = "LLC" if v.suffix != "LLC" else "Inc"
        return self.add(v.l2, kind="confusable", name=(f"{new_base} {suffix}", suffix))

    def related_of(self, v: Vendor, l2: str, word: str) -> Vendor:
        """A subsidiary-style vendor sharing the parent's first word (related, not the same)."""
        first = v.base.split()[0]
        r = self.add(l2, kind="related", name=(f"{first} {word} Inc", "Inc"))
        r.related_to, v.related_to = v.golden_id, r.golden_id
        return r


def person_names(rng: random.Random, n: int) -> list[str]:
    names: list[str] = []
    while len(names) < n:
        s = f"{rng.choice(FIRST_NAMES)} {rng.choice(SURNAMES)}"
        if s not in names:
            names.append(s)
    return names
