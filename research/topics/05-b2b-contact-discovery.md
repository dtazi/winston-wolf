# Topic 05 — B2B contact discovery

**Status**: Phase 1 stub. Will deepen substantially in Phase 3 (vertical research). Most differentiating topic — depth here is what competitors can't easily copy.

## Why this matters for Winston Wolf

Topics 01–04 were about the *general technology* of search and retrieval. This topic is about the **specific industry** of finding B2B contacts: where the data actually comes from, who the data brokers are, what "verified email" really means, and what's available without a paid service.

Most lead-discovery tools differentiate primarily on *volume* (how many contacts in the database) and *freshness* (how recently they were verified). Winston Wolf's hypothesis (per `VISION.md`) is to differentiate on **research depth** instead: industry-tuned context, multi-source corroboration, customer-specific learning. That hypothesis only works if we understand the existing data ecosystem deeply enough to build something genuinely different.

---

## 5.1 Where B2B contact data actually comes from

Every B2B contact database is built from some combination of these sources:

| Source | Typical contribution | Notes |
|---|---|---|
| **Public company websites** | Names of leadership, About pages | Surface-level; rarely emails. |
| **LinkedIn public profiles** | Names, roles, companies, recent moves | Massively informative; LinkedIn restricts scraping; some data is "leaked" via partnerships or other means. |
| **Crowdsourced data** | Mostly email addresses contributed by users | Apollo, Clay, RocketReach all rely on this — when their users connect their inbox, contacts can be added to the broader database. |
| **Email signature scraping** | Names + titles + emails harvested from email signatures | Gmail/Outlook plugins that "enrich" contacts often feed data brokers in the background. |
| **Business registries** | Company existence, ownership, official representatives | Public in most jurisdictions; especially strong in EU. Less so in US/MENA. |
| **Press releases / news** | Executive moves, hires, announcements | Public; freshness is good for high-profile people. |
| **Conference / event data** | Speaker lists, exhibitor lists, attendee programs | Public for the lists themselves; behind-login for full attendee databases. |
| **Trade publications** | Industry-specific names mentioned in articles | Strong for niche verticals. |
| **Webcrawl + parsing** | Pages where contact info is publicly listed | Lower quality at scale; legal grey areas vary. |
| **Partner data feeds** | Aggregated data from CRM providers, marketing automation tools, etc. | The "where did this email come from?" mystery often ends here. |

**Implication:** the major B2B databases (Apollo, ZoomInfo, etc.) are **mostly the same data**, sourced from overlapping pipelines. Differentiation happens at the edges — specific verticals, specific geographies, specific freshness windows.

---

## 5.2 Major data brokers — landscape

### Tier 1 (large, expensive, comprehensive)

| Service | Strengths | Notes |
|---|---|---|
| **ZoomInfo** | Largest US business contact database; high accuracy; deep firmographic data | Enterprise pricing ($$$$); not really accessible at solo / small-team scale. |
| **Apollo.io** | Mid-tier price (~$50–500/mo), reasonable coverage, good API, decent quality | The most likely "default" for Winston Wolf-scale users. |
| **Clay** | Modern data-enrichment platform; combines many providers in one workflow | Popular with sales teams; powerful but complex. |

### Tier 2 (specialised or affordable)

| Service | Strengths | Notes |
|---|---|---|
| **Hunter.io** | Email-finding focused; good domain-search; verifier | Solid baseline for "find an email at this domain." |
| **RocketReach** | Both work + personal email coverage | Useful for harder-to-find people. |
| **Snov.io** | Cheaper Hunter alternative | Worth testing. |
| **Crunchbase** | Strong for company data + funding signals | Weaker for individual contacts. |
| **People Data Labs** | API-first, pay per record, raw bulk data | Good for build-it-yourself enrichment. |

### Tier 3 (niche / specific)

| Service | Strengths |
|---|---|
| **Lusha** | Phone numbers + emails |
| **Cognism** | EU-compliant; strong for European leads |
| **AeroLeads** | Cheaper alternative |
| **UpLead** | Verified-only emails |

### Specifically for MENA / French / Moroccan leads

This is where the major players are *weakest*. ZoomInfo's coverage drops sharply outside the US. Apollo is OK in Western Europe but thin in MENA. The Moroccan Chamber of Commerce and similar registries are likely better sources for known regional companies. **This is a real gap and a possible Winston Wolf differentiation lever.**

---

## 5.3 Email-finding mechanisms

### Pattern guessing

Knowing the company domain (e.g. `richbond.com`) and a person's name (`Hassan El Mansouri`), generate likely email patterns:
- `hassan.elmansouri@richbond.com`
- `h.elmansouri@richbond.com`
- `helmansouri@richbond.com`
- `hassan@richbond.com`
- `hassane@richbond.com` (variations)

A pattern-guessing module emits N candidates per name and rank-orders them by likelihood.

### Pattern detection

Once you've found one verified email at a domain (e.g., from a press release), you know the pattern (`firstname.lastname@richbond.com`) for that organisation. Apply it to other names you have. This is what Hunter's "domain search" does at scale.

### Verification

Given a candidate email, check whether it actually exists. Methods:
- **SMTP probe** — connect to the recipient's mail server and start a delivery handshake without sending. The server's response indicates whether the address exists. Increasingly blocked by modern mail servers.
- **Catch-all detection** — many corporate domains accept all incoming email regardless of address; SMTP probes return "yes" even for fake addresses. Detection heuristics exist but are imperfect.
- **DNS / MX checks** — basic sanity check that the domain has mail servers.
- **Provider-specific checks** — Google Workspace, Microsoft 365 have specific signals.

**"Verified email" usually means: the address survived SMTP probing without bouncing.** It does NOT guarantee the email is read by the named person, that the person still works there, or that the address is monitored. Caveats are routinely under-disclosed by vendors.

### Verification services

Mailgun, NeverBounce, ZeroBounce, Bouncer, and others. All do roughly the same thing — pennies per check. Not really differentiated on quality; differentiated on integrations and trust.

---

## 5.4 What "verified" actually proves (and doesn't)

A verified email tells you:
- The mailbox accepts mail today.
- The mailbox is not on a published bounce list.

It does NOT tell you:
- Who reads the mailbox (could be a shared inbox, an assistant, etc.).
- Whether the named person is still at the company.
- How recently the address was confirmed-correct (could be months or years old).
- Whether sending to it will land in inbox vs. spam folder.

For Winston Wolf, this matters because customer trust depends on outreach landing with the right person. **A "verified" email rate of 90% from a vendor often translates to a real inbox-arrival-and-read rate of 50–70%** after stale data, role changes, and spam filters take their cut.

---

## 5.5 Quality dimensions to evaluate vendors on

When testing data brokers in Phase 3:

- **Coverage**: of N known-correct people, how many does the vendor return at all?
- **Accuracy**: of returned data, how much matches reality?
- **Freshness**: how recent are the verifications? Vendors often won't say.
- **Geographic coverage**: how does the vendor perform on Moroccan / MENA / French data specifically?
- **Email patterns**: does the vendor catch unusual patterns, or only common ones?
- **Role/title accuracy**: does the vendor get the role right, not just the name?
- **Cost per accurate result**: total spend divided by true positives.

The user (you) provides ground truth for the Richbond + known-companies test. Same methodology as the search-backend bake-off.

---

## 5.6 Public sources worth understanding

These are NOT vendors but raw sources Winston Wolf could potentially leverage:

| Source | What it provides | Caveats |
|---|---|---|
| **Moroccan Chamber of Commerce / Office Marocain de la Propriété Industrielle** | Company existence, official representatives, addresses | Coverage and API access vary. Likely manual querying for now. |
| **Conference exhibitor / speaker lists** | Company names, individual names with roles | Fragmented; one site per conference; high-value for vertical-specific research. |
| **Industry trade publications** (hospitality trade press, plastics manufacturing journals) | Names of executives, hires, announcements | Strong for vertical depth; usually behind paywalls but indexed by search. |
| **Press releases (general)** | Executive moves, company news | Searchable via Google; good freshness. |
| **Public company filings** (where applicable) | Officers, board members | High accuracy; only works for listed companies. |

**Mining these directly is more work than buying Apollo, but it's where genuinely differentiated data lives.** The customer's "we found this person via the trade press for plastics in Morocco" is a story neither Apollo nor ZoomInfo can tell.

---

## 5.7 Open questions for Winston Wolf

- **Which Tier-2 brokers should be in the evaluation?** Hunter is mandatory; Snov, RocketReach probably worth including. Apollo (Tier 1) too. Phase 3 bake-off.
- **How well does each vendor cover Moroccan / French data?** This is unknown without testing. Likely the differentiator.
- **Is pattern-guessing + verification (DIY) competitive with paid contact databases** for the kinds of leads Richbond cares about? Worth testing — could save costs significantly.
- **Build vs. buy on email verification.** Probably buy (verification services are cheap, hard to do well DIY).
- **Vertical-specific data ingestion** (conference data, trade press) — can we build this as a Phase 2 or Phase 3 differentiator? How much is automatable vs manual?
- **What's the right ground-truth list for evaluation?** Need 10+ known-correct Richbond people, plus 5–10 contacts at each of the user's known target companies. Ask user to compile when ready.
- **ICP definition quality is upstream of every other quality metric.** Vague input → vague output, regardless of vendor. Validation (2026-05-07): Gojiberry's flat 4-step form (roles → companies → goals → signals) returned generic-B2B suggestions for a hospitality FF&E vertical-specific target. A diagnostic-tree onboarding flow (per VISION.md parking lot) is a likely Winston Wolf differentiation lever — design Scout's architecture so the ICP-definition step has a clean swap-in point for a richer flow later.

---

## 5.8 References for Phase 2 / 3

- Apollo, ZoomInfo, Hunter, Clay engineering / methodology blog posts on how they source data.
- Cognism / Lusha posts on EU data-sourcing practices (often published for marketing reasons; useful regardless).
- Mailgun / NeverBounce blogs on verification mechanics.
- Posts from sales practitioners on Reddit r/sales, r/coldemail about real-world hit rates with each tool.
- Moroccan business-registry documentation.
- "Sales Navigator API" deprecation news (LinkedIn 2024–2026) — affects the underlying B2B data ecosystem.
- *"Data Brokers in the B2B Lead Generation Space"* — overviews from G2, Reddit, etc. (uneven quality, useful for landscape orientation).
