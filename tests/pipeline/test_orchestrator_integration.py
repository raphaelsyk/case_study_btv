"""End-to-end integration test: real docling extraction + real Gemini structuring calls
against one example PDF. Excluded from the default test run (needs GCP credentials and
makes real LLM calls) - run explicitly with `uv run pytest -m integration`.
"""

import os
from pathlib import Path

import pytest

from earnings_calls.llm_client import GeminiVertexClient
from earnings_calls.pipeline.orchestrator import TranscriptPipeline
from earnings_calls.storage.json_file_storage import JsonFileStorage
from tests.conftest import example_pdf_paths

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(not os.environ.get('GOOGLE_CLOUD_PROJECT'), reason='GOOGLE_CLOUD_PROJECT not set'),
]


def test_pipeline_runs_end_to_end_on_one_real_transcript(tmp_path: Path) -> None:
    pdf_path = min(example_pdf_paths(), key=lambda path: path.stat().st_size)
    pipeline = TranscriptPipeline(llm=GeminiVertexClient(), storage=JsonFileStorage(tmp_path))

    transcript = pipeline.run(pdf_path)

    assert transcript.participants
    assert transcript.turns
    assert all(turn.pages for turn in transcript.turns)
