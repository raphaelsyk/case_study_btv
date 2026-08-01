"""Top-level orchestration for the Analyzer: a company's stored transcripts -> a
cited, cross-quarter AI-discussion trend report.

Mirrors `earnings_calls.pipeline.TranscriptPipeline`'s shape: wires the stage-1/
stage-2 LLM calls, caches stage-1 output to disk so a new quarter doesn't require
re-distilling the whole company, and writes the final rendered report.
"""

import logging
from pathlib import Path

from earnings_calls.analysis.distiller import QuarterDistiller
from earnings_calls.analysis.models import AnalysisSection, Evidence, QuarterAIAnalysis
from earnings_calls.analysis.report_builder import ReportBuilder
from earnings_calls.analysis.synthesizer import TrendSynthesizer
from earnings_calls.llm_client import LLMClient
from earnings_calls.models import Transcript
from earnings_calls.storage.interface import TranscriptStorage
from earnings_calls.validation.grounding import check_evidence_grounding

logger = logging.getLogger(__name__)

_SECTION_NAMES = ('framing', 'execution_investment', 'competitive_landscape', 'outlook_credibility')


class CompanyAnalyzer:
    """Runs the two-stage distill -> synthesize pipeline for one company."""

    def __init__(self, llm: LLMClient, storage: TranscriptStorage, output_root: Path) -> None:
        self._distiller = QuarterDistiller(llm)
        self._synthesizer = TrendSynthesizer(llm)
        self._report_builder = ReportBuilder()
        self._storage = storage
        self._output_root = output_root

    def analyze(self, company: str) -> Path:
        """Produces the AI-discussion trend report for `company`.

        Args:
            company: The company's storage slug (as used by TranscriptStorage).

        Returns:
            The path the rendered markdown report was written to (a sibling
            `report.pdf` is written alongside it).

        Raises:
            ValueError: If `company` has no stored transcripts.
        """
        quarter_names = self._storage.list_quarters(company)
        if not quarter_names:
            raise ValueError(f'no stored transcripts for company {company!r}')

        quarters = [self._distill_or_cached(company, quarter_name) for quarter_name in quarter_names]
        report, catalogue = self._synthesizer.synthesize(quarters)
        markdown_text = self._report_builder.render_markdown(report, catalogue)

        company_dir = self._output_root / company
        company_dir.mkdir(parents=True, exist_ok=True)
        markdown_path = company_dir / 'report.md'
        markdown_path.write_text(markdown_text)
        self._report_builder.render_pdf(markdown_text, company_dir / 'report.pdf')
        logger.info('wrote AI-discussion trend report for %s across %d quarters', company, len(quarters))
        return markdown_path

    def _distill_or_cached(self, company: str, quarter_name: str) -> QuarterAIAnalysis:
        """Loads a cached stage-1 analysis for `quarter_name`, or distills and caches it.

        Delete `{output_root}/{company}/_cache/` to force a refresh after a distill
        prompt change.
        """
        cache_path = self._output_root / company / '_cache' / f'{quarter_name}.json'
        if cache_path.exists():
            analysis = QuarterAIAnalysis.model_validate_json(cache_path.read_text())
        else:
            transcript = self._storage.load(company, quarter_name)
            analysis = self._distiller.distill(transcript, company_slug=company)
            self._ground_check(analysis, transcript)

            cache_path.parent.mkdir(parents=True, exist_ok=True)
            cache_path.write_text(analysis.model_dump_json(indent=2))

        # For monitoring/logging purposes, also write a human-readable markdown version of the cached analysis.
        cache_path.with_suffix('.md').write_text(_render_evidence_markdown(analysis))
        return analysis

    @staticmethod
    def _ground_check(analysis: QuarterAIAnalysis, transcript: Transcript) -> None:
        """Flags every evidence item's `is_grounded` against the transcript's raw_pages.

        `raw_pages` is used here and only here in the Analyzer - never as LLM input
        (see the "Analyzer Module" decision in system_design/02_system_design.md).
        """
        for section_name in _SECTION_NAMES:
            section: AnalysisSection = getattr(analysis, section_name)
            for answer in section.answers:
                check_evidence_grounding(answer.evidence, transcript.raw_pages)


def _render_evidence_markdown(analysis: QuarterAIAnalysis) -> str:
    """Renders one quarter's distilled analysis as a human-readable markdown doc,
    for evaluating extraction quality and grounding without running synthesis.
    """
    lines = [f'# {analysis.company}: {analysis.quarter_name} — Extracted AI-Discussion Evidence', '']
    for section_name in _SECTION_NAMES:
        section: AnalysisSection = getattr(analysis, section_name)
        lines.append(f'## {section_name}')
        lines.append('')
        for answer in section.answers:
            lines.append(f'### {answer.question}')
            lines.append('')
            lines.append(answer.answer)
            lines.append('')
            lines.append(_render_evidence_table(answer.evidence))
            lines.append('')
    return '\n'.join(lines)


def _render_evidence_table(evidence_items: list[Evidence]) -> str:
    """Renders one section's evidence items as a markdown table."""
    if not evidence_items:
        return '_No evidence._'
    rows = ['| # | Grounded | Page | Speaker | Excerpt |', '|---|---|---|---|---|']
    rows.extend(
        f'| {index} | {_grounded_label(evidence.is_grounded)} | {evidence.page_no} | '
        f'{evidence.speaker.name} | {evidence.excerpt} |'
        for index, evidence in enumerate(evidence_items, start=1)
    )
    return '\n'.join(rows)


def _grounded_label(is_grounded: bool | None) -> str:
    """Renders an Evidence item's `is_grounded` flag as a table cell value."""
    if is_grounded is None:
        return 'unchecked'
    return 'yes' if is_grounded else 'no'


if __name__ == '__main__':
    import os

    from earnings_calls.llm_client import GeminiVertexClient
    from earnings_calls.storage.json_file_storage import JsonFileStorage

    llm = GeminiVertexClient(
        os.getenv('GOOGLE_CLOUD_PROJECT'), os.getenv('GOOGLE_CLOUD_LOCATION'), os.getenv('GEMINI_MODEL')
    )
    storage = JsonFileStorage(Path('output/structured'))
    analyzer = CompanyAnalyzer(llm=llm, storage=storage, output_root=Path('output/tmp'))
    analyzer.analyze('bank_of_america')
