"""Richbond query set, organised by Pattern.

Pattern A (people-at-target):   scored against ``contacts`` ground truth.
Pattern B (company-discovery):  scored against ``companies`` ground truth.
Pattern C (find-similar):       scored against ``companies`` ground truth;
                                Exa-only — other backends are skipped.

Three queries per pattern give us English + French + a regional variant
where it makes sense — Richbond's home market is French-speaking, so
language coverage matters per vendor.
"""

from __future__ import annotations

from .base import Pattern, Query


RICHBOND_QUERIES: list[Query] = [
    # ---------------- Pattern A — people at known target ----------------
    Query(
        id="rb-A1",
        pattern=Pattern.PEOPLE_AT_TARGET,
        description="Broad role-based query for procurement leadership at Richbond (English).",
        text="Senior procurement decision-makers at Richbond Group Morocco",
        country="ma",
        language="en",
    ),
    Query(
        id="rb-A2",
        pattern=Pattern.PEOPLE_AT_TARGET,
        description="French-language variant — Richbond's home-market language.",
        text="Richbond Casablanca responsable des achats direction",
        country="ma",
        language="fr",
    ),
    Query(
        id="rb-A3",
        pattern=Pattern.PEOPLE_AT_TARGET,
        description="Broad leadership-team query in English.",
        text="Richbond Group leadership team executives",
        country="ma",
        language="en",
    ),

    # ---------------- Pattern B — discover target companies ----------------
    Query(
        id="rb-B1",
        pattern=Pattern.COMPANY_DISCOVERY,
        description="Market-mapping query for direct mattress competitors in Morocco (English).",
        text="Largest mattress manufacturers in Morocco",
        country="ma",
        language="en",
    ),
    Query(
        id="rb-B2",
        pattern=Pattern.COMPANY_DISCOVERY,
        description="French-language market-mapping query.",
        text="Plus grands fabricants de matelas et literie au Maroc",
        country="ma",
        language="fr",
    ),
    Query(
        id="rb-B3",
        pattern=Pattern.COMPANY_DISCOVERY,
        description="Regional sweep — broaden beyond Morocco to North Africa.",
        text="Hospitality furniture and bedding suppliers North Africa",
        country="ma",
        language="en",
    ),

    # ---------------- Pattern C — find similar (Exa-only) ----------------
    Query(
        id="rb-C1",
        pattern=Pattern.FIND_SIMILAR,
        description="Exa find_similar against Richbond's homepage — finds embedding-nearest peers.",
        url="https://www.richbond.com/",
    ),

    # ---------------- Pattern D — ICP-from-URL via LLM ----------------
    Query(
        id="rb-D1",
        pattern=Pattern.ICP_FROM_URL,
        description="LLM derives a brand-agnostic ICP for Richbond's mattress and bedding "
                    "business specifically (ignoring plastics / vegetable oils); the "
                    "derived description is fired through every SearchBackend.",
        url="https://www.grouperichbond.ma/fr/le-groupe",
        focus="mattress and bedding manufacturing (literie / mousse / matelas)",
        country="ma",
        language="fr",
    ),

    # ---------------- Pattern B expanded — North Africa scope ----------------
    Query(
        id="rb-B4",
        pattern=Pattern.COMPANY_DISCOVERY,
        description="Regional sweep — mattress and bedding manufacturers across North Africa, "
                    "not just Morocco. Tests whether Richbond surfaces as a regional peer.",
        text="Largest mattress and bedding manufacturers in North Africa Morocco Tunisia Algeria Egypt",
        language="en",
    ),

    # ---------------- Pattern D expanded — North Africa focus ----------------
    Query(
        id="rb-D2",
        pattern=Pattern.ICP_FROM_URL,
        description="Pattern D with broadened regional focus — does Richbond itself surface "
                    "when we describe a North-African mattress manufacturer brand-agnostically?",
        url="https://www.grouperichbond.ma/fr/le-groupe",
        focus="mattress and bedding manufacturing across North Africa (Morocco, Tunisia, Algeria, Egypt, Libya)",
        language="en",
    ),

    # ---------------- Pattern E — email finding ----------------
    Query(
        id="rb-E1",
        pattern=Pattern.EMAIL_FROM_NAME_COMPANY,
        description="Find email for Mohamed RAOUI at Richbond (ground-truth email: MRaoui@richbond.ma).",
        first_name="Mohamed",
        last_name="RAOUI",
        domain="richbond.ma",
        target_contact_ids=["rb-c001"],
    ),
]
