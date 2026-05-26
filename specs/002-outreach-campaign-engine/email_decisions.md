# Email Decisions — Changelog

Reverse-chronological. Each entry records **what changed**, **why**, **what was considered and rejected**, and (where relevant) the commit hash.

The companion doc [`email_structure.md`](./email_structure.md) describes the *current* state. This doc describes *how we got there* so future iterations build on the reasoning rather than re-deriving it.

---

## 2026-05-26 — subject marker swapped: `· Richbond` middle-dot suffix replaces `[Richbond]` prefix

- **Change:** the project tag is now a quiet middle-dot suffix at the *end* of the subject (`a thought for your refresh cycle · Richbond`) rather than the bracketed mail-list prefix that was shipped on 2026-05-25.
- **Why:** operator pushed back on the bracketed form as too tag-y / mass-mail-feeling. The middle-dot suffix reads as a signature continuation rather than a tag, still survives "Re:" cleanly, and preserves the inbox-recognition value for replies.
- **Considered:** `Richbond:` prefix (rejected — still front-loaded and slightly vendor-y); `RB:` initials (rejected — too subtle to spot replies at a glance); no tag (rejected — operator explicitly wants reply visibility).
- **Hypothesis introduced:** H7 in `email_playbook.md` — the suffix's effect on open rate is unmeasured; flagged for A/B test once a fork can run a no-suffix variant.
- **Cross-ref:** [`email_playbook.md` §4](./email_playbook.md), [`email_foundation.md` §3](./email_foundation.md).

---

## 2026-05-26 — brand-ownership phrasing corrected (legal precision)

- **Change:** the drafter previously claimed Richbond was *"trusted by brands such as Simmons Beautyrest and Silentnight"*. Operator clarified the actual relationship: Richbond **owns/operates** these brand businesses — *manufactures Simmons in Morocco*, *manufactures Beautyrest in Morocco*, *operates Silentnight in Kenya*. The prompt now states this explicitly.
- **Why:** "trusted by" is materially different from "owns/operates" — the original phrasing was a soft-customer-of claim that could be legitimately challenged; the corrected phrasing is a verifiable ownership statement that is also a *stronger* credibility signal for institutional procurement (the company running Simmons in Morocco isn't a startup).
- **Implications:**
  - The named-account guard now permits **three** brand names (Simmons, Beautyrest, Silentnight as separate names), not two combined.
  - The credibility stack in [`email_foundation.md` §3](./email_foundation.md) is rewritten accordingly.
  - The stale "only two permitted names" line elsewhere in the drafter prompt was found and corrected in the same edit.
- **Considered:** softer phrasings like *"has manufactured for"* — rejected because the operator confirmed the ownership/license relationship, which is the stronger and accurate claim. No reason to weaken it.

---

## 2026-05-26 — `https://richbondgroup.eu` added to mandatory signoff

- **Change:** every email's signoff now includes the company URL on its own line. The drafter prompt makes this a mandatory rule.
- **Why:** the 4 emails shipped on 2026-05-25 had **no URL**. A recipient curious to verify Richbond had nowhere to click. This is a foundational omission a non-negotiables checklist (now in [`email_foundation.md` §3](./email_foundation.md)) would have caught before send. The omission is exactly why we now have a checklist doc.
- **URL choice:** richbondgroup.eu over richbond.ma / richbond.ci / grouperichbond.ma — the EU site is the right anchor for institutional US outreach (matches the "credible alternative for European institutions" positioning). Logged in the earlier 2026-05-26 URL-choice entry below.
- **Click-tracking note:** the URL is currently inserted *unwrapped* — when the tracking server is deployed (separate work item), the drafter will wrap it through the click-redirector to capture click events as engagement signal.

---

## 2026-05-26 — website URL chosen: `richbondgroup.eu`

- **Change:** the drafter signature will link to [richbondgroup.eu](https://richbondgroup.eu/). Click-tracking wrapping is still pending the tracking-server deployment decision.
- **Why:** the European-credibility angle in the pitch template (§2 element 2) explicitly references *"a credible alternative for European institutions"*. `richbondgroup.eu` is the site that backs that claim; richbond.ma is more B2C/Moroccan-market, richbond.ci is the Ivory Coast retail front, and grouperichbond.ma is French-language corporate. The EU site is the right anchor for US institutional buyers reading the email.
- **Considered:** richbond.ma (rejected — wrong anchor for US institutional pitch); a dedicated Richbond Export landing page (would be ideal but doesn't exist yet — flagged as a separate product opportunity).

---

## 2026-05-26 — created `email_structure.md` + this file

- **Change:** lifted the email-design knowledge out of `claude_code.py` and commit messages into two durable docs.
- **Why:** decisions were getting re-derived every session because there was no living spec of "what the next email looks like" or "why it looks that way." This is the architectural seam between *what the drafter does* and *the campaign content rules* — the latter is config, not code.
- **Considered:** waiting until the externalize-to-brief-YAML refactor was done. Rejected — the docs are useful even before the refactor; once the refactor lands they can be the source the YAML is generated from.

---

## 2026-05-26 — gap discovered: no website URL, broken pixel, click tracking never wired

- **Change:** identified that the 4 emails shipped 2026-05-25 had (a) no clickable website link, (b) an `<img>` pixel pointing at the `track.example.com` placeholder URL, (c) no URL-wrapping for click tracking because no URLs were in the body to wrap.
- **Why this matters:** batch one's open-rate data is null. Click data was never possible. The "is this a real company?" credibility check (one click to richbondgroup.eu) wasn't available to recipients.
- **Owned the miss:** the constitution and research R3 called for tracking to be wired; the engine code is correct but the tracking server was never deployed.
- **Remaining decisions:** which URL (resolved above), where to deploy `tracking/` (Zeno VPS / Cloudflare Tunnel / skip).

---

## 2026-05-25 — subject + CTA prompt rewrite from B2B cold-email research

- **Change:** subject style → 3–5 words after `[Richbond] `, peer-internal tone, recipient's world (Jason Bay "internal camouflage"). CTA → Josh Braun-style soft yes/no interest gauges + email-delivered assets. **Banned:** meeting time asks, physical mattress samples.
- **Why:** the first batch's subjects were product-language and 7–8 words; the CTA "ship a sample" was operator-corrected as nonsensical (institutional mattresses too large/expensive to ship speculatively). Iteration was driven by research (Bay, Braun, 30MPC, 2025 Belkins/Amplemarket open-rate data), not by user-specified wording.
- **Considered:** rewriting just the 4 in-flight drafts and re-sending. Rejected — that batch was already in real inboxes; iteration applies to touch 2 (~14 days) and all future batches.
- **Commit:** `1122f58`

---

## 2026-05-25 — architecture pivot: `/me/sendMail` instead of create-draft-then-send

- **Change:** GraphTransport now POSTs to `/me/sendMail` (Mail.Send scope only) instead of creating a draft (`POST /me/messages`) and sending it (`POST /me/messages/{id}/send`, requires Mail.ReadWrite). Added an invisible `<!-- ww-marker: TOKEN -->` HTML comment in the body to carry the marker_token into quoted replies even when headers don't survive.
- **Why:** got 403 ErrorAccessDenied at first send. Richbond IT had approved Mail.Send + Mail.ReadBasic only — Mail.ReadWrite was never granted. The research R3 design assumed wider scopes than we actually have.
- **Cost of the pivot:** `conversationId` and `internetMessageId` are no longer captured at send time (sendMail returns 202 with no body). Reply detection falls back to marker-token-in-body matching (already supported as rule 2 of `contracts/detector.md`). Less robust for forwarded threads.
- **Restore path:** request Mail.ReadWrite from Richbond IT; swap GraphTransport back. Not blocking.
- **Commit:** `c0abf92`

---

## 2026-05-25 — subject tag: `[Richbond] ` prefix replaces `@ Richbond` suffix

- **Change:** subject prefix `[Richbond] ` instead of suffix `@ Richbond`.
- **Why:** the `@` symbol can trigger spam heuristics (looks like an @mention pattern). `[Richbond]` is a long-established mail-list-style tag, filter-safe, and **visible at the start of the subject line in inbox previews** rather than buried at the end. Operator confirmed "@ Richbond" wasn't a great fit and asked for an alternative; the research-anchored choice was the prefix form.
- **Considered:** plain emoji prefix (e.g., 🇲🇦) — rejected for B2B professionalism; `(Richbond)` parens — same idea but less established convention.
- **Commit:** in `c0abf92`

---

## 2026-05-22 — pitch template formalized (6 elements)

- **Change:** the drafter prompt now enforces a 6-element pitch template (recipient-first opening → credibility stack → China-alternative frame → soft intent → audience-routed CTA → TAA/FTA closer) instead of a generic "write a B2B cold email" instruction. The three rotation angles become the *spotlight* within the template (~40% of the body), not three independent emails.
- **Why:** the operator wrote out the desired message template directly; reflecting it back as a 6-element scaffold made the drafter consistent across angles and recipients. The factored-message principle (FR-013 — recipe records what shaped each email) requires a stable template so we can isolate which angle drove a reply.
- **Considered:** keeping each angle as a fully independent message. Rejected — the recipe attribution becomes muddier and the credibility/closer elements have to be reinvented per angle.
- **Commit:** `7851c84`

---

## 2026-05-22 — Simmons Beautyrest + Silentnight authorized as named brands

- **Change:** the named-account guard (originally blocking *all* customer/partner names per FR-013) now permits exactly two: `Simmons Beautyrest` and `Silentnight`. IKEA and everything else remain forbidden, code-enforced via regex post-check.
- **Why:** operator authorization. The original guard existed because no specific permission had been given; with explicit permission for these two, the credibility stack gets concrete proof instead of generic "trusted by major brands" language.
- **Considered:** phrasing precision — *"trusted by"* (broader, easier to challenge) vs *"manufactured for"* (narrower, harder to challenge). Left at *"trusted by brands such as…"* per operator preference, matching the actual relationship.

---

## 2026-05-22 — signoff identity: "Djaafar Tazi / Richbond Export"

- **Change:** every email signs off exactly as `Djaafar Tazi\nRichbond Export`.
- **Why:** B2B reply rates favor a single named human over team aliases. The same identity now appears on the operator's LinkedIn ("International Expansion @ Richbond"), so a recipient who clicks through to verify sees the same person.

---

## 2026-05-22 — CTA split by audience (`direct_buyer` vs `gpo`)

- **Change:** drafter now routes the CTA based on a `lead.audience` field. `direct_buyer` gets a sample-shipment-style ask; `gpo` gets a factory-audit invite.
- **Why:** university housing directors will reply to a sample ask but ignore a factory invite to Morocco; GPO category managers expect supplier audits as part of their qualification process and a sample ask undersells the relationship. Same body, different doorway.
- **Superseded 2026-05-25** — the sample-shipment ask was later replaced with an email-delivered one-pager (mattresses are too large to ship speculatively).

---

## 2026-05-22 — `lead.audience` column added to the leads schema

- **Change:** new `audience` column on `leads` (`direct_buyer | gpo`, default `direct_buyer`, CHECK constraint). Idempotent migration via `engine/src/ww_engine/db.py::_ADD_COLUMNS`.
- **Why:** the per-audience CTA decision above needs a place to record the audience tag per lead so the drafter can route correctly.
- **Commit:** `7851c84`

---

## 2026-05-22 — personalization layer reads `lead.notes`

- **Change:** `personalization.gather()` now appends each line of `lead.notes` as a `context: …` fact, escalating the personalization level from `dataset` to `web`.
- **Why:** dataset-only personalization (name, title, region, size) produces too-generic openings. Sharp facts (e.g., *"~8,000 students across 36 residence halls"*) need a place to live per lead. The `notes` column was already on the `ww-core` schema, no migration required.

---

## 2026-05-19 — rotation reversal: all 3 angles across 3 touches per lead (not 1 angle for all 3)

- **Change:** every lead receives all three value angles across their three touches, in a rotated starting order across the population. Earlier rule (each lead locked to ONE angle across all 3 touches) was reversed.
- **Why:** the original "1 angle per lead" was designed to enable a clean A/B test of which angle wins. At pilot scale (low hundreds of leads, 1–5% reply rate, 3 cells) the cell sizes were too small for meaningful comparison — 4 replies vs 2 is noise. Sacrificing A/B cleanliness for reply volume is the right trade since the A/B can't be cleanly resolved anyway.
- **Considered:** dropping to 2 angles (smaller cells → bigger replies-per-cell). Rejected — same noise problem just with different arithmetic.
- **The data we *can* still learn from:** reply *content* per angle/touch combination (qualitative), and the position-rotation removes the trivial confound of "touch 2 always gets more replies just because it's the second contact."

---

## 2026-05-19 — value angles chosen

- **Change:** three rotation angles: `china_plus_one`, `60_years_experience`, `trusted_by_heavyweights`.
- **Why:** the three pillars of Richbond's strategic positioning that are testable independently. `china_plus_one` speaks to supply-chain pain; `60_years_experience` speaks to heritage; `trusted_by_heavyweights` speaks to social proof. Together they cover three distinct buyer motivations.
- **Considered:** adding `regional_african_supplier` (rejected: too narrow for US institutional buyers); `vertical_integration` (rejected: too operational, not pain-driven); `morocco_made` (rejected: implied by other angles).

---

## 2026-05-19 — success metric = a reply (not opens, not meetings)

- **Change:** the pilot's single success metric is a reply. Reply *content* is the primary signal at pilot volume.
- **Why:** opens are too noisy (pixel blockers, automated previews); meetings booked is too far down the funnel for pilot volume to inform message design. A reply — even a "thanks but not interested" — is real human attention to the message. Reply content (objection, interest level, wrong-person redirect) is dense signal per lead.
- **Considered:** open rate (rejected — too noisy); meeting booked rate (rejected — too sparse at pilot N).

---

## How to add a new entry

1. Decide whether the change is structural (add to `email_structure.md`) or a decision (add a new section here).
2. Write the entry: **Change**, **Why**, **Considered**, **Commit** (if applicable).
3. Place it at the top of this file (most recent first).
4. If experimenting with a structural variant, create `email_structure.<fork-name>.md` and reference it in this entry.
