# Email Structure — Current State

**Last updated:** 2026-05-26
**Active campaign:** `richbond-us-hybrid-2026q2` (see [`data/briefs/richbond-us-hybrid-pilot-2026q2.yaml`](../../data/briefs/richbond-us-hybrid-pilot-2026q2.yaml))
**This document describes what the next email Richbond sends will look like.**
For *why* it looks this way and what we tried before, see [`email_decisions.md`](./email_decisions.md).

---

## 1. Subject line

- Format: `[Richbond] <3–5 words of peer-internal tone>`
- The `[Richbond]` prefix is a classic mail-list-style tag — instantly visible in inbox previews so replies are unmistakable. It is filter-safe (`@`-prefixed forms were considered and rejected for spam-flag risk).
- The 3–5 words after the tag are **peer-internal**, *not* product language. Written as if a colleague in the recipient's own world wrote them.
  - **Good:** `[Richbond] a thought for your refresh cycle`, `[Richbond] Midwest furnishings sourcing thoughts`
  - **Bad:** `[Richbond] Bedding lifecycle planning across your 36 residence halls` (too long, too product-centric)
- No urgency words, no all-caps, no recipient name in the subject (triggers spam filters per Bay).

## 2. Body — the pitch template (6 elements, in order)

1. **Recipient-first opening.** Personalized to the recipient's situation using public/dataset facts. Opens *with their world*, not with us. Pattern: *"We thought [recipient] would want to know…"* — never *"I'd like to introduce…"*.
2. **Credibility stack.**
   - 60-year-old Moroccan institutional manufacturer
   - Trusted by brands such as **Simmons Beautyrest** and **Silentnight** (the only two named brands permitted — see §5)
   - Credible alternative for European institutions
3. **China-alternative frame.** A decade of tariff swings, container lead-time stretching past 90 days, geopolitical risk. Recognizes the buyer's actual pain.
4. **Soft intent.** *"Not pitching — making first contact"* or *"a quiet heads-up"*. Never a hard pitch.
5. **CTA (audience-routed).** See §3.
6. **Closer.** Morocco–US Free Trade Agreement in force, TAA-compliant origin. Commercially clean.

## 3. CTA by audience

| Audience | CTA pattern | Example |
|---|---|---|
| `direct_buyer` (institutional buyers, housing directors, procurement officers) | Low-friction asset offer phrased as yes/no interest gauge. Email-delivered. **Never a physical mattress sample** (too large/expensive to ship speculatively). **Never a meeting time ask.** | *"Worth a one-pager on our institutional capabilities by email?"* / *"Open to a 2-minute factory tour link?"* |
| `gpo` (cooperative purchasing org category managers, supplier-relations leads) | Soft interest gauge framed around their RFP cycle. Factory audit is offered conditionally on their existing supplier-qualification process — never as a cold first ask. | *"Worth being on the bidders list for the next furnishings re-bid?"* / *"Open to an introductory technical brief by email — no call needed?"* |

## 4. Length & signature

- **Target body length:** 120–150 words. 100–130 is even better. Hard cap implicit at 160.
- **Signoff (every email, exactly):**
  ```
  Djaafar Tazi
  Richbond Export
  ```
- **Signature URL:** [richbondgroup.eu](https://richbondgroup.eu/) (chosen 2026-05-26). Will be appended to the signature once the drafter prompt is updated; click-tracking wrapping is pending the tracking-server deployment decision (see `email_decisions.md`).

## 5. Named-account guard

- **Permitted named brands:** `Simmons Beautyrest`, `Silentnight` (operator authorization 2026-05-22).
- **Explicitly forbidden:** `IKEA` (code-enforced post-draft regex check in `drafting/base.py::violates_named_account_guard`).
- **Default for everything else:** prohibited. New brand mentions require explicit operator authorization recorded in this document.

## 6. Value-angle rotation

Every lead receives all three value angles across their 3 touches, in the order set by the lead's `rotation_group` (0/1/2). The drafter applies "spotlight ~40% of body" to the touch's assigned angle while keeping the rest of the pitch template intact.

| Angle | Spotlight content |
|---|---|
| `china_plus_one` | Supply-chain certainty after a decade of disruption (tariffs, lead-times, geopolitics) |
| `60_years_experience` | Heritage + established European-market alternative |
| `trusted_by_heavyweights` | Named brand credibility (Simmons Beautyrest, Silentnight) + Morocco–US FTA / TAA closer |

Rotation group is assigned by `stable_hash(lead.id) % 3` — deterministic, idempotent, balanced at population scale (variance high at N<10, expected).

## 7. Tracking / reply attribution (per send)

| Mechanism | Status (2026-05-26) | Purpose |
|---|---|---|
| `X-WW-Send: <marker_token>` custom internet header | **Set on every send.** | Primary marker for reply detection in NDRs and header-carrying clients. |
| Invisible HTML comment `<!-- ww-marker: <token> -->` in body | **Set on every send.** | Survives quoted replies even when headers are stripped. |
| `<img>` open-tracking pixel | **Broken** — points at placeholder `https://track.example.com`. Awaiting tracking-server deployment decision. |
| Click-tracking link wrapping via `tracked_links` table | **Not wired** — no URLs are currently injected into bodies. Awaiting drafter signature-URL update + tracking-server deployment. |
| `conversationId` / `internetMessageId` from Graph | **Not captured** since the 2026-05-25 switch to `/me/sendMail` (Mail.Send scope only). Restore-path: request Mail.ReadWrite from Richbond IT, swap back to draft-and-send flow. |

## 8. Forks (A/B variants of this structure)

When experimenting with a structural change (e.g., dropping brand mentions, trying emoji subjects, swapping the closer order), create a sibling document `email_structure.<fork-name>.md` and record the experiment in [`email_decisions.md`](./email_decisions.md). Only one structure is "live" per campaign at a time; the brief YAML's `style_guide:` ref (when introduced) points at the active file. No forks active yet.
