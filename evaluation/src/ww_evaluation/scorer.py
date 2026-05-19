"""Scorer — pattern-aware recall against ground truth.

Pattern A (people-at-target)   → scored against ``contacts`` ground truth.
Patterns B and C (company set) → scored against ``companies`` ground truth.

The headline metric per (backend, pattern) is recall: of the known-correct
targets, how many did the backend surface anywhere across the pattern's
query set? Per-query attribution and precision can be added later without
re-running the API calls — raw responses are preserved on disk.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

import yaml

from .queries.base import Pattern, Query


# ---------------- Ground truth ----------------


@dataclass(slots=True)
class Contact:
    id: str
    name: str
    title: str | None = None
    email: str | None = None
    linkedin: str | None = None
    confidence: str = "confirmed"
    # tier: 'target' = useful for outreach; 'directory' = real employee but not a
    # decision-maker for this campaign; 'noise' = misattribution / left / deceased.
    tier: str = "target"
    # status: 'active' = currently employed; 'left' = no longer with the company;
    # 'deceased' = dead; 'incorrect' = name not associated with company.
    status: str = "active"


@dataclass(slots=True)
class Company:
    id: str
    name: str
    aliases: list[str] = field(default_factory=list)
    domain: str | None = None
    country: str | None = None
    confidence: str = "confirmed"


@dataclass(slots=True)
class GroundTruth:
    contacts: list[Contact]
    companies: list[Company]


def load_ground_truth(path: Path) -> GroundTruth:
    data = yaml.safe_load(path.read_text()) or {}
    contacts = [
        Contact(
            id=entry["id"],
            name=entry["name"],
            title=entry.get("title"),
            email=entry.get("email"),
            linkedin=entry.get("linkedin"),
            confidence=entry.get("confidence", "confirmed"),
            tier=entry.get("tier", "target"),
            status=entry.get("status", "active"),
        )
        for entry in (data.get("contacts") or [])
    ]
    companies = [
        Company(
            id=entry["id"],
            name=entry["name"],
            aliases=list(entry.get("aliases") or []),
            domain=entry.get("domain"),
            country=entry.get("country"),
            confidence=entry.get("confidence", "confirmed"),
        )
        for entry in (data.get("companies") or [])
    ]
    return GroundTruth(contacts=contacts, companies=companies)


# ---------------- Scores ----------------


@dataclass(slots=True)
class PatternScore:
    backend: str
    pattern: Pattern
    queries_run: int = 0
    queries_with_results: int = 0
    queries_skipped: int = 0
    queries_errored: int = 0
    targets_found: set[str] = field(default_factory=set)
    targets_total: int = 0
    # Pattern E only: emails returned that matched ground truth, and those that didn't.
    correct_emails: int = 0
    incorrect_emails: int = 0
    null_emails: int = 0

    @property
    def recall(self) -> float:
        if self.targets_total == 0:
            return 0.0
        return len(self.targets_found) / self.targets_total


def score_run(
    run_dir: Path,
    ground_truth: GroundTruth,
    queries: Iterable[Query],
) -> list[PatternScore]:
    query_by_id: dict[str, Query] = {q.id: q for q in queries}

    # Pattern A recall measures only useful, currently-employed contacts.
    # Directory-tier employees and noise (deceased / left / incorrect) are
    # still matched and tracked separately, but don't count toward recall.
    target_contacts = [
        c for c in ground_truth.contacts if c.tier == "target" and c.status == "active"
    ]
    contact_total = len(target_contacts)
    company_total = len(ground_truth.companies)

    # Pattern E ground truth: contacts (any tier) for which we have a known
    # email. Email-finding accuracy is scored against this set.
    contacts_with_email = {
        c.id: c for c in ground_truth.contacts if c.email
    }

    scores: dict[tuple[str, Pattern], PatternScore] = {}

    for backend_dir in sorted(p for p in run_dir.iterdir() if p.is_dir()):
        # Skip runner-internal metadata directories (e.g. _pattern_d_meta).
        if backend_dir.name.startswith("_"):
            continue
        backend_name = backend_dir.name

        for query_file in backend_dir.glob("*.json"):
            payload = json.loads(query_file.read_text())
            query = query_by_id.get(payload.get("query_id"))
            if query is None:
                continue
            key = (backend_name, query.pattern)
            score = scores.get(key)
            if score is None:
                targets_total = (
                    contact_total
                    if query.pattern is Pattern.PEOPLE_AT_TARGET
                    else company_total
                )
                score = PatternScore(
                    backend=backend_name,
                    pattern=query.pattern,
                    targets_total=targets_total,
                )
                scores[key] = score

            score.queries_run += 1
            if payload.get("skipped"):
                score.queries_skipped += 1
                continue
            if payload.get("error"):
                score.queries_errored += 1
                continue

            # Pattern E has a different payload shape (single email, not a result list).
            if query.pattern is Pattern.EMAIL_FROM_NAME_COMPANY:
                returned_email = payload.get("email")
                if returned_email:
                    score.queries_with_results += 1
                    # A Pattern E query is associated with one or more target contacts;
                    # if the returned email matches any of them, count it as found.
                    matched = False
                    for cid in query.target_contact_ids:
                        contact = contacts_with_email.get(cid)
                        if contact and _emails_equal(returned_email, contact.email):
                            score.targets_found.add(cid)
                            matched = True
                    if matched:
                        score.correct_emails += 1
                    else:
                        score.incorrect_emails += 1
                else:
                    score.null_emails += 1
                continue

            results = payload.get("results") or []
            if results:
                score.queries_with_results += 1

            for result in results:
                blob = _searchable_text(result)
                if query.pattern is Pattern.PEOPLE_AT_TARGET:
                    # Only count target-tier active contacts toward recall.
                    for contact in target_contacts:
                        if _matches_contact(blob, contact):
                            score.targets_found.add(contact.id)
                else:
                    for company in ground_truth.companies:
                        if _matches_company(blob, company):
                            score.targets_found.add(company.id)

    # For Pattern E scores, targets_total is the number of distinct
    # target contacts (with known emails) covered by queries that ran.
    # Done after the iteration so we have the full set.
    for (backend, pattern), score in scores.items():
        if pattern is Pattern.EMAIL_FROM_NAME_COMPANY:
            covered_target_ids: set[str] = set()
            for q in queries:
                if q.pattern is not Pattern.EMAIL_FROM_NAME_COMPANY:
                    continue
                for cid in q.target_contact_ids:
                    if cid in contacts_with_email:
                        covered_target_ids.add(cid)
            score.targets_total = len(covered_target_ids)

    # Return sorted: pattern A, B, C, D, E, then backend name.
    pattern_order = {
        Pattern.PEOPLE_AT_TARGET: 0,
        Pattern.COMPANY_DISCOVERY: 1,
        Pattern.FIND_SIMILAR: 2,
        Pattern.ICP_FROM_URL: 3,
        Pattern.EMAIL_FROM_NAME_COMPANY: 4,
    }
    return sorted(
        scores.values(),
        key=lambda s: (pattern_order[s.pattern], s.backend),
    )


def _emails_equal(a: str | None, b: str | None) -> bool:
    if not a or not b:
        return False
    return a.strip().lower() == b.strip().lower()


# ---------------- Matchers ----------------


def _searchable_text(result: dict[str, Any]) -> str:
    parts = [
        str(result.get("title", "") or ""),
        str(result.get("url", "") or ""),
        str(result.get("snippet", "") or ""),
    ]
    raw = result.get("raw")
    if raw:
        parts.append(json.dumps(raw, default=str))
    return " ".join(parts).lower()


def _matches_contact(text: str, contact: Contact) -> bool:
    name = contact.name.lower()
    if name in text:
        return True
    parts = re.split(r"\s+", name)
    if len(parts) >= 2 and parts[0] in text and parts[-1] in text:
        return True
    if contact.email and contact.email.lower() in text:
        return True
    return False


def _matches_company(text: str, company: Company) -> bool:
    if company.domain and company.domain.lower() in text:
        return True
    for candidate in (company.name, *company.aliases):
        if candidate and candidate.lower() in text:
            return True
    return False
