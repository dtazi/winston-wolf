# Winston Wolf

**AI lead-discovery and outreach, configured per industry.**

Winston Wolf finds leads, writes and tests outreach, and runs a lightweight CRM dashboard on top of both. It is built first for Richbond Group (Moroccan manufacturer, hospitality buyers) and Richbond's plastics company — two real Phase 1 customers in different verticals.

The architecture is multi-tenant from day one and industry-adaptive by design: industry knowledge enters through configuration, prompts, data sources, and tenant settings — never hardcoded in the core schema. The tool learns an industry; it isn't built for one.

## Three pillars
- **Scout** — finds and qualifies leads.
- **Outreach** — writes, tests, and sends personalised email.
- **Dashboard** — control surface plus a lightweight CRM.

## Status
Outreach pillar building. Shipped modules: [`core/`](core/) (lead DB + brief/pitch), [`tracking/`](tracking/) (open-pixel + click redirector), [`outreach/`](outreach/) (M365 send/auth), [`evaluation/`](evaluation/) (Scout vendor bake-off), and [`engine/`](engine/) — the self-running outreach campaign engine ([`specs/002-outreach-campaign-engine/`](specs/002-outreach-campaign-engine/), implemented + tested). Next planned: [`specs/001-dashboard-skeleton/`](specs/001-dashboard-skeleton/). Project rules live in [`.specify/memory/constitution.md`](.specify/memory/constitution.md); strategy in [`VISION.md`](VISION.md).
