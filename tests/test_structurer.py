"""Tests for TranscriptStructurer's orchestration and participant reconciliation logic
against a FakeLLMClient - deterministic, no real API calls.
"""

import datetime

from earnings_calls.models import CallIdentity, Chunk, DateRange, QAType, RawPage, Section, Speaker, Turn
from earnings_calls.structuring.structurer import (
    TranscriptStructurer,
    _IdentityAndParticipantsResponse,
    _TurnsResponse,
)
from tests.conftest import FakeLLMClient

_IDENTITY = CallIdentity(
    company='JPMorgan',
    quarter_name='2025_Q2',
    call_date=datetime.date(2025, 7, 15),
    quarter_time_range=DateRange(start_date=datetime.date(2025, 4, 1), end_date=datetime.date(2025, 6, 30)),
)


def _pages(count: int) -> list[RawPage]:
    return [RawPage(page_no=n, text=f'page {n} text') for n in range(1, count + 1)]


def _llm(roster: list[Speaker], turns: list[Turn]) -> FakeLLMClient:
    return FakeLLMClient(
        {
            _IdentityAndParticipantsResponse: _IdentityAndParticipantsResponse(identity=_IDENTITY, participants=roster),
            _TurnsResponse: _TurnsResponse(turns=turns),
        }
    )


def test_structure_reconciles_participants_as_a_union_with_role_backfill() -> None:
    roster = [Speaker(name='Jeremy Barnum', role='CFO', company='JPMorganChase')]
    turns = [
        Turn(speaker=roster[0], text=[Chunk(page_no=1, text='...')], section=Section.MANAGEMENT_DISCUSSION),
        Turn(
            speaker=Speaker(name='Christopher McGratty', role='Analyst', company='KBW'),
            text=[Chunk(page_no=3, text='...')],
            section=Section.QA,
            qa_type=QAType.QUESTION,
        ),
    ]

    transcript = TranscriptStructurer(_llm(roster, turns)).structure(_pages(5))

    names = {p.name for p in transcript.participants}
    assert names == {'Jeremy Barnum', 'Christopher McGratty'}
    mcgratty = next(p for p in transcript.participants if p.name == 'Christopher McGratty')
    assert (mcgratty.role, mcgratty.company) == ('Analyst', 'KBW')


def test_structure_matches_roster_and_turn_speaker_case_insensitively() -> None:
    # Regression test: found against a real Microsoft transcript, where the upfront
    # roster uses title case ("Jonathan Neilson") but inline Q&A labels are ALL CAPS
    # ("JONATHAN NEILSON, Company:"). Without case-insensitive matching, the same
    # person was folded in twice - once with role info, once without.
    roster = [Speaker(name='Jonathan Neilson', role='Investor Relations')]
    turns = [
        Turn(
            speaker=Speaker(name='JONATHAN NEILSON'),
            text=[Chunk(page_no=1, text='...')],
            section=Section.MANAGEMENT_DISCUSSION,
        )
    ]

    transcript = TranscriptStructurer(_llm(roster, turns)).structure(_pages(3))

    assert len(transcript.participants) == 1
    assert transcript.participants[0].role == 'Investor Relations'


def test_structure_keeps_roster_participants_who_never_speak() -> None:
    roster = [
        Speaker(name='Jeremy Barnum', role='CFO', company='JPMorganChase'),
        Speaker(name='Corporate Secretary', role='Secretary', company='JPMorganChase'),
    ]
    turns = [Turn(speaker=roster[0], text=[Chunk(page_no=1, text='...')], section=Section.MANAGEMENT_DISCUSSION)]

    transcript = TranscriptStructurer(_llm(roster, turns)).structure(_pages(3))

    assert {p.name for p in transcript.participants} == {'Jeremy Barnum', 'Corporate Secretary'}


def test_structure_limits_identity_call_to_first_pages_but_not_the_turn_call() -> None:
    roster = [Speaker(name='Jane Doe')]
    turns = [Turn(speaker=roster[0], text=[Chunk(page_no=1, text='...')], section=Section.MANAGEMENT_DISCUSSION)]
    llm = _llm(roster, turns)

    TranscriptStructurer(llm).structure(_pages(5))

    identity_prompt, turn_prompt = llm.prompts
    assert '<page 4>' not in identity_prompt
    assert '<page 4>' in turn_prompt
