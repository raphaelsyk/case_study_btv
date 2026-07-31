"""Tests for TranscriptPipeline wiring and per-document failure isolation, against fakes
for extraction, the LLM, and storage - deterministic, no real docling/Gemini calls.
"""

import datetime
from pathlib import Path

from earnings_calls.models import CallIdentity, Chunk, DateRange, RawPage, Section, Speaker, Turn
from earnings_calls.pipeline import TranscriptPipeline
from earnings_calls.storage.json_file_storage import JsonFileStorage
from earnings_calls.structuring.structurer import _IdentityAndParticipantsResponse, _TurnsResponse
from tests.conftest import FakeLLMClient

_IDENTITY = CallIdentity(
    company='Test Co',
    quarter_name='1Q26',
    call_date=datetime.date(2026, 1, 1),
    quarter_time_range=DateRange(start_date=datetime.date(2025, 11, 1), end_date=datetime.date(2026, 1, 31)),
)


class _FakeExtractor:
    """A stand-in for DoclingPageExtractor that fails for any path containing "bad"."""

    def extract(self, pdf_path: Path, max_pages: int | None = None) -> list[RawPage]:
        if 'bad' in str(pdf_path):
            raise ValueError('simulated extraction failure')
        return [RawPage(page_no=n, text=f'page {n}') for n in range(1, 5)]


def _llm() -> FakeLLMClient:
    speaker = Speaker(name='Jane Doe')
    return FakeLLMClient(
        {
            _IdentityAndParticipantsResponse: _IdentityAndParticipantsResponse(
                identity=_IDENTITY, participants=[speaker]
            ),
            _TurnsResponse: _TurnsResponse(
                turns=[
                    Turn(
                        speaker=speaker,
                        text=[Chunk(page_no=1, text='page 1')],
                        section=Section.MANAGEMENT_DISCUSSION,
                    )
                ]
            ),
        }
    )


def test_run_extracts_structures_checks_and_stores(tmp_path: Path) -> None:
    storage = JsonFileStorage(tmp_path)
    pipeline = TranscriptPipeline(llm=_llm(), storage=storage, extractor=_FakeExtractor())

    transcript = pipeline.run(Path('good.pdf'))

    assert transcript.turns[0].is_grounded is True
    assert storage.load('Test Co', '1Q26') == transcript


def test_run_batch_skips_failed_documents_without_halting(tmp_path: Path) -> None:
    pipeline = TranscriptPipeline(llm=_llm(), storage=JsonFileStorage(tmp_path), extractor=_FakeExtractor())

    results = pipeline.run_batch([Path('good1.pdf'), Path('bad.pdf'), Path('good2.pdf')])

    assert len(results) == 2
