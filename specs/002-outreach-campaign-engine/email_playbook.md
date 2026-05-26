# Email Playbook — Testing Layer

**Last updated:** 2026-05-26
**Active campaign:** `richbond-us-hybrid-2026q2`
**Companion docs:** [`email_foundation.md`](./email_foundation.md) (stable layer) · [`email_decisions.md`](./email_decisions.md) (changelog)

This is the **testing layer** — what changes batch-to-batch as we iterate on real reply data. It holds: the *current rules*, the *falsifiable claims* those rules embody, the *external evidence* each rule rests on, and a *cross-reference* from every logged decision to the lessons that justify it.

Any new rule in the drafter prompt must cite a lesson in §3 or live in §2 as an explicit Richbond-specific bet.

---

## 1. Current message structure rules

The current tactical rules the drafter follows. Subject to iteration based on reply data and new research.

### 1.1 Subject line
- **Format:** `<3–5 words of peer-internal tone> · Richbond`
- **Tone:** as if a colleague in the recipient's own world wrote it. Lowercase or sentence case. No marketing language. No urgency words. No recipient name in subject (triggers spam filters per L1).
- **Good:** `a thought for your refresh cycle · Richbond`, `Midwest furnishings sourcing thoughts · Richbond`
- **Bad:** `Bedding lifecycle planning across your 36 residence halls · Richbond` (too long, too product-centric), `Are you available for a call? · Richbond` (commitment ask in subject)

### 1.2 Body — 6-element pitch template
1. **Recipient-first opening.** Personalized using `lead.notes` facts.
2. **Credibility stack.** 60-year heritage + Simmons/Beautyrest/Silentnight ownership phrased per foundation §1 + European track record.
3. **China-alternative frame.** Concrete: tariff swings, 90+ day lead-times, geopolitical risk.
4. **Soft intent.** *"Not pitching, just making first contact"* or equivalent.
5. **CTA (audience-routed).** See §1.3.
6. **Closer.** Morocco–US FTA + TAA-compliant origin.

### 1.3 CTA by audience

| Audience | CTA pattern | Example |
|---|---|---|
| `direct_buyer` | Low-friction email-delivered asset offer, framed as yes/no interest gauge. **No physical mattress. No meeting time.** | *"Worth a one-pager on our institutional capabilities by email?"* / *"Open to a 2-minute factory tour link?"* |
| `gpo` | Soft interest gauge framed around their RFP cycle. Factory audit offered as a future supplier-qualification option, not a cold first ask. | *"Worth being on the bidders list for the next furnishings re-bid?"* / *"Open to an introductory technical brief by email — no call needed?"* |

### 1.4 Length & signature
- Body length target: 120–150 words (160 hard cap).
- Signoff exactly (see foundation §3):
  ```
  Djaafar Tazi
  Richbond Export
  https://richbondgroup.eu
  ```

### 1.5 Value-angle rotation (FR-011 / FR-012)

Every lead receives all three value angles across their 3 touches, in the order set by the lead's `rotation_group` (0/1/2). The drafter applies "spotlight ~40% of body" to the touch's assigned angle while keeping the rest of the pitch template intact.

| Angle | Spotlight content |
|---|---|
| `china_plus_one` | Supply-chain certainty after a decade of disruption |
| `60_years_experience` | Heritage + established European-market alternative |
| `trusted_by_heavyweights` | Named brand operations (Simmons / Beautyrest / Silentnight) + Morocco–US FTA / TAA closer |

Rotation group: `stable_hash(lead.id) % 3`. Deterministic, idempotent, balanced at population scale; high variance at small N is expected.

### 1.6 Open gaps (current state vs the foundation standard)

**Closed 2026-05-26 (step 2 code update):**
- ~~Signature URL `https://richbondgroup.eu` — now in the drafter prompt as a mandatory signoff line.~~
- ~~Brand-ownership phrasing — drafter now states *"manufactures Simmons and Beautyrest in Morocco and operates Silentnight in Kenya"* instead of the inaccurate *"trusted by"*.~~
- ~~Subject marker — drafter now uses the subtle `· Richbond` middle-dot suffix; the bracketed prefix was retired.~~

**Still open:**
1. **Open-tracking pixel** points at the placeholder `https://track.example.com/pixel/...`. The `tracking/` FastAPI service has never been deployed. Batch one's open data is null and any future batch's will be too until deployment lands.
2. **Click-tracking wrapping** isn't wired — the new signature URL is currently inserted *unwrapped*, so clicks aren't captured even though the URL is present. Wiring requires the tracking server.
3. **`conversationId` capture** lost since the 2026-05-25 architecture pivot to `/me/sendMail`. Restore path: request `Mail.ReadWrite` from Richbond IT.

---

## 2. Hypotheses under test

Each hypothesis is **falsifiable** (a refuting result is stated), **sourced** (we know who said it works), and **measurable** (we know what data we need).

### H1 — Subject style
**Claim:** A 3–5 word peer-internal-toned subject referencing the recipient's world outperforms longer product-language subjects.
**Source:** [L1 Bay](#l1), [L4 2025 open-rate data](#l4).
**Prior:** Open rate ~46% (research consensus) vs ~35% baseline.
**Refuted by:** Open rate ≤ 25% across batch two on current subjects.
**Measure:** Open events from tracking pixel (once deployed); A/B against a product-language subject fork.

### H2 — CTA style
**Claim:** A soft yes/no interest gauge or email-delivered asset offer outperforms a meeting-time ask or physical-sample offer.
**Source:** [L2 Braun](#l2).
**Prior:** Higher reply rate; replies skew toward "yes, send the one-pager" or "what's the next RFP date" rather than calendar clicks.
**Refuted by:** Zero replies on this CTA across batch two; or a fork with a soft meeting ask outperforming.
**Measure:** Reply rate; reply content classification.

### H3 — Recipient-first opening
**Claim:** Opening with *"we thought [recipient] would want to know…"* outperforms *"I'd like to introduce…"*.
**Source:** [L1 Bay](#l1), [L3 Holland](#l3).
**Prior:** Higher read-through; higher reply rate.
**Refuted by:** Equal or worse reply rate vs a vendor-first opener fork.

### H4 — Named brand-operation credibility *(HIGH PRIORITY TO A/B TEST)*
**Claim:** Mentioning Richbond's ownership of Simmons + Beautyrest in Morocco and Silentnight in Kenya lifts reply rate vs an unnamed *"established institutional manufacturer"* phrasing.
**Source:** Inferred from social-proof principles in [L3 Holland](#l3); **no direct expert citation specific to this case** — this is a Richbond-specific bet.
**Prior:** Modest lift; main effect is recipients can verify the claim by web search, raising legitimacy.
**Refuted by:** A fork without brand-operation mentions produces equal or higher reply rate.
**Measure:** Reply rate compared to an unnamed-operations fork.
**Why flagged:** Claim with no direct expert citation deserves priority A/B testing — we shouldn't take our own opinion as evidence.

### H5 — Audience-routed CTA differentiation
**Claim:** Capability one-pager for direct buyers + bidders-list factory-audit for GPO category managers produce **different reply patterns**, not just different reply rates. Direct buyers reply with "send the one-pager" or "wrong person"; GPO category managers reply with "RFP cycle is Q3" or "we're full on this category."
**Source:** [L2 Braun](#l2) + industry knowledge of GPO procurement cycles (no single expert citation).
**Prior:** GPO reply rate is lower but each reply is strategically more valuable.
**Refuted by:** Both audiences reply at the same rate AND with the same content patterns.

### H6 — Length
**Claim:** 120–150 word emails outperform 200+ word emails for B2B cold first contact.
**Source:** [L4 2025 open-rate data](#l4); [L5 30MPC length analysis](#l5).
**Prior:** Replies skew toward emails under 150 words; degrades above 200.
**Refuted by:** Longer emails consistently outperform.

### H7 — Subject marker does not hurt deliverability *(HIGH PRIORITY TO A/B TEST)*
**Claim:** A subtle middle-dot `· Richbond` suffix does not depress open rates vs an untagged subject.
**Source:** Indirect — middle-dot is unobtrusive (vs the bracketed form rejected by operator). No direct cold-email study cited.
**Prior:** Negligible delta vs untagged.
**Refuted by:** A fork without the suffix opens at materially higher rate (e.g., 10+ percentage points).
**Measure:** A/B between tagged and untagged batches. The marker's *operator-recognition* value must be weighed against any deliverability cost we measure.

---

## 3. Lessons library (sourced)

Whenever a drafter prompt rule is added, it must cite at least one entry here.

### L1 — Jason Bay (Outbound Squad) <a id="l1"></a>
[outboundsquad.com](https://outboundsquad.com) · Bay's LinkedIn archive · Outbound Squad cold-email starter pack.
- "Internal camouflage" — subjects should mirror how the recipient's *colleagues* write to them internally, not how vendors write. Casual, lowercase, peer-tone.
- Subjects under 5 words have materially higher open rates (Gong data citation).
- You-centric framing in the opening.
- Recipient name in subject is dated and triggers spam filters.
- Activity-based personalization outperforms title/company-based at director+ levels.
- *Used in:* H1, H3.

### L2 — Josh Braun (Salesborne) <a id="l2"></a>
[joshbraun.com](https://joshbraun.com) · Braun's LinkedIn archive · "15 Cold Email Copywriting Principles" PDF.
- Meeting-time asks are among the worst-performing CTAs.
- Soft yes/no interest gauges work better: *"Worth exploring?"*, *"Opposed to learning more?"*.
- Low-friction asset offers ("send a 2-min demo / one-pager") outperform commitment asks.
- Some emails work better with no explicit CTA — interested people know how to reply.
- *Used in:* H2, H5.

### L3 — Becc Holland (Flip the Script / Personalization at Scale) <a id="l3"></a>
Holland's published methodology and LinkedIn writing.
- Personalization at scale via repeatable formats > one-off artisanal personalization that doesn't survive batch sending.
- Open with the recipient's situation as you understand it, not your offer.
- Social proof works better when it's specific and verifiable.
- *Used in:* H3, H4.

### L4 — 2025 open-rate data (Belkins / Amplemarket / Evaboot / lemlist) <a id="l4"></a>
- [Belkins B2B Cold Email Subject Lines and Engagement Statistics 2025](https://belkins.io/blog/b2b-cold-email-subject-line-statistics)
- [Amplemarket subject lines](https://www.amplemarket.com/blog/30-insanely-clickable-email-subject-lines-for-b2b-sales)
- [Evaboot subject lines guide](https://evaboot.com/blog/b2b-cold-email-subject-lines)
- Subjects of 2–4 words: ~46% open rate.
- Personalized subjects: 46% vs 35% non-personalized.
- Question-framed subjects perform best.
- Marketing jargon and urgency words ("ASAP", "now") push engagement below 36%.
- *Used in:* H1, H6, H7.

### L5 — 30 Minutes to President's Club <a id="l5"></a>
- [The Data-Backed Cold Email Formula](https://www.30mpc.com/newsletter/the-data-backed-cold-email-formula-the-exact-words-length)
- [4 Data-Backed Subject Lines](https://www.30mpc.com/newsletter/4-data-backed-subject-lines-to-get-your-cold-emails-opened)
- Specific word-length analyses tied to reply outcomes.
- Subject + opener should pass the "could a colleague have written this?" test.
- *Used in:* H6.

### L6 — Sales Hacker community <a id="l6"></a>
[saleshacker.com](https://saleshacker.com) — used as secondary corroboration. Not currently the primary source for any hypothesis.

---

## 4. Decisions ↔ Lessons cross-reference

Every entry in [`email_decisions.md`](./email_decisions.md) should map to a lesson here. Decisions with no lesson citation are **flagged unsupported opinion** — they should be sourced or A/B tested before they earn their place.

| Decision (date, summary) | Cites | Hypothesis |
|---|---|---|
| 2026-05-26 brand-ownership phrasing correction | (factual precision, not a stylistic choice) | — |
| 2026-05-26 subject tag: `· Richbond` middle-dot suffix | None directly — operator design choice + L1 (subtlety principle) | **H7 — flagged for A/B test** |
| 2026-05-25 subject + CTA rewrite | L1, L2, L4, L5 | H1, H2, H6 |
| 2026-05-25 `/me/sendMail` pivot | (architectural, not strategic) | — |
| 2026-05-25 `[Richbond]` prefix replaced `@ Richbond` suffix | Mail-list convention | (superseded 2026-05-26) |
| 2026-05-22 pitch template formalized | L1 (recipient-first), L2 (CTA) | H3, H5 |
| 2026-05-22 Simmons + Silentnight permitted as named brands | L3 (social proof, generic) | **H4 — flagged for A/B test** |
| 2026-05-22 signoff identity | Industry convention | — |
| 2026-05-22 CTA split by audience | L2 + GPO procurement knowledge | H5 — partly sourced |
| 2026-05-19 rotation reversal | Statistical reasoning (small-N noise) | — |
| 2026-05-19 value angles chosen | Richbond strategic positioning | — |
| 2026-05-19 success metric = a reply | Industry standard for cold B2B at pilot scale | — |

**Priority A/B tests** (decisions with weakest external citations):
- **H4** — named brand-operation lift. Test by running one batch fork without the brand mentions.
- **H7** — middle-dot subject suffix deliverability. Test by running one batch fork without the suffix.

---

## 5. Fork procedure (A/B variants)

When experimenting with a structural change:
1. Pick the hypothesis the fork tests (H1–H7 or a new one).
2. Create `email_structure.<fork-name>.md` as a sibling document describing the variant.
3. Update [`email_decisions.md`](./email_decisions.md) with the experiment plan (start date, sample size, refutation condition).
4. Once data is in, record the result under the relevant hypothesis (confirmed / refuted / inconclusive) and add a follow-up decision entry.

No forks active as of 2026-05-26.

---

## 6. How to use this document

- **Before adding a rule to the drafter prompt:** ensure it cites a lesson in §3. If no citation exists, mark it as a Richbond-specific bet and add it as a new hypothesis in §2.
- **When a batch's replies arrive:** map each reply against the relevant hypothesis. Did H2's soft CTA produce the reply, or H3's opener? When unsure, flag it in [`email_decisions.md`](./email_decisions.md) and propose a fork experiment to disambiguate.
- **When forking the structure:** see §5.
- **When the strategy or non-negotiables themselves change:** update [`email_foundation.md`](./email_foundation.md) instead.
