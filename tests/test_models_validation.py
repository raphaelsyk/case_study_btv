"""Tests for Transcript's plausibility validators (earnings_calls.validation.checks) -
the "written once, used as both a pydantic validator and a pytest assertion" checks
from the design discussion in system_design/02_system_design.md.
"""

import datetime

import pytest
from pydantic import ValidationError

from earnings_calls.models import CallIdentity, Chunk, DateRange, RawPage, Section, Speaker, Transcript, Turn

_IDENTITY = CallIdentity(
    company='Test Co',
    quarter_name='1Q26',
    call_date=datetime.date(2026, 1, 1),
    quarter_time_range=DateRange(start_date=datetime.date(2025, 11, 1), end_date=datetime.date(2026, 1, 31)),
)


def _raw_pages(count: int) -> list[RawPage]:
    return [RawPage(page_no=n, text=f'page {n} text') for n in range(1, count + 1)]


def _valid_transcript_kwargs() -> dict:
    speaker = Speaker(name='Jane Doe', role='CFO')
    turns = [
        Turn(speaker=speaker, text=[Chunk(page_no=n, text=f'turn {n}')], section=Section.MANAGEMENT_DISCUSSION)
        for n in range(1, 3)
    ]
    return {'identity': _IDENTITY, 'participants': [speaker], 'turns': turns, 'raw_pages': _raw_pages(8)}


def test_valid_transcript_constructs() -> None:
    Transcript(**_valid_transcript_kwargs())


def test_rejects_empty_participants() -> None:
    kwargs = _valid_transcript_kwargs()
    kwargs['participants'] = []

    with pytest.raises(ValidationError, match='no participants'):
        Transcript(**kwargs)


def test_rejects_turn_speaker_missing_from_participants() -> None:
    kwargs = _valid_transcript_kwargs()
    kwargs['turns'].append(Turn(speaker=Speaker(name='Ghost'), text=[Chunk(page_no=1, text='x')], section=Section.QA))

    with pytest.raises(ValidationError, match='missing from participants'):
        Transcript(**kwargs)


def test_rejects_turn_page_not_in_raw_pages() -> None:
    kwargs = _valid_transcript_kwargs()
    kwargs['turns'][0] = kwargs['turns'][0].model_copy(update={'text': [Chunk(page_no=999, text='x')]})

    with pytest.raises(ValidationError, match='unknown pages'):
        Transcript(**kwargs)


def test_rejects_severely_undersegmented_turns() -> None:
    kwargs = _valid_transcript_kwargs()
    kwargs['raw_pages'] = _raw_pages(40)  # far more pages than 2 turns can plausibly cover

    with pytest.raises(ValidationError, match='expected at least'):
        Transcript(**kwargs)
