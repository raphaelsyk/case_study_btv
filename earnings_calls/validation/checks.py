"""Shared plausibility checks for a structured transcript.

Used both as Transcript's pydantic validator and directly in pytest regression
tests, so a parsing regression is caught the same way in both places.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # Avoids a circular import: earnings_calls.models imports this module.
    from earnings_calls.models import RawPage, Speaker, Turn


def assert_participants_present(participants: Sequence['Speaker']) -> None:
    """Fails if the reconciled participant list is empty."""
    assert participants, 'transcript has no participants'


def assert_turns_present(turns: Sequence['Turn']) -> None:
    """Fails if no dialogue turns were extracted at all."""
    assert turns, 'transcript has no turns'


def assert_turn_count_plausible(turns: Sequence['Turn'], page_count: int) -> None:
    """Fails if the turn count looks wildly under-segmented relative to the page count.

    A rough heuristic (at least one turn per four pages), not meant to be precise -
    only to catch a structuring call that returned a near-empty or truncated result.
    """
    assert page_count > 0, 'transcript has no raw pages'
    min_expected = max(1, page_count // 4)
    assert len(turns) >= min_expected, (
        f'only {len(turns)} turns for {page_count} pages, expected at least {min_expected}'
    )


def assert_turn_pages_within_raw_pages(turns: Sequence['Turn'], raw_pages: Sequence['RawPage']) -> None:
    """Fails if a turn cites a page number that was never extracted."""
    known_pages = {page.page_no for page in raw_pages}
    for turn in turns:
        unknown = set(turn.pages) - known_pages
        assert not unknown, f'turn for {turn.speaker.name} references unknown pages: {sorted(unknown)}'


def normalize_speaker_name(name: str) -> str:
    """Collapses whitespace and case so e.g. "JANE DOE" and "Jane Doe" compare equal.

    Used by TranscriptStructurer._reconcile_participants to avoid folding one
    person into two participant entries due to inconsistent casing across sources.
    """
    return ' '.join(name.split()).casefold()


def assert_all_speakers_known(turns: Sequence['Turn'], participants: Sequence['Speaker']) -> None:
    """Fails if a turn's speaker was not folded into the participants list.

    Guards the participant reconciliation step in TranscriptStructurer - every
    speaker that gets a turn must end up in `participants`.
    """
    known_names = {normalize_speaker_name(p.name) for p in participants}
    unknown = {turn.speaker.name for turn in turns if normalize_speaker_name(turn.speaker.name) not in known_names}
    assert not unknown, f'turn speakers missing from participants: {sorted(unknown)}'


def validate_transcript(
    turns: Sequence['Turn'],
    participants: Sequence['Speaker'],
    raw_pages: Sequence['RawPage'],
) -> None:
    """Runs every plausibility check for a structured transcript, raising on the first failure."""
    assert_participants_present(participants)
    assert_turns_present(turns)
    assert_turn_count_plausible(turns, len(raw_pages))
    assert_turn_pages_within_raw_pages(turns, raw_pages)
    assert_all_speakers_known(turns, participants)
