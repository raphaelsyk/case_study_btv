"""Tests for GroundingChecker and check_evidence_grounding - fully deterministic, no
LLM/docling involved.
"""

import datetime

from earnings_calls.analysis.models import Evidence
from earnings_calls.models import CallIdentity, Chunk, DateRange, RawPage, Section, Speaker, Transcript, Turn
from earnings_calls.validation.grounding import GroundingChecker, check_evidence_grounding

_IDENTITY = CallIdentity(
    company='Test Co',
    quarter_name='1Q26',
    call_date=datetime.date(2026, 1, 1),
    quarter_time_range=DateRange(start_date=datetime.date(2025, 11, 1), end_date=datetime.date(2026, 1, 31)),
)
_SPEAKER = Speaker(name='Jane Doe')


def _transcript(chunks: list[Chunk], raw_pages: list[RawPage]) -> Transcript:
    turn = Turn(speaker=_SPEAKER, text=chunks, section=Section.MANAGEMENT_DISCUSSION)
    return Transcript(identity=_IDENTITY, participants=[_SPEAKER], turns=[turn], raw_pages=raw_pages)


def test_verbatim_chunk_is_grounded() -> None:
    transcript = _transcript(
        chunks=[Chunk(page_no=1, text='thank you for joining our earnings call today')],
        raw_pages=[RawPage(page_no=1, text='Good morning everyone, thank you for joining our earnings call today.')],
    )

    GroundingChecker().check(transcript)

    assert transcript.turns[0].is_grounded is True


def test_fabricated_chunk_is_not_grounded() -> None:
    transcript = _transcript(
        chunks=[Chunk(page_no=1, text='we are pleased to announce record profits of one trillion dollars')],
        raw_pages=[RawPage(page_no=1, text='Good morning everyone, thank you for joining our earnings call today.')],
    )

    GroundingChecker().check(transcript)

    assert transcript.turns[0].is_grounded is False


def test_turn_with_chunks_on_different_pages_is_checked_per_chunk() -> None:
    transcript = _transcript(
        chunks=[
            Chunk(page_no=1, text='we delivered strong results this quarter'),
            Chunk(page_no=2, text='revenue growing twelve percent year over year'),
        ],
        raw_pages=[
            RawPage(page_no=1, text='We delivered strong results this quarter, with revenue'),
            RawPage(page_no=2, text='growing twelve percent year over year across all segments.'),
        ],
    )

    GroundingChecker().check(transcript)

    assert [chunk.is_grounded for chunk in transcript.turns[0].text] == [True, True]
    assert transcript.turns[0].is_grounded is True


def test_chunk_attributed_to_the_wrong_page_is_not_grounded() -> None:
    # Regression case for the switch from whole-turn to per-chunk grounding: the old
    # check concatenated every page a turn touched before diffing, so a chunk
    # attributed to the wrong page could still pass because its text existed *somewhere*
    # in the combined blob. Checking each chunk against only its own claimed page
    # catches this.
    transcript = _transcript(
        chunks=[Chunk(page_no=2, text='we delivered strong results this quarter')],
        raw_pages=[
            RawPage(page_no=1, text='We delivered strong results this quarter, with revenue'),
            RawPage(page_no=2, text='growing twelve percent year over year across all segments.'),
        ],
    )

    GroundingChecker().check(transcript)

    assert transcript.turns[0].is_grounded is False


def test_one_ungrounded_chunk_makes_the_whole_turn_ungrounded() -> None:
    transcript = _transcript(
        chunks=[
            Chunk(page_no=1, text='we delivered strong results this quarter'),
            Chunk(page_no=2, text='we invented a time machine last tuesday'),
        ],
        raw_pages=[
            RawPage(page_no=1, text='We delivered strong results this quarter, with revenue'),
            RawPage(page_no=2, text='growing twelve percent year over year across all segments.'),
        ],
    )

    GroundingChecker().check(transcript)

    assert [chunk.is_grounded for chunk in transcript.turns[0].text] == [True, False]
    assert transcript.turns[0].is_grounded is False


def test_check_evidence_grounding_flags_a_verbatim_excerpt_as_grounded() -> None:
    evidence = Evidence(quarter_name='2025_Q1', page_no=1, speaker=_SPEAKER, excerpt='thank you for joining today')
    raw_pages = [RawPage(page_no=1, text='Good morning, thank you for joining today, everyone.')]

    check_evidence_grounding([evidence], raw_pages)

    assert evidence.is_grounded is True


def test_check_evidence_grounding_flags_a_fabricated_excerpt_as_not_grounded() -> None:
    evidence = Evidence(quarter_name='2025_Q1', page_no=1, speaker=_SPEAKER, excerpt='we invented a time machine')
    raw_pages = [RawPage(page_no=1, text='Good morning, thank you for joining today, everyone.')]

    check_evidence_grounding([evidence], raw_pages)

    assert evidence.is_grounded is False


def test_check_evidence_grounding_checks_against_the_excerpts_own_claimed_page() -> None:
    evidence = Evidence(quarter_name='2025_Q1', page_no=2, speaker=_SPEAKER, excerpt='thank you for joining today')
    raw_pages = [
        RawPage(page_no=1, text='thank you for joining today'),
        RawPage(page_no=2, text='revenue grew twelve percent year over year'),
    ]

    check_evidence_grounding([evidence], raw_pages)

    assert evidence.is_grounded is False
