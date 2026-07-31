"""Orchestrates the two-call structuring flow: raw pages -> validated Transcript."""

from collections.abc import Sequence

from pydantic import BaseModel, Field

from earnings_calls.llm_client import LLMClient
from earnings_calls.models import CallIdentity, Chunk, RawPage, Speaker, Transcript
from earnings_calls.structuring import prompts
from earnings_calls.validation.checks import normalize_speaker_name

# First N pages sent to the identity/participants call - covers the title page plus the
# page 2 participant roster some sources (NVDA, BAC) use.
IDENTITY_CALL_PAGE_COUNT = 3


class _IdentityAndParticipantsResponse(BaseModel):
    """Response shape for the call-identity + participant-roster structuring call."""

    identity: CallIdentity
    participants: list[Speaker] = Field(default_factory=list)


class _ChunksResponse(BaseModel):
    """Response shape for the full chunk-segmentation structuring call."""

    chunks: list[Chunk]


class TranscriptStructurer:
    """Turns per-page raw text into a fully structured, validated Transcript."""

    def __init__(self, llm: LLMClient) -> None:
        self._llm = llm

    def structure(self, pages: Sequence[RawPage]) -> Transcript:
        """Runs both structuring calls and assembles a validated Transcript.

        Args:
            pages: Per-page raw text as extracted by DoclingPageExtractor, in page order.

        Returns:
            A Transcript with reconciled participants and page-tagged chunks.
        """
        identity_response = self._llm.generate_structured(
            prompts.identity_and_participants_prompt(self._tag_pages(pages[:IDENTITY_CALL_PAGE_COUNT])),
            _IdentityAndParticipantsResponse,
        )
        chunks_response = self._llm.generate_structured(
            prompts.chunk_segmentation_prompt(self._tag_pages(pages)),
            _ChunksResponse,
        )
        participants = self._reconcile_participants(identity_response.participants, chunks_response.chunks)
        return Transcript(
            identity=identity_response.identity,
            participants=participants,
            chunks=chunks_response.chunks,
            raw_pages=list(pages),
        )

    @staticmethod
    def _tag_pages(pages: Sequence[RawPage]) -> str:
        """Joins pages into one string, each wrapped in <page N>...</page N> tags."""
        return '\n'.join(f'<page {page.page_no}>\n{page.text}\n</page {page.page_no}>' for page in pages)

    @staticmethod
    def _reconcile_participants(roster: Sequence[Speaker], chunks: Sequence[Chunk]) -> list[Speaker]:
        """Unions the upfront roster with every distinct chunk speaker.

        Chunk speakers missing from the roster are added, carrying whatever role/company
        the chunk-segmentation call recovered for them; roster entries who never speak
        are kept (see the participants-reconciliation decision in
        03_system_design_data_model.md). Matched by normalized name, since the same
        person is often cased differently between an upfront roster (title case) and
        inline Q&A speaker labels (often ALL CAPS) - without this, e.g. "Jane Doe" from
        the roster and "JANE DOE" from a chunk would be folded in as two different people.
        """
        by_normalized_name: dict[str, Speaker] = {}
        for speaker in roster:
            by_normalized_name[normalize_speaker_name(speaker.name)] = speaker
        for chunk in chunks:
            by_normalized_name.setdefault(normalize_speaker_name(chunk.speaker.name), chunk.speaker)
        return list(by_normalized_name.values())
