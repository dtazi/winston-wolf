# Email Foundation — Stable Layer

**Last updated:** 2026-05-26
**Active campaign:** `richbond-us-hybrid-2026q2`
**Companion docs:** [`email_playbook.md`](./email_playbook.md) (testing layer) · [`email_decisions.md`](./email_decisions.md) (changelog)

This is the **stable layer** of Richbond's email design — what changes rarely (at most quarterly, with strategic shifts or new identity facts). Re-read before every batch.

The companion [`email_playbook.md`](./email_playbook.md) holds what changes batch-to-batch (subject style, CTA wording, hypotheses, sourced lessons). If something here moves, also log it in [`email_decisions.md`](./email_decisions.md).

---

## 1. Richbond identity facts

Verifiable, stable, every email may draw on these.

- **60 years** of institutional manufacturing experience.
- **Manufacturing footprint:**
  - Morocco — parent operations and main plant.
  - Côte d'Ivoire — Yopougon plant, opened 2018, ~17,800 m², 164 employees.
- **Distribution reach:** 8 African markets exported from the CI plant (Mali, Burkina Faso, Ghana, Tanzania, Uganda, Rwanda, Burundi, etc.).
- **Brand operations owned/operated by Richbond:**
  - **Simmons** — manufactured in Morocco
  - **Beautyrest** — manufactured in Morocco
  - **Silentnight** — operated in Kenya
- **Vertical integration:** in-house foam, fabric, finishing.
- **Trade status:** Morocco–US Free Trade Agreement in force; institutional bedding output is **TAA-compliant** on origin.
- **Public web anchor:** [richbondgroup.eu](https://richbondgroup.eu/) — the European/institutional-facing site, used as the signature URL for US institutional outreach.

## 2. Strategic positioning

The market story Richbond is telling and testing.

### Target audience segments (the `audience` field on each lead)
- **`direct_buyer`** — institutional buyers (university housing directors, healthcare procurement, hospitality operators). Decision authority on individual purchases or RFPs.
- **`gpo`** — Group Purchasing Organization category managers and supplier-relations leads. Decision authority on multi-institution cooperative contracts.

### The pitch's strategic arguments (priority order)
1. **China-alternative narrative.** A decade of tariff swings, 90+ day ocean lead-times, and geopolitical surprises. Morocco offers shorter Atlantic transit, political stability, and (via FTA) duty-free entry.
2. **Heritage + scale.** 60 years of manufacturing experience; not a startup.
3. **Verifiable named-brand operations.** Ownership of Simmons + Beautyrest in Morocco and Silentnight in Kenya is web-checkable, turning "established institutional player" into a verifiable claim, not a soft assertion.
4. **Regulatory/FTA clarity.** Morocco–US FTA + TAA-compliant origin → cooperative procurement rules are satisfied. Removes a typical objection ("can we buy from this origin under our contract?").

### Success metric
**A reply.** Open rates and click rates are diagnostic (which subject worked, which CTA got clicked) but the pilot's pass/fail is reply rate and reply *content*. A "thanks but not interested" is more informative than 100 opens. A "what's your next RFP date?" is gold.

---

## 3. Non-negotiables checklist

Every email Richbond sends MUST contain ALL of these before delivery. The drafter prompt enforces this; this list is the human-readable double-check. **If a draft is missing one, the drafter is broken — fix it, don't paper over the draft.**

- [ ] **Subject marker** `· Richbond` suffix (middle dot separator) — signature-style, survives "Re:" cleanly.
- [ ] **Subject body** 3–5 words, peer-internal tone, recipient's world (not our product).
- [ ] **Recipient-first opening** — *"We thought [recipient] would want to know…"*. Never *"I'd like to introduce…"*.
- [ ] **At least one specific personalization fact** drawn from `lead.notes`, never invented.
- [ ] **Credibility stack:**
  - 60-year-old institutional manufacturer
  - "Manufactures Simmons and Beautyrest in Morocco and operates Silentnight in Kenya" (or equivalent wording — this is the *only* named-brand language permitted; see named-account guard below)
  - Credible alternative for European institutions
- [ ] **China-alternative frame** — acknowledges a decade of tariff swings / lead-time pain / geopolitical risk.
- [ ] **Soft intent line** — *"not pitching, just making first contact"* or equivalent.
- [ ] **Audience-routed CTA** — yes/no interest gauge or email-delivered asset offer. **Never a meeting time ask. Never a physical mattress sample** (institutional mattresses are too large/expensive to ship speculatively).
- [ ] **TAA / Morocco–US FTA closer** — commercially clean: FTA in force, TAA-compliant origin.
- [ ] **Signoff exactly:**
  ```
  Djaafar Tazi
  Richbond Export
  https://richbondgroup.eu
  ```
- [ ] **Body length** 120–150 words (160 hard cap).
- [ ] **Named-account guard:** `Simmons`, `Beautyrest`, `Silentnight` are the **only three** brand names permitted. **IKEA** is explicitly forbidden (code-enforced via regex post-check in [`drafting/base.py::violates_named_account_guard`](../../engine/src/ww_engine/drafting/base.py)). All other named hotels/hospitals/buyers/competitors are forbidden by default; new brand permissions require explicit operator authorization recorded here **and** in [`email_decisions.md`](./email_decisions.md).
- [ ] **`X-WW-Send: <marker_token>` custom internet header** on every send.
- [ ] **Invisible HTML marker** `<!-- ww-marker: <marker_token> -->` in body — survives quoted replies.
- [ ] **Open-tracking pixel** in body (see playbook §1.6 open gaps).
- [ ] **Click-tracking wrapping** for any links (see playbook §1.6 open gaps).

## 4. When to update this document

Update §1 when:
- A new brand operation is added (e.g., Richbond acquires a license in a new market)
- A new compliance certification is obtained or expires
- Manufacturing footprint changes
- richbondgroup.eu is replaced or augmented with a US-facing landing page

Update §2 when:
- The strategic narrative changes (e.g., a new audience segment added, China-alternative frame retired)
- The success metric changes

Update §3 when:
- A new always-required element is added (a new compliance line, a new tracking mechanism)
- A previous fundamental is removed (record in [`email_decisions.md`](./email_decisions.md) *why*)

Updates here should always be paired with a corresponding entry in [`email_decisions.md`](./email_decisions.md).
