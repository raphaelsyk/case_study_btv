"""Stage 2 of the Analyzer: synthesizes a cross-quarter AI-trend report from a
company's cached stage-1 analyses.

Only ever sees the small, already-AI-filtered evidence catalogue below - never raw
transcript text - and may only cite existing evidence by id, never retype excerpt
text. See the "Analyzer Module" decision in system_design/02_system_design.md.
"""

from earnings_calls.analysis import prompts
from earnings_calls.analysis.evidence_catalogue import EvidenceCatalogue
from earnings_calls.analysis.models import (
    CompanyAIExposureTrendReport,
    QuarterAIAnalysis,
    SynthesizeResponse,
)
from earnings_calls.llm_client import LLMClient


class TrendSynthesizer:
    """Synthesizes a company's cross-quarter AI-trend report from stage-1 analyses."""

    def __init__(self, llm: LLMClient) -> None:
        self._llm = llm

    def synthesize(self, quarters: list[QuarterAIAnalysis]) -> tuple[CompanyAIExposureTrendReport, EvidenceCatalogue]:
        """Runs the stage-2 synthesize call over a company's chronological quarters.

        Args:
            quarters: One QuarterAIAnalysis per quarter, chronologically ordered.

        Returns:
            The synthesized trend report and the EvidenceCatalogue it was built from -
            `report_builder` needs the catalogue to resolve `evidence_refs` at render time.

        Raises:
            ValueError: If `quarters` is empty.
        """
        if not quarters:
            raise ValueError('cannot synthesize a trend report from zero quarters')
        catalogue = EvidenceCatalogue(quarters)
        quarter_names = [quarter.quarter_name for quarter in quarters]
        prompt = prompts.synthesize_prompt(
            company=quarters[0].company,
            quarter_names=quarter_names,
            catalogue_text=catalogue.render_for_prompt(),
        )
        response = self._llm.generate_structured(prompt, SynthesizeResponse)
        report = CompanyAIExposureTrendReport(
            company=quarters[0].company,
            quarters_covered=quarter_names,
            framing=response.framing,
            execution_investment=response.execution_investment,
            competitive_landscape=response.competitive_landscape,
            outlook_credibility=response.outlook_credibility,
        )
        return report, catalogue
