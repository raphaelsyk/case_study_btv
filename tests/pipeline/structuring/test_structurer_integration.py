"""Integration test: real Gemini call-identity extraction against NVIDIA's first two
transcript pages.

Regression coverage for the call-identity model change in earnings_calls.models: past
extractions were inconsistent about the quarter label and got the reported time range
wrong, so this pins the exact identity NVIDIA's Q1 FY2026 call should produce.
"""

import datetime
import os
import pickle
from pathlib import Path

import pytest

from earnings_calls.llm_client import GeminiVertexClient
from earnings_calls.models import DateRange, RawPage
from earnings_calls.pipeline.structuring import prompts
from earnings_calls.pipeline.structuring.structurer import TranscriptStructurer, _IdentityAndParticipantsResponse

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(not os.environ.get('GOOGLE_CLOUD_PROJECT'), reason='GOOGLE_CLOUD_PROJECT not set'),
]

_NVIDIA_PAGES_PATH = Path(__file__).resolve().parent / 'test_data' / 'nvidia_raw_pages_12.pkl'


def _nvidia_pages() -> list[RawPage]:
    with _NVIDIA_PAGES_PATH.open('rb') as f:
        return pickle.load(f)  # noqa: S301 - trusted fixture file committed to this repo


def test_identity_call_extracts_correct_call_identity_for_nvidia() -> None:
    pages = _nvidia_pages()
    tagged_text = TranscriptStructurer._tag_pages(pages)

    response = GeminiVertexClient().generate_structured(
        prompts.identity_and_participants_prompt(tagged_text),
        _IdentityAndParticipantsResponse,
    )

    assert response.identity.company == 'NVIDIA Corp.'
    assert response.identity.quarter_name == '2026_Q1'
    assert response.identity.call_date == datetime.date(2025, 5, 28)
    assert response.identity.quarter_time_range == DateRange(
        start_date=datetime.date(2025, 2, 1), end_date=datetime.date(2025, 4, 30)
    )
