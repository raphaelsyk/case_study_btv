"""Deterministic (no-LLM) rendering of a CompanyAIExposureTrendReport to markdown/PDF.

Resolves every TrendClaim's `evidence_refs` against the EvidenceCatalogue it was
synthesized from - this is where "citation verification" (the Analyzer responsibility
named in system_design/02_system_design.md) is actually enforced: an id that doesn't
resolve is dropped and logged, never silently rendered as if it were real.
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
            listing only the evidence actually cited by a resolved claim.
        """
        used_evidence: dict[str, Evidence] = {}
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
            lines.extend(self._render_claim(claim, catalogue, used_evidence) for claim in section.claims)
            lines.append('')
        lines.append('## Evidence')
        lines.append('')
        lines.append(self._render_evidence_table(used_evidence))
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

    def _render_claim(self, claim: TrendClaim, catalogue: EvidenceCatalogue, used_evidence: dict[str, Evidence]) -> str:
        """Renders one claim as a bullet with a footnote marker per resolved evidence id.

        An id that fails to resolve against `catalogue` (the model hallucinated an id
        it wasn't given) is dropped from the rendered claim and logged - it is never
        rendered as if it were a real citation.
        """
        markers = []
        for evidence_id in claim.evidence_refs:
            evidence = catalogue.resolve(evidence_id)
            if evidence is None:
                logger.warning('dropping unresolved evidence id %r cited by claim %r', evidence_id, claim.text)
                continue
            used_evidence.setdefault(evidence_id, evidence)
            markers.append(f'[{evidence_id}]')
        suffix = f' {"".join(markers)}' if markers else ''
        return f'- {claim.text}{suffix}'

    def _render_evidence_table(self, used_evidence: dict[str, Evidence]) -> str:
        """Renders the footnote-style evidence table for every evidence id actually cited."""
        if not used_evidence:
            return '_No evidence cited._'
        rows = ['| id | quarter | speaker | page | excerpt |', '|---|---|---|---|---|']
        rows.extend(
            f'| [{evidence_id}] | {evidence.quarter_name} | {evidence.speaker.name} | '
            f'{evidence.page_no} | {evidence.excerpt} |'
            for evidence_id, evidence in used_evidence.items()
        )
        return '\n'.join(rows)
