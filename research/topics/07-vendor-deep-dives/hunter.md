# Vendor deep-dive — Hunter.io

**Status**: Phase 1 stub. Will deepen with hands-on testing in Phase 2 + comparative evaluation against Richbond ground truth.

## What Hunter.io is

Hunter.io is the **email-finding specialist** in the B2B contact-discovery landscape. Founded 2015, it's the oldest and most-recognised name in the "given a domain or a name + company, return the email" niche.

Unlike Apollo (broad person+company database) or Clay (workflow / orchestration platform), Hunter is narrowly focused: **find an email address.** Domain search ("what emails exist at richbond.com?"), email finder ("what's Hassan El Mansouri's email at Richbond?"), and email verifier ("is hassan@richbond.com valid?"). That's the whole product.

For Winston Wolf, Hunter is the **likely default email-finding backend in v1** — established, focused, integrates cleanly with everything, predictable pricing.

## How it works (mechanism)

Hunter's data comes from a different mix than Apollo's:

- **Public web crawling.** Hunter crawls the public web specifically looking for email addresses. Press releases, About pages, company blogs, public press, conference speaker lists, public social profiles.
- **Pattern detection.** Once Hunter sees one email at a domain (e.g., `j.smith@richbond.com`), it infers the domain's email pattern (`firstname.lastname@`) and applies it to other names.
- **No inbox crowdsourcing** (unlike Apollo). This is a cleaner data-provenance story but also means Hunter has narrower coverage than Apollo for individual people.
- **SMTP verification pipeline.** When a candidate email is generated, Hunter validates it via SMTP probe to determine if the mailbox accepts mail.

Hunter's accuracy is generally good for **finding any email at a domain** (domain search) and **verifying a candidate email**. It's weaker at **finding a specific person's email** when that person hasn't appeared in any public source — there, pattern-guessing + verification is the only mechanism, and it can fail silently when the person's email follows an unusual pattern.

## API surface

REST API. Python SDK exists (`pyhunter`).

Main endpoints:

| Endpoint | Purpose |
|---|---|
| `/v2/domain-search` | All emails Hunter has at a given domain. Useful for finding the email pattern. |
| `/v2/email-finder` | Given first name + last name + domain, find the email. |
| `/v2/email-verifier` | Verify an email address (deliverability + format). |
| `/v2/email-count` | Count emails Hunter has at a domain (useful for vetting before paying for full search). |

Example:
```python
import requests

r = requests.get(
    "https://api.hunter.io/v2/email-finder",
    params={
        "domain": "richbond.com",
        "first_name": "Hassan",
        "last_name": "El Mansouri",
        "api_key": "...",
    },
)
result = r.json()
# {"email": "h.elmansouri@richbond.com", "score": 92, ...}
```

The response includes a `score` (Hunter's confidence) and `sources` (where Hunter saw evidence supporting this email). The `score` is calibrated and useful — emails with score ≥ 90 are usually correct; below 50 are coin flips.

## Pricing

| Tier | Cost | Includes |
|---|---|---|
| Free | $0 | 25 monthly searches, 50 verifications |
| Starter | $49/mo | 500 searches |
| Growth | $149/mo | 5,000 searches |
| Pro | $299/mo | 20,000 searches |
| Business | $499/mo | 50,000 searches |

Pricing is **per-search**, not per-account. Predictable. At small scales (under 500 searches/month), Hunter is cheap. At customer scale (thousands of searches/month per customer), the unit economics need modelling.

There's also a **Chrome extension** that consumes the same quota — useful for the user's own manual testing during evaluation.

## Strengths

- **Focused and mature.** Hunter does email-finding well because it's all they do.
- **Public-web-sourced data.** Cleaner provenance than inbox-crowdsourced databases. Less legally grey.
- **The score is calibrated.** Real signal, not marketing fluff.
- **Predictable pricing.** No surprises.
- **Solid API.** Stable, well-documented, low-friction.
- **Domain search is genuinely useful for ICP discovery.** "What emails exist at this company?" returns a list including roles, which can seed people-search.

## Weaknesses / open questions

- **Narrower than Apollo.** Hunter doesn't return phone numbers, employment history, role changes, intent signals. Email is the product.
- **Coverage drops outside English-speaking + EU/US markets.** Public-web-only sourcing means less data on people who don't appear in English-language press / blogs / public listings.
- **Pattern-guessing is the failure mode.** When Hunter says "no match found," sometimes the person exists but their email doesn't follow the inferred pattern. Hunter doesn't always tell you when it's guessing vs. confirmed.
- **Rate limits and per-search pricing make agent loops expensive.** If Scout calls Hunter for every candidate person across many queries, costs add up fast.
- **Not designed for bulk enrichment.** Each search is one API call; no batch endpoint at the entry tier.

## How it fits Winston Wolf

Hunter is the **email-finding backend** in Scout's pipeline. The likely architecture:

1. Search backend (Tavily / Brave / Exa) → finds candidate company pages.
2. Apollo (or LLM-extraction from search results) → identifies candidate people with names + roles.
3. **Hunter** → for each candidate, find/verify the email.
4. Email verifier (Hunter's own, or NeverBounce / ZeroBounce) → final deliverability check.

For the email-finding bake-off (planned in `topics/05-b2b-contact-discovery.md`): Hunter is the **mandatory baseline**. Other candidates (Snov, Apollo's email finder, RocketReach, pattern-guessing-DIY) get evaluated against Hunter's hit rate and accuracy.

## Verification queue (for Phase 2 / Phase 3)

1. **Richbond email ground-truth test.** Of the user's 10 known-correct Richbond emails, how many does Hunter find correctly?
2. **Score calibration check.** Score distribution vs. actual accuracy — is "score ≥ 90 = correct" actually true on our data?
3. **Domain-search test.** Given `richbond.com`, what does Hunter return? Useful for both ICP discovery and pattern detection.
4. **Geographic coverage.** Test a Moroccan, French, and US company. Does Hunter's hit rate drop off?
5. **Cost-per-correct-email.** Track Hunter spend / true-positive emails. Compare to alternatives.
6. **Catch-all domain handling.** Some companies accept all incoming email to their domain regardless of address (catch-all). Hunter should detect this; verify it does.

## References

- Hunter API docs: https://hunter.io/api-documentation.
- Hunter blog posts on email pattern detection and verification.
- Comparative blog posts: Hunter vs. Snov vs. RocketReach vs. Apollo email-finder.
- Reddit r/sales threads on Hunter's real-world accuracy.
