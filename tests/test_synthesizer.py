"""Tests for TrendSynthesizer's deterministic field backfill and evidence-catalogue
wiring, against a FakeLLMClient - deterministic, no real API calls.
"""

import pytest

from earnings_calls.analysis.models import AnalysisSection, Evidence, QuarterAIAnalysis, TrendClaim, TrendSection
from earnings_calls.analysis.synthesizer import TrendSynthesizer, _SynthesizeResponse
from earnings_calls.models import Speaker
from tests.conftest import FakeLLMClient

_SPEAKER = Speaker(name='Jane Doe', role='CFO')


def _quarter(quarter_name: str) -> QuarterAIAnalysis:
    evidence = Evidence(
        quarter_name=quarter_name, page_no=1, speaker=_SPEAKER, excerpt='we invest heavily in AI', is_grounded=True
    )
    populated = AnalysisSection(narrative='AI framed as a growth driver', evidence=[evidence])
    empty = AnalysisSection(narrative='not discussed')
    return QuarterAIAnalysis(
        company='Test Co',
        quarter_name=quarter_name,
        framing=populated,
        operations_summary=empty,
        context=empty,
        commitments_outlook=empty,
    )


def _synthesize_response() -> _SynthesizeResponse:
    claim = TrendClaim(text='AI framing intensified over time', evidence_refs=['2025_Q1#framing#0'])
    empty = TrendSection(claims=[])
    return _SynthesizeResponse(
        framing=TrendSection(claims=[claim]), operations_summary=empty, context=empty, commitments_outlook=empty
    )


def _llm() -> FakeLLMClient:
    return FakeLLMClient({_SynthesizeResponse: _synthesize_response()})


def test_synthesize_backfills_company_and_quarters_covered() -> None:
    report, _ = TrendSynthesizer(_llm()).synthesize([_quarter('2025_Q1'), _quarter('2025_Q2')])

    assert report.company == 'Test Co'
    assert report.quarters_covered == ['2025_Q1', '2025_Q2']


def test_synthesize_prompt_carries_catalogue_evidence_not_raw_transcript_text() -> None:
    llm = _llm()

    TrendSynthesizer(llm).synthesize([_quarter('2025_Q1')])

    assert '2025_Q1#framing#0' in llm.prompts[0]
    assert 'we invest heavily in AI' in llm.prompts[0]


def test_synthesize_returns_the_catalogue_it_was_built_from() -> None:
    _, catalogue = TrendSynthesizer(_llm()).synthesize([_quarter('2025_Q1')])

    evidence = catalogue.resolve('2025_Q1#framing#0')
    assert evidence is not None
    assert evidence.excerpt == 'we invest heavily in AI'


def test_synthesize_raises_on_empty_quarters() -> None:
    with pytest.raises(ValueError, match='zero quarters'):
        TrendSynthesizer(FakeLLMClient({})).synthesize([])
