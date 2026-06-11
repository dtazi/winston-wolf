# Winston Wolf — Pivot Disposition Ledger

**Date:** 2026-06-05
**Source:** `scope-architecture-update.md` — the intelligence-layer pivot. WW becomes the
knowledge-base + AI-writer + approval-gate + signal-filter + learning layer on top of
**Instantly** (which owns lead data, verification, domains, inboxes, warm-up, SMTP,
deliverability, and compliance-link injection).
**Purpose:** Give every existing asset a deliberate disposition *before* we re-spec on the
new scope, so nothing is silently abandoned and nothing built is wasted.

**Legend:** **KEEP** = carries into the new architecture (possibly rebound) · **RETIRE** =
out of scope, stop investing + plan removal · **HOLD** = dormant, not deleted, revisit later.

---

## ⚠️ SUPERSEDED IN PART BY PIVOT 2 (2026-06-08) — read this first

The Instantly-layer scope below (Pivot 1, 2026-06-05) was **partially reversed three days
later** by the proof-of-life experiment (spec `004-proof-of-life-experiment`, locked
2026-06-08). The original entries are kept intact as the historical record and reasoning;
this section states what is now true (per Article 18 — supersede, never silently overwrite).

**Why Pivot 2 happened:** the Instantly path assumed a paid, third-party mass-send platform
would carry deliverability. On inspection that motion was still too costly/unreliable to
validate the core question cheaply. So we narrowed again — to the **minimum-cost test**:
send cold outreach from a **single real Richbond mailbox (`richbond.ma`, M365 via
`ww-outreach`)**, with **zero spend** on paid lead databases, email verification, extra
domains, or mass-send tooling — to learn whether disciplined, researched, human-approved
cold email produces any positive signal before investing in scale. (Now enshrined as
constitution **Article 19 — Evidence Before Investment.**)

**Reversals — these Pivot-1 dispositions no longer hold:**

| Asset | Pivot-1 said | Pivot-2 truth (current) |
|---|---|---|
| **`ww-outreach`** (M365 Graph send/auth) | RETIRE — "cold sending = Instantly on secondary domains; cold-on-primary forbidden" | **KEEP & ACTIVE.** The pilot sends from `richbond.ma` via `ww-outreach`, under the Article 16 validation-pilot exception (human-approved, low-volume, time-boxed, primary-domain risk accepted in writing). |
| **`ww-tracking`** (open-pixel + click redirector) | RETIRE — "Instantly owns tracking" | **KEEP & ACTIVE.** Un-retired for the experiment; opens + clicks are the engagement signal (`track.richbondgroup.eu`). |
| **Instantly integration** (Decision 4) | Committed, behind an adapter | **DROPPED for the pilot.** No Instantly, no secondary domains, no warm-up network in 004. Revisit only if the cheap test shows signal worth scaling (Article 19). |
| **Sending identity** = Instantly secondary domains | (dashboard rebind) | **Single real M365 mailbox.** |

**Still valid from Pivot 1:** the KEEP inheritance (`ww-engine` approval gate, drafting
seam grounded in the KB per Article 17, `ww-llm`, `ww-core`), and the manual reply
boundary (Article 15) — the 004 reply handling is manual flagging, not an Instantly webhook.

---

## KEEP — the inheritance

The pivot does **not** reset to zero. The most-emphasized differentiator in the new doc —
the human approval gate with visible AI reasoning — is already built and tested in `ww-engine`.

| Asset | New role | Change required |
|---|---|---|
| **`ww-engine` (002)** — review mode, per-email approve/edit/reject (`modes.py`, `runs.py`, `selection.py`) | **Approval Gate** (workflow layer) — default-on quality control | Keep autonomous mode as an explicit opt-in; ground the writer in the KB so it can't fabricate offers (Art. 17) |
| `ww-engine` drafting seam (`drafting/base.py`, `claude_code.py`, `personalization.py`) | **AI Writer** (intelligence layer) | Ground it in the KB instead of just pitch/brief; keep the input→output contract |
| `ww-engine` `detector.py` (M365 reply/bounce poller) | **Reply handling** | Replace detection *source* with the Instantly webhook; keep stop/suppress/log semantics |
| `ww-engine` `rotation.py`, `cost.py` | Feed the writer / per-stage token+cost accounting | Keep as-is |
| **`ww-llm` (003 foundation)** — engine registry + 4 provider adapters | Powers writer, signal filter, learning | Keep wholesale — just built, still correct |
| **`ww-core`** `customers` / `campaigns` tables + brief/pitch loaders | Tenant + campaign spine; loaders stay | Keep |
| **`pitch.yaml`** (offer, pains, objections, vocabulary) | **Reference input / answer-key for onboarding** — the real Richbond facts the KB interview should surface (not the KB itself anymore, since onboarding builds the KB fresh) | Keep as reference; do not wire as the KB directly |
| ~~`brief.yaml` (ICP, niches, buying triggers)~~ | **Deleted (2026-06-05, operator: "start fresh")** — the Ohio/university + institutional briefs are gone; the ICP is now an *output of onboarding*, not an inherited artifact | Recoverable from git history if ever needed |
| **003 qualification design** (rules → AI-judge vs ICP — *designed, unbuilt*) | **Signal Filter** logic | Rebuild as "filter Instantly contacts" not "qualify discovered leads" |
| **Dashboard spec (001)** | Operator control surface | **Prune + rebind** (see below), not rewrite |
| **Constitution + Spec-Kit** | Governance | Amend Articles 5 & 6, add pivot non-negotiables |
| **`evaluation/` adapter-Protocol pattern** | Reference for the adapter layer | Keep the *pattern*; retire the specific backends |

**Dashboard (001) prune list** — KEEP: approval queue, AI reasoning panel, reply-notification
(fact-only), AI-spend cap/at-cap enforcement, lead table/profile. PRUNE: per-user connected-email
OAuth + the owner-email-disconnect grace machinery (FR-120–136), Scout-mission panel → "lead-pull /
filter status". REBIND: sending identity = Instantly secondary domains, not per-user M365.

---

## RETIRE — now Instantly's job

| Asset | Why retired |
|---|---|
| **`ww-tracking`** (open-pixel + click redirector) | Instantly owns tracking/deliverability. Engagement signals now arrive *from* Instantly. **Code: retire.** **Prod: a live container at `track.richbondgroup.eu` — decommission is a separate ops step (Decision 2).** |
| **`ww-outreach`** (M365 Graph send/auth) | Cold sending = Instantly on secondary domains. Cold-on-primary-domain is now *forbidden*. |
| **`scout/sources/cms_nursing_home.py`** + the source-ingester framework | Lead acquisition is Instantly's (450M+ bundled contacts). |
| **003 enrichment half** — `domain.py`, `person.py`, `email.py` (*unbuilt*) | Domain/person/email-verification are Instantly's. **Do not build these.** |
| **`evaluation/` search + email backends** (brave/exa/perplexity/tavily/serper, hunter/apollo) | Email-finding moves to Instantly; the vendor bake-off (blocked on keys) is moot. |
| **`source_channels`** seed (17 rows) + the table | Acquisition out of scope. |

---

## HOLD — dormant, revisit later

- **China+1 positioning investigation** (VISION.md) — unaffected by the pivot; still parked for Phase 3.
- **Dual-identity model** (cold secondary identity + real primary identity) — needed once WW supports any post-reply workflow; out of skeleton scope.
- **Learning-engine depth** — the skeleton ingests only reply *metadata* (occurred / bounced / opened). Whether the moat eventually needs (consented) reply-*content* access — which collides with the reply boundary — is a deliberate later decision, not a skeleton problem.

---

## Branch / git disposition

- **`003-scout-enrichment` is superseded.** Its genuinely reusable parts — `ww-llm`, the ICP/qualification
  *design*, the cost ledger — are already committed (`4568872`). Do **not** continue building 003's
  enrichment tasks (T016–T030).
- **Recommendation:** cut a fresh branch (e.g. `004-instantly-skeleton`) from `003` so `ww-llm` and the
  reusable foundation come along. Nothing needs reverting; the built foundation is the inheritance.

---

## Decisions this ledger surfaces

1. **Approval gate stays optional — RESOLVED (2026-06-05).** Operator decision: the gate is *not*
   absolute. It defaults ON and is the right early posture — its real value is injecting industry
   knowledge and catching AI fabrications (first trial: the writer invented a "free mattress sample,"
   an unapproved commitment, on Opus). Autonomous mode (002 `FR-004`) is **retained** as an explicit
   per-campaign opt-in once messaging is trusted. The deeper fix is grounding the writer in the KB so it
   cannot fabricate offers/claims in the first place (new **Article 17**). 002's autonomous path is
   **kept, not removed.**
2. **`ww-tracking` prod container.** Decommission `track.richbondgroup.eu` now, or leave it running until
   the skeleton lands? **Recommend:** leave running (harmless), decommission when 001/tracking is formally
   cut — but flag it as an exposed surface carrying no further purpose.
3. **`leads.db` schema.** Rework so `leads` is a *projection of Instantly contacts + WW annotations*
   (filter verdict, draft, approval state, suppression) rather than a WW-owned acquisition store —
   vs. a fresh DB. **Recommend:** migration on the existing file, keep `ww-core`'s loaders.
4. **Instantly.** Committed starting integration (per the doc), behind an adapter, with an early task to
   validate its *actual* contact depth/filter API on a real Richbond niche (pushback #2).
