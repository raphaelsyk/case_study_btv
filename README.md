# case-study-btv

Data pipeline for evaluating earnings calls.

## Setup

```bash
uv sync
```

## Data

Earnings call transcripts (PDF/TXT) live in `data/`.

## Dev

```bash
uv run ruff check .
uv run pytest
```
