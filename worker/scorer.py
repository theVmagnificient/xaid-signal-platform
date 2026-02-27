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

# --- News: AI/PACS adoption signals ---
NEWS_KEYWORDS = {
    "ai_adoption": {
        "score": 9,
        "subtype": "ai_adoption",
        "keywords": [
            # Radiology AI vendors
            "aidoc", "gleamer", "nuance powerscribe", "viz.ai", "rapid ai",
            "rad ai", "zebra medical", "bayer calantic",
            # Radiology-specific AI terms
            "ai-assisted reading", "ai radiology",
            "artificial intelligence radiology", "machine learning radiology",
        ],
    },
    "pacs_upgrade": {
        "score": 8,
        "subtype": "pacs_upgrade",
        "keywords": [
            "sectra", "ge healthc", "fujifilm pacs", "agfa pacs",
            "cloud pacs", "cloud-based pacs", "pacs migration",
            "new pacs", "pacs upgrade", "pacs implementation",
            "vendor neutral archive", "vna",
        ],
    },
    "tech_adoption": {
        "score": 6,
        "subtype": "tech_adoption",
        "keywords": [
            "opens new imaging center", "expands radiology",
            "acquires imaging", "acquires radiology",
        ],
    },
    "funding": {
        "score": 8,
        "subtype": "funding",
        "keywords": [
            "series a", "series b", "series c",
            "raises $", "secures funding", "funding round",
            "venture capital", "secures investment", "raises funding",
        ],
    },
    "pe_acquisition": {
        "score": 9,
        "subtype": "pe_acquisition",
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
        "keywords": [
            "radiology backlog", "imaging backlog", "scan backlog",
            "reading backlog", "radiologist shortage",
            "radiology staffing shortage", "imaging wait times",
            "radiology staffing crisis", "radiology wait times",
        ],
    },
    "rsna_acr": {
        "score": 6,
        "subtype": "rsna_acr",
        "keywords": [
            "rsna 2024", "rsna 2025", "rsna annual meeting",
            "acr annual", "radiological society of north america",
            "american college of radiology annual",
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
    t = (title + " " + description).lower()
    best_score, best_subtype = 0, ""
    for category, cat_data in NEWS_KEYWORDS.items():
        for kw in cat_data["keywords"]:
            if kw in t:
                if cat_data["score"] > best_score:
                    best_score = cat_data["score"]
                    best_subtype = cat_data["subtype"]
    return best_score, best_subtype
