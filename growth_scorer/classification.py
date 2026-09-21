from __future__ import annotations

from dataclasses import dataclass
import re

from .models import InputSnapshot, ScorecardName


@dataclass(frozen=True)
class Classification:
    scorecard: ScorecardName
    confidence: str
    reason: str


SPECIALIST_TERMS = {
    "insurer": (
        "insurance", "reinsurance", "life insurance", "property casualty", "insurance brokers",
    ),
    "bank": (
        "banks diversified", "banks regional", "banking services", "mortgage finance",
        "savings cooperative", "commercial bank", "regional bank", "money center bank",
    ),
    "semiconductor": (
        "semiconductor", "semiconductors", "semiconductor equipment materials", "chip foundry",
    ),
}

MEMORY_TERMS = (
    "dram", "dynamic random access memory", "hbm", "high bandwidth memory", "nand",
    "memory chip", "memory semiconductor", "flash memory",
)

INDUSTRY_ROUTES: dict[ScorecardName, tuple[str, ...]] = {
    "oil_gas": ("oil gas", "energy", "uranium", "coal", "coking coal", "oilfield services"),
    "utilities_renewables": (
        "utilities", "regulated electric", "regulated gas", "regulated water", "renewable utilities",
        "independent power", "solar",
    ),
    "materials_mining": (
        "steel", "copper", "gold", "silver", "aluminum", "mining", "metals", "chemicals",
        "specialty chemicals", "agricultural inputs", "building materials", "paper", "lumber",
    ),
    "pharmaceuticals": ("drug manufacturers", "pharmaceutical", "diagnostics research"),
    "medical_devices": (
        "medical devices", "medical instruments", "medical laboratories", "medical distribution", "dental",
    ),
    "healthcare": ("healthcare plans", "health information", "medical care facilities", "healthcare services"),
    "payments_fintech": ("credit services", "payment", "fintech", "financial data", "financial exchanges"),
    "asset_management": (
        "asset management", "capital markets", "broker", "investment banking", "wealth management",
        "mortgage real estate investment trust",
    ),
    "aerospace_defense": ("aerospace defense",),
    "transportation_logistics": (
        "airlines", "airports air services", "railroads", "trucking", "marine shipping",
        "integrated freight", "logistics",
    ),
    "automotive": ("auto manufacturers", "auto parts"),
    "capital_goods": (
        "farm heavy construction machinery", "specialty industrial machinery", "industrial distribution",
        "engineering construction", "infrastructure operations", "building products equipment",
        "rental leasing", "tools accessories", "electrical equipment supplies",
        "pollution treatment controls", "waste management", "security protection services",
    ),
    "consumer_staples": (
        "grocery stores", "household personal products", "packaged foods", "beverages", "tobacco",
    ),
    "retail_discretionary": (
        "retail", "apparel", "footwear", "luxury goods", "restaurants", "discount stores",
        "department stores", "internet retail", "consumer electronics", "residential construction",
        "furnishings", "lodging", "travel services", "resorts casinos", "leisure",
    ),
    "media_education": (
        "entertainment", "broadcasting", "publishing", "advertising agencies", "education training",
        "internet content information",
    ),
    "software_cloud": (
        "software application", "software infrastructure", "information technology services",
        "data center", "cloud computing", "cybersecurity",
    ),
    "hardware_telecom": (
        "computer hardware", "electronic components", "communication equipment", "telecom services",
        "scientific technical instruments", "business equipment supplies",
    ),
}

SECTOR_FALLBACKS: dict[str, ScorecardName] = {
    "technology": "technology",
    "communication services": "technology",
    "healthcare": "healthcare",
    "financial services": "financial_platform",
    "industrials": "industrial",
    "consumer cyclical": "consumer",
    "consumer defensive": "consumer",
    "energy": "energy_materials",
    "basic materials": "energy_materials",
    "utilities": "energy_materials",
}


def _normalized(*values: str | None) -> str:
    return " ".join(
        re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()
        for value in values
        if value
    )


def _first_match(text: str, terms: tuple[str, ...]) -> str | None:
    normalized_terms = sorted(
        ((term, _normalized(term)) for term in terms), key=lambda item: len(item[1]), reverse=True
    )
    return next((original for original, normalized in normalized_terms if normalized in text), None)


def detect_classification(snapshot: InputSnapshot, requested: str = "auto") -> Classification:
    valid = {
        "general", "technology", "healthcare", "financial_platform", "industrial", "consumer",
        "energy_materials", "bank", "insurer", "biotech", "semiconductor", "memory_semiconductor",
        "software_cloud", "hardware_telecom", "pharmaceuticals", "medical_devices",
        "payments_fintech", "asset_management", "aerospace_defense", "transportation_logistics",
        "automotive", "capital_goods", "consumer_staples", "retail_discretionary",
        "media_education", "oil_gas", "utilities_renewables", "materials_mining",
    }
    if requested != "auto":
        if requested not in valid:
            raise ValueError(f"Unknown scorecard: {requested}")
        return Classification(requested, "manual", f"Analyst selected the {requested} scorecard")  # type: ignore[arg-type]

    industry_text = _normalized(snapshot.industry_key, snapshot.industry)
    sector_text = _normalized(snapshot.sector_key, snapshot.sector)
    summary_text = _normalized(snapshot.business_summary)
    profile_text = _normalized(industry_text, sector_text, summary_text)

    insurer_term = _first_match(industry_text, SPECIALIST_TERMS["insurer"])
    if insurer_term:
        return Classification("insurer", "high", f"Yahoo industry matched insurer term '{insurer_term}'")

    bank_term = _first_match(industry_text, SPECIALIST_TERMS["bank"])
    if bank_term:
        return Classification("bank", "high", f"Yahoo industry matched bank term '{bank_term}'")

    semiconductor_term = _first_match(industry_text, SPECIALIST_TERMS["semiconductor"])
    memory_term = _first_match(profile_text, MEMORY_TERMS)
    if semiconductor_term and memory_term:
        source = "industry and company description" if memory_term in summary_text else "industry"
        return Classification(
            "memory_semiconductor", "high",
            f"Yahoo {source} identified semiconductor operations and memory term '{memory_term}'",
        )
    if semiconductor_term:
        return Classification(
            "semiconductor", "high", f"Yahoo industry matched semiconductor term '{semiconductor_term}'",
        )

    biotech_term = _first_match(industry_text, ("biotechnology", "biotech"))
    pre_profit = (snapshot.metrics.get("operating_income", 0) or 0) < 0 or (
        snapshot.metrics.get("free_cash_flow", 0) or 0
    ) < 0
    if biotech_term and pre_profit:
        return Classification(
            "biotech", "high",
            f"Yahoo industry matched '{biotech_term}' and operating income or free cash flow is negative",
        )
    if biotech_term:
        return Classification(
            "healthcare", "high", f"Yahoo industry matched profitable biotechnology term '{biotech_term}'",
        )

    for scorecard, terms in INDUSTRY_ROUTES.items():
        match = _first_match(industry_text, terms)
        if match:
            return Classification(
                scorecard, "high", f"Yahoo industry matched {scorecard} term '{match}'",
            )

    for scorecard, terms in INDUSTRY_ROUTES.items():
        match = _first_match(summary_text, terms)
        if match:
            return Classification(
                scorecard, "medium", f"Company description matched {scorecard} term '{match}'",
            )

    for sector_name, scorecard in SECTOR_FALLBACKS.items():
        if _normalized(sector_name) in sector_text:
            return Classification(
                scorecard, "sector fallback", f"No detailed industry rule matched; Yahoo sector is '{snapshot.sector}'",
            )

    return Classification(
        "general", "fallback",
        "Yahoo industry and company description did not match a specialist or sector scorecard",
    )
