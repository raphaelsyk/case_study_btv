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
