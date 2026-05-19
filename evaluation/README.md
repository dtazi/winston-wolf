# Winston Wolf — Evaluation Harness

Permanent infrastructure for evaluating search and contact-data vendors against per-customer ground truth.

The harness is **customer-agnostic** and **vendor-agnostic**: adding a new customer is a YAML + query-set drop-in, adding a new vendor is a single adapter file implementing the `SearchBackend` protocol.

## Quick start

```bash
cd evaluation
uv sync                                          # installs deps into .venv
cp .env.example .env                             # then fill in API keys
uv run ww-eval list-backends                     # show available adapters
uv run ww-eval list-customers                    # show registered customers
uv run ww-eval run --customer richbond --backends exa,tavily
uv run ww-eval score --customer richbond --run-id <timestamp-from-run-output>
```

## Layout

```
evaluation/
├── pyproject.toml
├── .env / .env.example          # API keys (.env is gitignored)
├── src/ww_evaluation/
│   ├── backends/                # one adapter per vendor — implements SearchBackend
│   │   ├── base.py              # the SearchBackend protocol + SearchResult
│   │   ├── exa.py
│   │   └── tavily.py
│   ├── queries/                 # query sets per customer
│   │   ├── base.py              # Query model
│   │   └── richbond.py
│   ├── ground_truth/            # data files — the answer keys
│   │   └── richbond.yaml
│   ├── runner.py                # fires queries through backends, saves raw responses
│   ├── scorer.py                # measures recall against ground truth
│   └── cli.py                   # ww-eval entry point
├── results/
│   ├── raw/                     # vendor responses, one dir per run (gitignored)
│   └── history/                 # scored summaries — version-controlled
└── docs/                        # extension recipes (forthcoming)
```

## Design principles

- **Adapter pattern.** Every vendor's response shape gets normalised into `SearchResult`. The runner and scorer only ever see the normalised shape.
- **Raw responses preserved.** `results/raw/` keeps every vendor's full response, so we can re-score under new criteria without re-paying for API calls.
- **Scoring evolves separately.** Today's scorer measures recall against ground truth. Tomorrow's may weight by confidence, penalise latency, etc. — the scorer is its own module so the criteria can change without re-running.
- **Results-first.** Quality against ground truth is the primary axis. Cost and latency are tracked passively until we have multiple vendors that meet the quality bar.

See the project memory file `project_evaluation_harness_permanent.md` for the rationale.
