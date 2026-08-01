# case-study-btv

Data pipeline for evaluating earnings calls. See `system_design/` for the system
requirements, architecture decisions, and data model behind this implementation.

## Setup

### Requirements
- A GCP project with the Vertex AI API enabled, and local Application Default
  Credentials (`gcloud auth application-default login`).
- [uv](https://docs.astral.sh/uv/) for dependency management.
- Environment variables that configure access to the Vertex AI API:

```bash
export GOOGLE_CLOUD_LOCATION=<REGION>       # e.g. 'eu'
export GEMINI_MODEL=<MODEL>                 # e.g. 'gemini-2.5-pro'
export GOOGLE_CLOUD_PROJECT=<PROJECT-ID>
```

### Before your first start
Create the virtual environment with:
```bash
uv sync
```


## Data

Earnings call transcripts (PDF) live in `data/` (the full multi-quarter corpus) and
`example_data/` (one transcript per company, for quick iteration).

## Running the transformation pipeline

```bash
uv run python -m earnings_calls.cli example_data --output output/structured
```

Structures every PDF in the given input directory and writes one validated JSON file
per transcript to `output/structured/{company}/{quarter}.json`. A failure on one
document is logged and skipped rather than stopping the batch.

## Running the Analyzer

```bash
GOOGLE_CLOUD_PROJECT=<your-project> uv run python -m earnings_calls.analyze_cli jpmorganchase
```

Produces a cited, cross-quarter AI-discussion trend report for one company from its
stored transcripts (`output/structured/{company}/`), writing
`output/analysis/{company}/report.md` and `report.pdf`. The company argument is the
storage slug (e.g. `jpmorganchase`, `bank_of_america`, `microsoft`, `nvidia_corp`).

Internally this runs two LLM stages: a per-quarter "distill" call (cached to
`output/analysis/{company}/_cache/{quarter}.json`, so re-running only distills a newly
added quarter) followed by a cross-quarter "synthesize" call. See the "Analyzer
Module" decision in `system_design/02_system_design.md` for the full design, including
how citations survive the two stages intact.

## Dev

```bash
uv run ruff format .
uv run ruff check .
uv run ty check
uv run pytest
```

`pytest` runs the fast, deterministic suite by default (docling extraction against real
PDFs, everything else against fakes - no GCP calls, no cost). One integration test
exercises a real end-to-end Gemini call and is excluded by default; run it explicitly
with GCP credentials configured:

```bash
uv run pytest -m integration
```
