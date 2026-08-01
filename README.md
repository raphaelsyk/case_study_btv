# case-study-btv

Data pipeline for evaluating earnings calls. See `system_design/` for the system
requirements, architecture decisions, and data model behind this implementation.

## Repository Structure

```
.
├── earnings_calls/      # The Python package - pipeline + Analyzer (see below)
├── tests/               # Pytest suite, mirrors earnings_calls/ 1:1
├── system_design/       # Requirements, architecture decisions, data model docs
├── docs/reference/      # Background reading (case-study brief, reference paper)
├── assets/              # Static assets (report logo)
├── pyproject.toml       # Project metadata, dependencies, tool config
├── ruff.toml            # Linter/formatter rules
├── AGENTS.md            # Repository rules for coding agents
├── project_approach.md  # Case-study brief: goal, approach, deliverables, timeline
└── README.md            # This file
```

## Setup

### Requirements
- A GCP project with the Vertex AI API enabled, and local Application Default
  Credentials (`gcloud auth application-default login`).
- [uv](https://docs.astral.sh/uv/) for dependency management.
- Environment variables that configure access to the Vertex AI API:

```bash
export GOOGLE_CLOUD_PROJECT=<PROJECT-ID>
export GOOGLE_CLOUD_LOCATION=<REGION>       # e.g. 'eu'
export GEMINI_MODEL=<MODEL>                 # e.g. 'gemini-3.5-flash-lite' for best performance
```

All three are required - there is no default location or model.

To use an LLM provider other than Google, implement the `LLMClient` protocol in
`earnings_calls/llm_client.py`.

### First-time setup
Create the virtual environment with:
```bash
uv sync
```

## Data

- Earnings call transcripts (PDF) need to live in `data/` (the full multi-quarter corpus).
- Output data of the transformation pipeline should be written to `output/structured`
  to make the analyzer work out of the box (see next section).

## Running the transformation pipeline

```bash
uv run python -m earnings_calls.pipeline_cli data --output output/structured
```

Structures every PDF in the given input directory and writes one validated JSON file
per transcript to `output/structured/{company}/{quarter}.json` using a unified data
model. A failure on one document is logged and skipped rather than stopping the batch.

## Running the Analyzer

```bash
uv run python -m earnings_calls.analyze_cli jpmorganchase
```

Produces a cited, cross-quarter AI-discussion trend report for one company from its
stored transcripts (`output/structured/{company}/`), writing
`output/analysis/{company}/report.md` and `report.pdf`. The company argument is the
storage slug, not the display name (e.g. `jpmorganchase`, `bank_of_america`, `microsoft`,
`nvidia_corp`).

Internally this runs two LLM stages: a per-quarter "distill" call (cached to
`output/analysis/{company}/_cache/{quarter}.json`, so re-running only distills a newly
added quarter) followed by a cross-quarter "synthesize" call.

## Dev

```bash
uv run ruff format .
uv run ruff check .
uv run ty check
uv run pytest
```

`pytest` runs the fast, deterministic suite by default (docling extraction against real
PDFs, everything else against fakes - no GCP calls, no cost). Two integration tests make
real Gemini calls (structuring and a full pipeline run) and are excluded by default; run
them explicitly with GCP credentials configured:

```bash
uv run pytest -m integration
```
