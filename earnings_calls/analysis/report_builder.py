"""Renders a synthesized AI-discussion trend report to markdown and PDF.

Resolves each claim's cited evidence ids against the evidence catalogue, drops any
id that fails to resolve, and numbers the rest as sequential footnotes for display.
"""

import logging
from pathlib import Path

import markdown as markdown_lib
from xhtml2pdf import pisa

from earnings_calls.analysis.evidence_catalogue import EvidenceCatalogue
from earnings_calls.analysis.models import CompanyAIExposureTrendReport, Evidence, TrendClaim, TrendSection
from earnings_calls.models import Speaker

logger = logging.getLogger(__name__)

# (attribute name, display title), in report order.
_SECTIONS = (
    ('framing', 'Framing'),
    ('execution_investment', 'Execution & Investment'),
    ('competitive_landscape', 'Competitive Landscape'),
    ('outlook_credibility', 'Outlook & Credibility'),
)


_EVIDENCE_TABLE_COLUMN_WIDTHS = ('5%', '10%', '4%', '21%', '60%')
_MUTED_TEXT_COLOR = '#999999'
_SPEAKER_DETAIL_FONT_SIZE = '6pt'
_EVIDENCE_TABLE_CELL_PADDING = 6

_LOGO_PATH = Path(__file__).resolve().parents[2] / 'src' / 'logo.svg'
_LOGO_WIDTH_PX = 140
_DISCLAIMER_TEXT = 'AI generated -- for internal use only.'


class ReportBuilder:
    """Renders a synthesized trend report to a citation-verified markdown + PDF file."""

    def render_markdown(self, report: CompanyAIExposureTrendReport, catalogue: EvidenceCatalogue) -> str:
        """Renders `report` to markdown, resolving every claim's evidence against `catalogue`.

        Args:
            report: The synthesized trend report to render.
            catalogue: The evidence catalogue to resolve citations against.

        Returns:
            The full markdown report text, including a footnote-style evidence table.
        """
        numbers, used_evidence = self._assign_citation_numbers(report, catalogue)
        lines = [
            self._render_header(report.company),
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
        html = self._constrain_evidence_table_columns(html)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open('wb') as pdf_file:
            result = pisa.CreatePDF(html, dest=pdf_file)
        if result.err:
            raise ValueError(f'failed to render PDF for {output_path}')

    @staticmethod
    def _render_header(company: str) -> str:
        """Renders the title and disclaimer beside a top-right logo.

        A borderless two-cell table, not `float`, places the logo - xhtml2pdf doesn't
        honor CSS float, but reliably lays out tables (see `_constrain_evidence_table_columns`).
        """
        return (
            '<table style="width: 100%; border: none;"><tr>'
            '<td style="border: none; vertical-align: top; text-align: left;">'
            f'<h1>{company}: AI-Discussion Trend Report</h1>'
            f'<p style="color: {_MUTED_TEXT_COLOR};">{_DISCLAIMER_TEXT}</p>'
            '</td>'
            f'<td style="border: none; vertical-align: top; text-align: right; width: {_LOGO_WIDTH_PX + 20}px;">'
            f'<img src="{_LOGO_PATH.as_posix()}" alt="logo" width="{_LOGO_WIDTH_PX}" />'
            '</td>'
            '</tr></table>'
        )

    @staticmethod
    def _constrain_evidence_table_columns(html: str) -> str:
        """Sets the Evidence table's column widths and row padding for the PDF render."""
        # xhtml2pdf ignores CSS colgroups for column widths, so set plain HTML attributes instead.
        html = html.replace('<table>', f'<table width="100%" cellpadding="{_EVIDENCE_TABLE_CELL_PADDING}">', 1)
        for width in _EVIDENCE_TABLE_COLUMN_WIDTHS:
            html = html.replace('<th>', f'<th width="{width}">', 1)
        return html

    def _assign_citation_numbers(
        self, report: CompanyAIExposureTrendReport, catalogue: EvidenceCatalogue
    ) -> tuple[dict[str, int], dict[str, Evidence]]:
        """Resolves every claim's cited evidence ids and assigns sequential display numbers.

        Returns:
            `(numbers, used_evidence)`: `numbers` maps an evidence id to its display
            number; `used_evidence` maps the same ids to their Evidence. Both are in
            first-appearance order and include only ids that resolved successfully.
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
        """Renders one claim as a bullet with a numeric footnote marker per cited id."""
        marker_numbers = sorted({numbers[evidence_id] for evidence_id in claim.evidence_refs if evidence_id in numbers})
        suffix = f' {"".join(f"[{n}]" for n in marker_numbers)}' if marker_numbers else ''
        return f'- {claim.text}{suffix}'

    def _render_evidence_table(self, numbers: dict[str, int], used_evidence: dict[str, Evidence]) -> str:
        """Renders the footnote-style evidence table, numbered to match the claim markers."""
        if not used_evidence:
            return '_No evidence cited._'
        rows = ['| # | quarter | page | speaker | excerpt |', '|---|---|---|---|---|']
        rows.extend(
            f'| [{numbers[evidence_id]}] | {evidence.quarter_name} | {evidence.page_no} | '
            f'{self._render_speaker_cell(evidence.speaker)} | {evidence.excerpt} |'
            for evidence_id, evidence in used_evidence.items()
        )
        return '\n'.join(rows)

    @staticmethod
    def _render_speaker_cell(speaker: Speaker) -> str:
        """Renders a speaker's name, with role/company on a light-grey line underneath if known."""
        detail = ', '.join(part for part in (speaker.role, speaker.company) if part)
        if not detail:
            return speaker.name
        # Raw HTML inside a markdown table cell passes through to the rendered PDF unchanged.
        detail_style = f'color: {_MUTED_TEXT_COLOR}; font-size: {_SPEAKER_DETAIL_FONT_SIZE}; font-weight: bold;'
        return f'{speaker.name}<br><span style="{detail_style}">{detail}</span>'
