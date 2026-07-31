"""Pydantic data model for a structured earnings-call transcript.

See system_design/03_system_design_data_model.md for the design rationale.
"""

from datetime import date
from enum import Enum

from pydantic import BaseModel, Field, computed_field, model_validator

from earnings_calls.validation.checks import validate_transcript


class RawPage(BaseModel):
    """One physical PDF page as extracted by docling, before any structuring."""

    page_no: int = Field(gt=0)
    text: str


class Speaker(BaseModel):
    """A person on the call. Reused for both the participant roster and chunk speakers."""

    name: str
    role: str | None = None
    company: str | None = None


class DateRange(BaseModel):
    """An inclusive calendar date range, e.g. the fiscal quarter an earnings call covers."""

    start_date: date = Field(description='A starting date as ISO 8601, (YYYY-MM-DD)')
    end_date: date = Field(description='An end date as ISO 8601, (YYYY-MM-DD)')


class CallIdentity(BaseModel):
    """Identity of the earnings call: who, and for which quarter."""

    company: str
    quarter_name: str = Field(description='The quarter that is reported on, formatted as [YYYY]_Q[Q], e.g. 2025_Q2')
    call_date: date = Field(description='The date of the earnings call')
    quarter_time_range: DateRange = Field(description='The timespan of the quarter discussed in the call')


class ChunkSection(str, Enum):
    """Which part of the call a chunk belongs to."""

    MANAGEMENT_DISCUSSION = 'management_discussion'
    QA = 'qa'


class QAType(str, Enum):
    """Whether a Q&A chunk is the analyst's question or management's answer."""

    QUESTION = 'question'
    ANSWER = 'answer'


class ChunkSegment(BaseModel):
    """One page's worth of a chunk's text, so a turn's text stays anchored to its exact
    source page even when a turn spans several pages (docling's page_range numbering).
    """

    page_no: int = Field(ge=1, description='Physical PDF page this segment is on, matching a <page N> tag')
    text: str
    is_grounded: bool | None = None


class Chunk(BaseModel):
    """One continuous speaker turn. Never split at a page boundary — `text` lists one
    segment per physical PDF page the turn touches, in order.
    """

    speaker: Speaker
    text: list[ChunkSegment] = Field(min_length=1)
    section: ChunkSection
    qa_type: QAType | None = None

    @computed_field
    @property
    def pages(self) -> list[int]:
        """Every physical page this chunk's turn touches, in order."""
        return [segment.page_no for segment in self.text]

    @computed_field
    @property
    def is_grounded(self) -> bool | None:
        """None until grounding-checked; else True only if every segment is grounded."""
        statuses = [segment.is_grounded for segment in self.text]
        return None if any(status is None for status in statuses) else all(statuses)


class Transcript(BaseModel):
    """A fully structured earnings-call transcript.

    `participants` is the reconciled union of any upfront roster and every distinct
    speaker found while tagging chunks (see structuring.structurer.TranscriptStructurer).
    `raw_pages` is docling's independently-extracted per-page text, kept alongside the
    structured fields so grounding/citation checks have ground truth to check against.
    """

    identity: CallIdentity
    participants: list[Speaker]
    chunks: list[Chunk]
    raw_pages: list[RawPage]

    @model_validator(mode='after')
    def _check_plausible(self) -> 'Transcript':
        """Rejects a structurally implausible transcript rather than storing it silently."""
        validate_transcript(chunks=self.chunks, participants=self.participants, raw_pages=self.raw_pages)
        return self
