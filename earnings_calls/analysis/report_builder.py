"""Deterministic (no-LLM) rendering of a CompanyAIExposureTrendReport to markdown/PDF.

Resolves every TrendClaim's `evidence_refs` against the EvidenceCatalogue it was
synthesized from - this is where "citation verification" (the Analyzer responsibility
named in system_design/02_system_design.md) is actually enforced: an id that doesn't
resolve is dropped and logged, never silently rendered as if it were real.

The internal catalogue id (e.g. "2026_Q2#framing#0") is what stage 2 cites and what
resolve() checks against - it's built for machine correctness, not for a reader. The
rendered report never shows it: each resolved id is assigned a short sequential
footnote number (in first-appearance order) purely for display, the same way the
original hand-authored single-quarter report used numbered footnotes.
"""

import logging
from pathlib import Path

import markdown as markdown_lib
from xhtml2pdf import pisa

from earnings_calls.analysis.evidence_catalogue import EvidenceCatalogue
from earnings_calls.analysis.models import CompanyAIExposureTrendReport, Evidence, TrendClaim, TrendSection

logger = logging.getLogger(__name__)

# (attribute name, display title), in report order.
_SECTIONS = (
    ('framing', 'Framing'),
    ('operations_summary', 'Summary of AI-related operations'),
    ('context', 'Context'),
    ('commitments_outlook', 'Commitments, Outlook & Credibility'),
)


class ReportBuilder:
    """Renders a synthesized trend report to a citation-verified markdown + PDF file."""

    def render_markdown(self, report: CompanyAIExposureTrendReport, catalogue: EvidenceCatalogue) -> str:
        """Renders `report` to markdown, resolving every claim's evidence against `catalogue`.

        Args:
            report: The stage-2 synthesized trend report.
            catalogue: The EvidenceCatalogue `report` was synthesized from.

        Returns:
            The full markdown report text, including a footnote-style evidence table
            listing only the evidence actually cited by a resolved claim, numbered
            [1], [2], ... in first-appearance order rather than by internal catalogue id.
        """
        numbers, used_evidence = self._assign_citation_numbers(report, catalogue)
        lines = [
            f'# {report.company}: AI-Discussion Trend Report',
            '',
            f'Quarters covered: {", ".join(report.quarters_covered)}',
            '',
        ]
        for attr_name, title in _SECTIONS:
            section: TrendSection = getattr(report, attr_name)
            lines.append(f'## {title}')
            lines.append('')
            lines.extend(self._render_claim(claim, numbers) for claim in section.claims)
            lines.append('')
        lines.append('## Evidence')
        lines.append('')
        lines.append(self._render_evidence_table(numbers, used_evidence))
        return '\n'.join(lines)

    def render_pdf(self, markdown_text: str, output_path: Path) -> None:
        """Converts rendered markdown to a PDF file at `output_path`.

        Args:
            markdown_text: Markdown produced by `render_markdown`.
            output_path: Where to write the PDF.

        Raises:
            ValueError: If PDF generation fails.
        """
        html = markdown_lib.markdown(markdown_text, extensions=['tables'])
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open('wb') as pdf_file:
            result = pisa.CreatePDF(html, dest=pdf_file)
        if result.err:
            raise ValueError(f'failed to render PDF for {output_path}')

    def _assign_citation_numbers(
        self, report: CompanyAIExposureTrendReport, catalogue: EvidenceCatalogue
    ) -> tuple[dict[str, int], dict[str, Evidence]]:
        """Walks every claim in report order, resolving each evidence id exactly once.

        The first time an id resolves it gets the next sequential display number
        (1, 2, 3, ...) - this is what lets the rendered report use short numeric
        footnotes instead of the internal catalogue id. An id that fails to resolve
        (the model hallucinated an id it wasn't given, or cited ungrounded evidence -
        see EvidenceCatalogue.resolve) is logged once and never numbered, so it can
        never appear in the rendered report as if it were a real citation.

        Returns:
            `(numbers, used_evidence)`: `numbers` maps catalogue id -> display number
            for every id that resolved; `used_evidence` maps the same ids to their
            Evidence, in the same first-appearance order, for the evidence table.
        """
        numbers: dict[str, int] = {}
        used_evidence: dict[str, Evidence] = {}
        seen: set[str] = set()
        for attr_name, _ in _SECTIONS:
            section: TrendSection = getattr(report, attr_name)
            for claim in section.claims:
                for evidence_id in claim.evidence_refs:
                    if evidence_id in seen:
                        continue
                    seen.add(evidence_id)
                    evidence = catalogue.resolve(evidence_id)
                    if evidence is None:
                        logger.warning('dropping unresolved/ungrounded evidence id %r', evidence_id)
                        continue
                    numbers[evidence_id] = len(numbers) + 1
                    used_evidence[evidence_id] = evidence
        return numbers, used_evidence

    def _render_claim(self, claim: TrendClaim, numbers: dict[str, int]) -> str:
        """Renders one claim as a bullet with a numeric footnote marker per cited id.

        Markers are the ids' assigned display numbers (see `_assign_citation_numbers`),
        deduplicated and sorted ascending so multiple citations on one claim read left
        to right in footnote order regardless of the order the model listed them in.
        """
        marker_numbers = sorted({numbers[evidence_id] for evidence_id in claim.evidence_refs if evidence_id in numbers})
        suffix = f' {"".join(f"[{n}]" for n in marker_numbers)}' if marker_numbers else ''
        return f'- {claim.text}{suffix}'

    def _render_evidence_table(self, numbers: dict[str, int], used_evidence: dict[str, Evidence]) -> str:
        """Renders the footnote-style evidence table, numbered to match the claim markers."""
        if not used_evidence:
            return '_No evidence cited._'
        rows = ['| # | quarter | speaker | page | excerpt |', '|---|---|---|---|---|']
        rows.extend(
            f'| [{numbers[evidence_id]}] | {evidence.quarter_name} | {evidence.speaker.name} | '
            f'{evidence.page_no} | {evidence.excerpt} |'
            for evidence_id, evidence in used_evidence.items()
        )
        return '\n'.join(rows)
