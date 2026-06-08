# Architecture — structure, layers, how vendors are reached

## Layering (post-pivot)
**adapters → intelligence → workflow.** Vendors are named ONLY in adapters.
- **adapters:** `ww-outreach` (M365 send), `ww-tracking` (open/click), `ww-llm`
  (model access).
- **intelligence:** `research.py` (researcher seam), `drafting/grounded.py`
  (KB-grounded drafter), `knowledge.py` (KB/strategy/conclusions loaders).
- **workflow:** `ww-engine` `modes`/`selection`/`sender`/deliver, `feedback.py`
  (the markdown review interface).

For the 30-day experiment the intelligence pieces live **inside `ww-engine`**
(Article 2 — keep the loop tight); they graduate to their own modules at product
time. The **Drafter Protocol seam** (`drafting/base.py`) is the swap point —
keep it intact.

## Modules (each uv-managed)
`core` (ww-core: schema + loaders) · `engine` (ww-engine) · `outreach`
(ww-outreach) · `llm` (ww-llm) · `tracking` (ww-tracking). `engine` depends on
`ww-core`/`ww-outreach`/`ww-llm` as **editable path deps**.

## Public edge
**traefik** owns :80/:443 — Docker-label routing, no file provider. Expose a new
service = containerize + add traefik labels (mirror openclaw); **never install
Caddy / add a file provider.** Full detail in the `reference-zeno-infra` memory.
