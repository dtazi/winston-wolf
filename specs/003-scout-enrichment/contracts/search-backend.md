# Contract — `SearchBackend` (domain + person discovery adapter)

Mirrors the `evaluation` harness's `SearchBackend` so a bake-off winner drops in
as one adapter file. Lives in `scout/src/ww_scout/enrichment/base.py`. One adapter
per vendor under `enrichment/` (selected via config; `null` stub for keyless runs).

```python
class DomainResult(Protocol-shaped dataclass):
    domain: str | None          # official domain, or None
    confidence: float           # 0..1
    status: str                 # "found" | "not_found"
    detail: str                 # short reason (no PII)

class PersonResult:
    first_name: str | None
    last_name: str | None
    title: str | None
    source_url: str | None
    status: str                 # "found" | "not_found"
    detail: str

class SearchBackend(Protocol):
    name: str
    def find_domain(self, company_name: str, region: str | None) -> DomainResult: ...
    def find_person(self, domain: str, target_roles: list[str]) -> PersonResult: ...
```

**Rules of the seam**
- All network calls HTTPS; API key from env only (Article 3).
- Deterministic acceptance of a domain match is the **caller's** job (R3) — the
  backend returns candidates + confidence; `domain.py` applies the name-token /
  denylist check. Keeps vendor adapters dumb and swappable.
- A backend MUST NOT raise for "not found" — it returns `status="not_found"`.
  It MAY raise a typed `BackendError` for outages (caller parks the lead, Art. 11).
- No prospect PII in logs emitted by adapters (Article 3/10).
