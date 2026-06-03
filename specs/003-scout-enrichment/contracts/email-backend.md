# Contract — `EmailBackend` (email discovery adapter)

Lives in `scout/src/ww_scout/enrichment/base.py`. One adapter per vendor
(`hunter`, `apollo`, … selected by the bake-off; `null` stub for keyless runs).
Called **only on qualified keepers** (SC-003) — the caller enforces that gate, not
the adapter.

```python
class EmailResult:
    email: str | None
    status: str                 # "verified" | "unverified" | "not_found"
    confidence: float           # 0..1 (provider score)
    cost_usd: float | None      # per-lookup cost, for the ledger
    detail: str                 # short reason (no PII)

class EmailBackend(Protocol):
    name: str
    def find_email(self, *, first_name: str, last_name: str, domain: str) -> EmailResult: ...
```

**Rules of the seam**
- The caller maps provider `confidence` to `verified` vs `unverified` against the
  R5 threshold — a backend never reports `verified` for a low-confidence guess by
  fiat; it reports its score and the caller decides.
- `cost_usd` is recorded to `enrichment_ledger` on every call (Article 4).
- HTTPS only; key from env (Article 3). Typed `BackendError` on outage → caller
  parks the lead (Art. 11).
- Never logs the discovered email in plaintext (Article 3).
