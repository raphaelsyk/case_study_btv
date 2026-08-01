"""Tests for CompanyAnalyzer's orchestration: stage-1 caching, grounding, and the
final report being written - against a FakeLLMClient and a real JsonFileStorage on
disk (tmp_path), deterministic, no real API calls.
"""

import datetime
from pathlib import Path

import pytest

from earnings_calls.analysis.analyzer import CompanyAnalyzer
from earnings_calls.analysis.models import (
    AnalysisSection,
    DistillResponse,
    Evidence,
    QuarterAIAnalysis,
    QuestionAnswer,
    SynthesizeResponse,
    TrendClaim,
    TrendSection,
)
from earnings_calls.models import CallIdentity, Chunk, DateRange, RawPage, Section, Speaker, Transcript, Turn
from earnings_calls.storage.json_file_storage import JsonFileStorage
from tests.conftest import FakeLLMClient

_SPEAKER = Speaker(name='Jeremy Barnum', role='CFO')


def _transcript(quarter_name: str) -> Transcript:
    turn = Turn(
        speaker=_SPEAKER,
        text=[Chunk(page_no=1, text='we are excited about our AI investments')],
        section=Section.MANAGEMENT_DISCUSSION,
    )
    identity = CallIdentity(
        company='JPMorganChase',
        quarter_name=quarter_name,
        call_date=datetime.date(2025, 7, 15),
        quarter_time_range=DateRange(start_date=datetime.date(2025, 4, 1), end_date=datetime.date(2025, 6, 30)),
    )
    return Transcript(
        identity=identity,
        participants=[_SPEAKER],
        turns=[turn],
        raw_pages=[RawPage(page_no=1, text='we are excited about our AI investments this quarter')],
    )


def _draft_response() -> DistillResponse:
    evidence = Evidence(
        quarter_name='ignored', page_no=1, speaker=_SPEAKER, excerpt='we are excited about our AI investments'
    )
    answer = QuestionAnswer(question='How is AI framed?', answer='As a growth driver', evidence=[evidence])
    populated = AnalysisSection(answers=[answer])
    empty = AnalysisSection(answers=[])
    return DistillResponse(
        framing=populated, execution_investment=empty, competitive_landscape=empty, outlook_credibility=empty
    )


def _synthesize_response() -> SynthesizeResponse:
    claim = TrendClaim(text='AI framing intensified', evidence_refs=['2025_Q1#framing#0#0'])
    empty = TrendSection(claims=[])
    return SynthesizeResponse(
        framing=TrendSection(claims=[claim]),
        execution_investment=empty,
        competitive_landscape=empty,
        outlook_credibility=empty,
    )


def _llm() -> FakeLLMClient:
    return FakeLLMClient({DistillResponse: _draft_response(), SynthesizeResponse: _synthesize_response()})


def test_analyze_writes_a_markdown_and_pdf_report(tmp_path: Path) -> None:
    storage = JsonFileStorage(tmp_path / 'structured')
    storage.save(_transcript('2025_Q1'))
    output_root = tmp_path / 'analysis'

    report_path = CompanyAnalyzer(_llm(), storage, output_root).analyze('jpmorganchase')

    assert report_path == output_root / 'jpmorganchase' / 'report.md'
    assert report_path.exists()
    assert (output_root / 'jpmorganchase' / 'report.pdf').exists()
    assert 'AI framing intensified' in report_path.read_text()


def test_analyze_grounding_checks_and_caches_stage_one_output(tmp_path: Path) -> None:
    storage = JsonFileStorage(tmp_path / 'structured')
    storage.save(_transcript('2025_Q1'))
    output_root = tmp_path / 'analysis'

    CompanyAnalyzer(_llm(), storage, output_root).analyze('jpmorganchase')

    cache_path = output_root / 'jpmorganchase' / '_cache' / '2025_Q1.json'
    cached = QuarterAIAnalysis.model_validate_json(cache_path.read_text())
    assert cached.framing.answers[0].evidence[0].is_grounded is True


def test_analyze_reuses_cached_stage_one_output_on_a_second_run(tmp_path: Path) -> None:
    storage = JsonFileStorage(tmp_path / 'structured')
    storage.save(_transcript('2025_Q1'))
    output_root = tmp_path / 'analysis'
    llm = _llm()

    CompanyAnalyzer(llm, storage, output_root).analyze('jpmorganchase')
    prompts_after_first_run = len(llm.prompts)
    CompanyAnalyzer(llm, storage, output_root).analyze('jpmorganchase')

    # Only stage 2 (synthesize) re-runs on the second call - stage 1 (distill) is cached.
    assert len(llm.prompts) == prompts_after_first_run + 1


def test_analyze_raises_for_a_company_with_no_stored_transcripts(tmp_path: Path) -> None:
    storage = JsonFileStorage(tmp_path / 'structured')
    output_root = tmp_path / 'analysis'

    with pytest.raises(ValueError, match='no stored transcripts'):
        CompanyAnalyzer(_llm(), storage, output_root).analyze('jpmorganchase')
