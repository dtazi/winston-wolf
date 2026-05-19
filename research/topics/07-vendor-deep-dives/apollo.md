# Vendor deep-dive — Apollo.io

**Status**: Phase 1 stub. Will deepen with hands-on testing in Phase 2 + comparative evaluation against Richbond ground truth.

## What Apollo.io is

Apollo is a **B2B contact and company database with workflow tools layered on top**. It's the most likely "default" choice for Winston Wolf-scale users in the contact-data category — bigger than Hunter, smaller and cheaper than ZoomInfo, with API access available at solo / small-team pricing.

The core product is the database: ~275 million contacts, ~75 million companies (Apollo's own claim — verify in Phase 2). Around it, Apollo has built sequencing tools, email plugins, sales engagement features. For Winston Wolf, only the database (via API) is relevant — the sales-engagement layer overlaps with what Outreach will be.

## How it works (mechanism — where the data comes from)

The opaque-but-important part. Apollo's contact database is built from a combination of:

- **Crowdsourced contributions.** When Apollo users connect their email inbox, contacts from their inbox get added to Apollo's database. This is the dominant source.
- **Web scraping of company sites and public listings.** About-us pages, press releases, public team pages.
- **LinkedIn public-profile scraping.** Names, titles, role changes — what's visible on a LinkedIn profile without logging in.
- **Partner data feeds.** Aggregated data from CRM providers, marketing automation tools, and other database brokers.
- **Signal ingestion.** Recent moves (job changes), funding events, news mentions.

The "verified email" pipeline runs on top: Apollo computes likely email patterns for a domain (from observed-correct emails) and validates candidate emails via SMTP probing.

**What Apollo NOT-quite-says publicly:** the email-from-inbox-scraping is the engine. When you sign up for Apollo's free tier and connect your inbox, your contacts (including those of people who never consented to be in Apollo) become part of the database for everyone. This is how Apollo grows. It's also why their freemium is so generous — every free user is a net contributor.

## API surface

REST API. Python SDK is community-maintained; first-party SDK is JS/TS-focused.

Most-used endpoints:

| Endpoint | Purpose |
|---|---|
| `/v1/people/search` | Search for people by criteria (title, company, location, etc.). |
| `/v1/people/match` | Given a name + company, find the matching person record. |
| `/v1/contacts/search` | Search Apollo's contact database with filters. |
| `/v1/organizations/search` | Search for companies by criteria. |
| `/v1/people/{id}` | Get full person record (includes email, phone, role, etc.). |
| `/v1/email_finder` | Email-finder endpoint specifically. |

Example:
```python
import requests

r = requests.post(
    "https://api.apollo.io/v1/people/search",
    headers={"X-Api-Key": "..."},
    json={
        "person_titles": ["procurement", "sourcing", "supply chain"],
        "person_locations": ["Morocco"],
        "organization_industries": ["hospitality"],
        "page": 1,
        "per_page": 25,
    },
)
results = r.json()
```

Search filters are rich: title, location, industry, employee count, revenue, technology used, recent funding, intent signals.

## Pricing

| Tier | Cost | Includes |
|---|---|---|
| Free | $0 | Limited search; no API access (or very limited) |
| Basic | ~$49/user/mo | Limited API quota |
| Professional | ~$79/user/mo | More API quota, intent signals |
| Custom / Enterprise | $500+/mo | High API quota, custom workflows |

For Winston Wolf, the actual pricing tier needed depends on customer-scale query volume. Phase 1 testing fits in free / basic. Production likely requires Professional or higher.

The unit economics consideration: Apollo's price-per-contact is roughly $0.10–$0.50 depending on tier. At customer scale (thousands of contacts queried per month per customer), this is meaningful.

## Strengths

- **Bundled.** Person record includes name, email, phone, role, company, LinkedIn URL, employment history. Saves stitching together multiple data sources.
- **Searchable by intent signals.** Recent job change, recent funding, technology used, hiring intent — useful for filtering targets.
- **Reasonable accuracy** at the Tier 1 / 2 contact-database level. Better than Hunter for full records; worse than ZoomInfo for absolute accuracy.
- **API access at solo-team scale.** Unlike ZoomInfo (enterprise-only).
- **Geographic coverage in EU/US is solid.** Less so for MENA / Africa.

## Weaknesses / open questions

- **MENA / Moroccan / Africa coverage is the critical Phase 3 question.** Apollo's data sourcing skews US/EU. Coverage of Richbond's actual market (Morocco) and target buyer market (likely EU/US hospitality) needs hands-on testing.
- **Data freshness varies.** "Verified" emails may be months or years old. Stated verification dates can be misleading.
- **Source opacity.** You don't know if a record came from inbox scraping, LinkedIn scraping, or partner data. Affects how much you trust each field.
- **The crowdsourced-from-inboxes practice is legally grey.** Anyone whose contact info was shared by an Apollo user is in the database without consent. Fine for Winston Wolf to consume; worth understanding for honesty about the data's provenance.
- **API rate limits.** Get hit at production scale; need careful batching.
- **Vendor dependence.** If Apollo changes pricing, terms, or data quality, Winston Wolf's lead-data layer is exposed.

## How it fits Winston Wolf

Apollo would be the **contact-database backend** for Scout. Different role than the search backends (Tavily / Brave / Exa / Perplexity / SerpAPI):

- **Search backends** = "find pages on the open web that mention X."
- **Apollo** = "look up a structured contact record for X in this curated database."

In a typical Scout workflow:
1. Search backend finds candidate company pages (or starts from the user's ICP).
2. Apollo enriches: given a company name + role criteria, return matching contact records.
3. Hunter (or pattern-guessing) verifies / completes email addresses.

For the Richbond evaluation, the right test for Apollo is: **given the user's 10 known-correct Richbond contacts, does Apollo return them with correct names, roles, and emails?** This is Tier 1 vs Tier 2 vs DIY-from-search question.

## Verification queue (for Phase 2 / Phase 3)

1. **Richbond ground-truth test.** Of the user's 10 known-correct people, how many does Apollo return? With what accuracy on role, email, recent-move signals?
2. **Geographic coverage test.** Same query in Morocco vs. France vs. US — does coverage drop off sharply outside US/EU?
3. **Email accuracy.** Apollo claims "verified" emails — measure actual deliverability against verified-by-other-means cases.
4. **API quotas.** Verify what's possible at each pricing tier; model out customer-scale usage.
5. **Intent signals utility.** Test whether "recent job change" and "recent funding" signals actually correlate with outreach receptiveness.
6. **Cost-per-correct-result.** Track total spend / number of true-positive contact records.

## References

- Apollo API docs: https://apolloio.github.io/apollo-api-docs/.
- Apollo blog posts on their data sourcing methodology (limited but useful).
- Reddit r/sales threads on real-world Apollo accuracy (mixed but informative).
- Comparative posts: Apollo vs. ZoomInfo vs. Lusha (positioning landscape).
