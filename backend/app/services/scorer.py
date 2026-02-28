"""
Signal scoring rules based on radiology domain research.
Scores are 1-10 (higher = more urgent to reach out).
"""

# --- Job Change: C-level / leadership titles ---
JOB_CHANGE_TIERS = {
    # Tier 1 — direct decision-makers for AI purchasing (score 9-10)
    "tier1": {
        "score": 10,
        "subtype": "tier1_clevel",
        "titles": [
            "head of radiology",
            "chief of radiology",
            "radiology chair",
            "chair of radiology",
            "chief medical officer",
            "cmo",
            "chief technology officer",
            "cto",
            "chief operations officer",
            "coo",
            "vp of radiology",
            "vp radiology",
            "vice president of radiology",
            "medical director of radiology",
            "director of radiology",
            "vp of clinical operations",
            "vp clinical operations",
            "vice president clinical operations",
        ],
    },
    # Tier 2 — influencers / secondary decision-makers (score 6-7)
    "tier2": {
        "score": 7,
        "subtype": "tier2_secondary",
        "titles": [
            "chief executive officer",
            "ceo",
            "chief financial officer",
            "cfo",
            "president",
            "practice manager",
            "director of operations",
            "it director",
            "chief information officer",
            "cio",
            "vp of quality",
            "director of imaging",
            "imaging director",
        ],
    },
    # Tier 3 — worth noting but lower priority (score 4)
    "tier3": {
        "score": 4,
        "subtype": "tier3_other",
        "titles": [
            "radiologist",
            "senior radiologist",
            "lead radiologist",
            "attending radiologist",
        ],
    },
}

# --- Job Postings: radiologist titles indicating CT expansion ---
JOB_POSTING_TIERS = {
    "tier1": {
        "score": 10,
        "subtype": "ct_radiologist_tier1",
        "keywords": [
            "body radiologist",
            "ct radiologist",
            "cross-sectional",
            "cross sectional",
            "abdominal radiologist",
            "abdominal imaging",
            "body imaging",
            "chest radiologist",
        ],
    },
    "tier2": {
        "score": 7,
        "subtype": "ct_radiologist_tier2",
        "keywords": [
            "diagnostic radiologist",
            "general radiologist",
            "staff radiologist",
            "teleradiologist",
            "teleradiology physician",
            "emergency radiologist",
            "radiology physician",
        ],
    },
}

# Titles to EXCLUDE from job posting signals (wrong specialty)
JOB_POSTING_EXCLUSIONS = [
    "interventional radiologist",
    "radiation oncologist",
    "nuclear medicine",
    "ultrasound",
    "mammograph",
    "breast imaging",
    "musculoskeletal",
    "msk radiolog",
    "ct technologist",
    "radiologic technologist",
    "radiology technician",
    "mri technologist",
]

# Names of AI vendors / competitors — articles primarily about these are NOT leads.
# Used to filter out vendor news in score_news().
COMPETITOR_NAMES = [
    "aidoc", "gleamer", "viz.ai", "rapid ai", "zebra medical",
    "bayer calantic", "nuance powerscribe", "powerscribe", "rad ai",
    "nanox", "avicenna", "qure.ai", "lunit", "oxipit", "intelerad",
    "change healthcare", "olive ai", "enlitic", "behold.ai",
    # Additional AI/tech vendors that are not buyer targets
    "vista ai", "sirona medical", "harrison.ai", "prenuvo",
    "core sound", "vital ai", "deepnoid", "augmedix",
]

# --- News: AI/PACS adoption signals ---
#
# context_required: if set, at least one word must appear in title+description
# for the signal to be scored. Guards against generic matches (e.g. "deploys AI"
# for call centers, "funding" for unrelated startups).
#
NEWS_KEYWORDS = {
    "ai_adoption": {
        "score": 9,
        "subtype": "ai_adoption",
        # Must be about radiology / diagnostic imaging — not AI in general
        "context_required": [
            "radiology", "radiologist", "imaging", "diagnostic",
            "ct scan", "mri", "x-ray", "reads", "scan",
        ],
        "keywords": [
            # Org adopting / implementing AI — buyer intent phrases
            "implements ai", "implementing ai",
            "adopts ai", "adopting ai",
            "deploys ai", "deploying ai",
            "launches ai",
            "using ai to", "hospitals using ai", "health system using ai",
            # AI-assisted / AI-powered reads
            "ai-assisted read", "ai-powered read", "ai-powered workflow",
            "ai-powered imaging", "ai-powered radiology",
            # Radiology-specific (vendor-neutral)
            "artificial intelligence radiology", "machine learning radiology",
            "ai diagnostic imaging", "ai radiology solution", "ai radiology platform",
        ],
    },
    "pacs_upgrade": {
        "score": 8,
        "subtype": "pacs_upgrade",
        # Vendor names removed — too broad. Only deployment-action keywords remain.
        # These already imply radiology context, so no extra context_required needed.
        "context_required": None,
        "keywords": [
            "cloud pacs", "cloud-based pacs", "pacs migration",
            "new pacs", "pacs upgrade", "pacs implementation",
            "implements pacs", "deploys pacs",
            "vendor neutral archive", "vna implementation",
        ],
    },
    "tech_adoption": {
        "score": 6,
        "subtype": "tech_adoption",
        "context_required": None,  # keywords already radiology-specific
        "keywords": [
            "opens new imaging center", "expands radiology",
            "acquires imaging", "acquires radiology",
            "expands imaging", "new imaging center", "opens imaging",
        ],
    },
    "funding": {
        "score": 8,
        "subtype": "funding",
        # Must be a hospital / imaging org getting funded — not an AI startup
        "context_required": [
            "hospital", "health system", "imaging center", "radiology group",
            "outpatient", "teleradiology", "medical center",
            "healthcare system", "physician group", "imaging network",
            "radiology practice", "imaging practice",
        ],
        "keywords": [
            "series a", "series b", "series c",
            "raises $", "secures funding", "funding round",
            "venture capital", "secures investment", "raises funding",
        ],
    },
    "pe_acquisition": {
        "score": 9,
        "subtype": "pe_acquisition",
        # Must be about a radiology / imaging org — not general healthcare PE
        "context_required": [
            "radiology", "imaging center", "imaging group", "imaging network",
            "radiology group", "radiology practice", "teleradiology",
            "diagnostic imaging", "outpatient imaging",
        ],
        "keywords": [
            "private equity", "pe-backed", "pe firm",
            "recapitalization", "management buyout",
            "equity firm", "portfolio company",
            "private equity firm", "pe investment",
        ],
    },
    "backlog": {
        "score": 10,
        "subtype": "backlog",
        "context_required": None,  # keywords already radiology-specific
        "keywords": [
            "radiology backlog", "imaging backlog", "scan backlog",
            "reading backlog", "radiologist shortage",
            "radiology staffing shortage", "imaging wait times",
            "radiology staffing crisis", "radiology wait times",
        ],
    },
}


def score_job_change(title: str) -> tuple[int, str]:
    """Return (score, subtype) for a job title. 0 = not relevant."""
    t = title.lower()
    for tier_name, tier in JOB_CHANGE_TIERS.items():
        for kw in tier["titles"]:
            if kw in t:
                return tier["score"], tier["subtype"]
    return 0, ""


def score_job_posting(title: str, description: str = "") -> tuple[int, str]:
    """Return (score, subtype) for a job posting. 0 = not relevant."""
    t = (title + " " + description).lower()

    # Check exclusions first
    for excl in JOB_POSTING_EXCLUSIONS:
        if excl in t:
            return 0, ""

    for tier_name, tier in JOB_POSTING_TIERS.items():
        for kw in tier["keywords"]:
            if kw in t:
                return tier["score"], tier["subtype"]
    return 0, ""


# --- Adjacent specialties: track as weak signals for future pipeline expansion ---
ADJACENT_TIERS = {
    "adjacent_ir": {
        "score": 4,
        "subtype": "adjacent_ir",
        "keywords": ["interventional radiologist", "musculoskeletal", "msk radiolog", "neuroradiologist", "neuro radiologist"],
    },
    "adjacent_oncology": {
        "score": 3,
        "subtype": "adjacent_oncology",
        "keywords": ["radiation oncologist"],
    },
    "adjacent_imaging": {
        "score": 3,
        "subtype": "adjacent_imaging",
        "keywords": ["nuclear medicine", "ultrasound", "mammograph", "breast imaging"],
    },
    "adjacent_tech": {
        "score": 3,
        "subtype": "adjacent_tech",
        "keywords": ["ct technologist", "radiologic technologist", "radiology technician", "mri technologist"],
    },
}


def score_adjacent_posting(title: str, description: str = "") -> tuple[int, str]:
    """Return (score, subtype) for adjacent specialty job postings. 0 = not relevant."""
    t = (title + " " + description).lower()
    for tier in ADJACENT_TIERS.values():
        for kw in tier["keywords"]:
            if kw in t:
                return tier["score"], tier["subtype"]
    return 0, ""


def score_news(title: str, description: str = "") -> tuple[int, str]:
    """Return (score, subtype) for a news item. 0 = not relevant."""
    # If the headline is primarily about a competitor/vendor, skip.
    title_lower = title.lower()
    for competitor in COMPETITOR_NAMES:
        if competitor in title_lower:
            return 0, ""

    t = (title + " " + description).lower()
    best_score, best_subtype = 0, ""
    for cat_data in NEWS_KEYWORDS.values():
        for kw in cat_data["keywords"]:
            if kw not in t:
                continue
            # Enforce context_required: at least one context word must appear
            ctx = cat_data.get("context_required")
            if ctx and not any(c in t for c in ctx):
                continue
            if cat_data["score"] > best_score:
                best_score = cat_data["score"]
                best_subtype = cat_data["subtype"]
    return best_score, best_subtype
