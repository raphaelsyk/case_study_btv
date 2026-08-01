"""Orchestrates the two-call structuring flow: raw pages -> validated Transcript."""

from collections.abc import Sequence

from pydantic import BaseModel, Field

from earnings_calls.llm_client import LLMClient
from earnings_calls.models import CallIdentity, RawPage, Speaker, Transcript, Turn
from earnings_calls.pipeline.structuring import prompts
from earnings_calls.validation.checks import normalize_speaker_name

IDENTITY_CALL_PAGE_COUNT = 3


class _IdentityAndParticipantsResponse(BaseModel):
    """Response shape for the call-identity + participant-roster structuring call."""

    identity: CallIdentity
    participants: list[Speaker] = Field(default_factory=list)


class _TurnsResponse(BaseModel):
    """Response shape for the full turn-segmentation structuring call."""

    turns: list[Turn]


class TranscriptStructurer:
    """Turns per-page raw text into a fully structured, validated Transcript."""

    def __init__(self, llm: LLMClient) -> None:
        self._llm = llm

    def structure(self, pages: Sequence[RawPage]) -> Transcript:
        """Runs both structuring calls and assembles a validated Transcript.

        Args:
            pages: Per-page raw text as extracted by DoclingPageExtractor, in page order.

        Returns:
            A Transcript with reconciled participants and page-tagged turns.
        """
        identity_response = self._llm.generate_structured(
            prompts.identity_and_participants_prompt(self._tag_pages(pages[:IDENTITY_CALL_PAGE_COUNT])),
            _IdentityAndParticipantsResponse,
        )
        turns_response = self._llm.generate_structured(
            prompts.turn_segmentation_prompt(self._tag_pages(pages)),
            _TurnsResponse,
        )
        participants = self._reconcile_participants(identity_response.participants, turns_response.turns)
        return Transcript(
            identity=identity_response.identity,
            participants=participants,
            turns=turns_response.turns,
            raw_pages=list(pages),
        )

    @staticmethod
    def _tag_pages(pages: Sequence[RawPage]) -> str:
        """Joins pages into one string, each wrapped in <page N>...</page N> tags."""
        return '\n'.join(f'<page {page.page_no}>\n{page.text}\n</page {page.page_no}>' for page in pages)

    @staticmethod
    def _reconcile_participants(roster: Sequence[Speaker], turns: Sequence[Turn]) -> list[Speaker]:
        """Unions the upfront roster with every distinct turn speaker.

        Turn speakers missing from the roster are added; roster entries who never
        speak are kept. Matched by normalized name, since the same person is often
        cased differently between an upfront roster (title case) and inline Q&A
        labels (often ALL CAPS) - e.g. "Jane Doe" vs. "JANE DOE" would otherwise
        fold in as two people.
        """
        by_normalized_name: dict[str, Speaker] = {}
        for speaker in roster:
            by_normalized_name[normalize_speaker_name(speaker.name)] = speaker
        for turn in turns:
            by_normalized_name.setdefault(normalize_speaker_name(turn.speaker.name), turn.speaker)
        return list(by_normalized_name.values())
