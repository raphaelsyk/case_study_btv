"""Stage 1 of the Analyzer: distills one quarter's transcript into a structured,
citeable AI-discussion analysis.

Built only from a Transcript's `identity`, `participants`, and `turns` - never
`raw_pages`, which has no speaker attribution and so cannot back an `Evidence` item.
"""

from collections.abc import Sequence

from pydantic import BaseModel

from earnings_calls.analysis import prompts
from earnings_calls.analysis.models import AnalysisSection, QuarterAIAnalysis
from earnings_calls.analysis.sector import sector_for_company
from earnings_calls.llm_client import LLMClient
from earnings_calls.models import Transcript, Turn


class _DistillResponse(BaseModel):
    """Response shape for the stage-1 distill call.

    `company`/`quarter_name` and each evidence item's `quarter_name` are set
    afterward, deterministically, from the source Transcript rather than trusted to
    the LLM - see `QuarterDistiller.distill`.
    """

    framing: AnalysisSection
    operations_summary: AnalysisSection
    context: AnalysisSection
    commitments_outlook: AnalysisSection


_SECTION_NAMES = ('framing', 'operations_summary', 'context', 'commitments_outlook')


class QuarterDistiller:
    """Distills a single quarter's Transcript into a structured QuarterAIAnalysis."""

    def __init__(self, llm: LLMClient) -> None:
        self._llm = llm

    def distill(self, transcript: Transcript, company_slug: str) -> QuarterAIAnalysis:
        """Runs the stage-1 distill call for one quarter.

        Args:
            transcript: The quarter's structured transcript.
            company_slug: The storage slug used to pick the sector-specific prompt.
        Returns:
            The quarter's structured AI-discussion analysis.
        """
        sector = sector_for_company(company_slug)
        tagged_turns = self._render_turns(transcript.turns)
        prompt = prompts.distill_prompt(
            sector=sector,
            company=transcript.identity.company,
            quarter_name=transcript.identity.quarter_name,
            tagged_turns=tagged_turns,
        )
        response = self._llm.generate_structured(prompt, _DistillResponse)
        quarter_name = transcript.identity.quarter_name
        for section_name in _SECTION_NAMES:
            section: AnalysisSection = getattr(response, section_name)
            for evidence in section.evidence:
                evidence.quarter_name = quarter_name
        return QuarterAIAnalysis(
            company=transcript.identity.company,
            quarter_name=quarter_name,
            framing=response.framing,
            operations_summary=response.operations_summary,
            context=response.context,
            commitments_outlook=response.commitments_outlook,
        )

    @staticmethod
    def _render_turns(turns: Sequence[Turn]) -> str:
        """Renders turns as speaker- and page-tagged text for the distill prompt.

        Deliberately built only from `Transcript.turns`, never `raw_pages` (see the
        module docstring).
        """
        rendered_turns = []
        for turn in turns:
            speaker_label = turn.speaker.name
            details = ', '.join(part for part in (turn.speaker.role, turn.speaker.company) if part)
            if details:
                speaker_label = f'{speaker_label} ({details})'
            chunks = '\n'.join(f'<page {chunk.page_no}>\n{chunk.text}\n</page {chunk.page_no}>' for chunk in turn.text)
            rendered_turns.append(f'<turn speaker="{speaker_label}" section="{turn.section.value}">\n{chunks}\n</turn>')
        return '\n'.join(rendered_turns)
