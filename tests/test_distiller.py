"""Tests for QuarterDistiller's deterministic field backfill and LLM-input scoping,
against a FakeLLMClient - deterministic, no real API calls.
"""

import datetime

from earnings_calls.analysis.distiller import QuarterDistiller
from earnings_calls.analysis.models import AnalysisSection, DistillResponse, Evidence, QuestionAnswer
from earnings_calls.models import CallIdentity, Chunk, DateRange, RawPage, Section, Speaker, Transcript, Turn
from tests.conftest import FakeLLMClient

_IDENTITY = CallIdentity(
    company='JPMorganChase',
    quarter_name='2025_Q2',
    call_date=datetime.date(2025, 7, 15),
    quarter_time_range=DateRange(start_date=datetime.date(2025, 4, 1), end_date=datetime.date(2025, 6, 30)),
)
_SPEAKER = Speaker(name='Jeremy Barnum', role='CFO')


def _transcript(raw_page_text: str = 'super-secret raw page text never sent to the LLM') -> Transcript:
    turn = Turn(
        speaker=_SPEAKER,
        text=[Chunk(page_no=1, text='we are excited about our AI investments')],
        section=Section.MANAGEMENT_DISCUSSION,
    )
    return Transcript(
        identity=_IDENTITY,
        participants=[_SPEAKER],
        turns=[turn],
        raw_pages=[RawPage(page_no=1, text=raw_page_text)],
    )


def _draft_response(evidence_quarter_name: str = 'WRONG_QUARTER') -> DistillResponse:
    evidence = Evidence(quarter_name=evidence_quarter_name, page_no=1, speaker=_SPEAKER, excerpt='AI investments')
    answer = QuestionAnswer(question='How is AI framed?', answer='As a growth driver', evidence=[evidence])
    populated = AnalysisSection(answers=[answer])
    empty = AnalysisSection(answers=[])
    return DistillResponse(
        framing=populated, execution_investment=empty, competitive_landscape=empty, outlook_credibility=empty
    )


def _llm(response: DistillResponse) -> FakeLLMClient:
    return FakeLLMClient({DistillResponse: response})


def test_distill_backfills_company_and_quarter_name_from_transcript_identity() -> None:
    analysis = QuarterDistiller(_llm(_draft_response())).distill(_transcript(), company_slug='jpmorganchase')

    assert analysis.company == 'JPMorganChase'
    assert analysis.quarter_name == '2025_Q2'


def test_distill_backfills_evidence_quarter_name_even_if_the_llm_got_it_wrong() -> None:
    # The LLM's own quarter_name output is untrusted and overwritten deterministically -
    # this is what stage 2's evidence catalogue keys rely on being correct.
    llm = _llm(_draft_response(evidence_quarter_name='WRONG_QUARTER'))

    analysis = QuarterDistiller(llm).distill(_transcript(), company_slug='jpmorganchase')

    assert analysis.framing.answers[0].evidence[0].quarter_name == '2025_Q2'


def test_distill_prompt_never_includes_raw_page_text() -> None:
    # Core requirement: stage-1 LLM input is built only from identity/participants/
    # turns, never raw_pages (see the "Analyzer Module" decision in
    # system_design/02_system_design.md).
    llm = _llm(_draft_response())
    transcript = _transcript(raw_page_text='super-secret raw page text never sent to the LLM')

    QuarterDistiller(llm).distill(transcript, company_slug='jpmorganchase')

    assert 'super-secret raw page text never sent to the LLM' not in llm.prompts[0]
    assert 'we are excited about our AI investments' in llm.prompts[0]


def test_distill_dispatches_bank_questions_for_a_bank_company() -> None:
    llm = _llm(_draft_response())

    QuarterDistiller(llm).distill(_transcript(), company_slug='jpmorganchase')

    assert 'Visibility:' in llm.prompts[0]
    assert 'sovereign AI' not in llm.prompts[0]


def test_distill_dispatches_tech_questions_for_a_tech_company() -> None:
    llm = _llm(_draft_response())

    QuarterDistiller(llm).distill(_transcript(), company_slug='nvidia_corp')

    assert 'sovereign AI' in llm.prompts[0]
