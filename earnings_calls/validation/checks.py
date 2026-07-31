"""Shared plausibility checks for a structured transcript.

Used both as Transcript's pydantic validator (earnings_calls.models) and directly in
pytest regression tests, so a parsing regression is caught the same way in both places
instead of only being checked once in CI and never again at real pipeline runtime.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # Deferred import: earnings_calls.models imports this module, so importing it back
    # here at runtime would be circular. Only needed for static type checking.
    from earnings_calls.models import Chunk, RawPage, Speaker


def assert_participants_present(participants: Sequence['Speaker']) -> None:
    """Fails if the reconciled participant list is empty."""
    assert participants, 'transcript has no participants'


def assert_chunks_present(chunks: Sequence['Chunk']) -> None:
    """Fails if no dialogue chunks were extracted at all."""
    assert chunks, 'transcript has no chunks'


def assert_chunk_count_plausible(chunks: Sequence['Chunk'], page_count: int) -> None:
    """Fails if the chunk count looks wildly under-segmented relative to the page count.

    A rough heuristic (at least one chunk per four pages), not meant to be precise -
    only to catch a structuring call that returned a near-empty or truncated result.
    """
    assert page_count > 0, 'transcript has no raw pages'
    min_expected = max(1, page_count // 4)
    assert len(chunks) >= min_expected, (
        f'only {len(chunks)} chunks for {page_count} pages, expected at least {min_expected}'
    )


def assert_chunk_pages_within_raw_pages(chunks: Sequence['Chunk'], raw_pages: Sequence['RawPage']) -> None:
    """Fails if a chunk cites a page number that was never extracted."""
    known_pages = {page.page_no for page in raw_pages}
    for chunk in chunks:
        unknown = set(chunk.pages) - known_pages
        assert not unknown, f'chunk for {chunk.speaker.name} references unknown pages: {sorted(unknown)}'


def normalize_speaker_name(name: str) -> str:
    """Collapses whitespace and case so e.g. "JANE DOE" and "Jane Doe" compare equal.

    Sources format the same speaker's name differently between an upfront roster
    (usually title case) and inline Q&A labels (often ALL CAPS) - see
    TranscriptStructurer._reconcile_participants, which relies on this same
    normalization to avoid folding one person into two participant entries.
    """
    return ' '.join(name.split()).casefold()


def assert_all_speakers_known(chunks: Sequence['Chunk'], participants: Sequence['Speaker']) -> None:
    """Fails if a chunk's speaker was not folded into the participants list.

    Guards the participant reconciliation step in TranscriptStructurer - every speaker
    that gets a chunk must end up in `participants` (see 03_system_design_data_model.md).
    """
    known_names = {normalize_speaker_name(p.name) for p in participants}
    unknown = {chunk.speaker.name for chunk in chunks if normalize_speaker_name(chunk.speaker.name) not in known_names}
    assert not unknown, f'chunk speakers missing from participants: {sorted(unknown)}'


def validate_transcript(
    chunks: Sequence['Chunk'],
    participants: Sequence['Speaker'],
    raw_pages: Sequence['RawPage'],
) -> None:
    """Runs every plausibility check for a structured transcript, raising on the first failure."""
    assert_participants_present(participants)
    assert_chunks_present(chunks)
    assert_chunk_count_plausible(chunks, len(raw_pages))
    assert_chunk_pages_within_raw_pages(chunks, raw_pages)
    assert_all_speakers_known(chunks, participants)
