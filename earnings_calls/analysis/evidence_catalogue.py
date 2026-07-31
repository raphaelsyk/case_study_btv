"""Deterministic id assignment and resolution for stage-1 evidence, so stage 2 can
cite existing evidence by id without ever having to retype excerpt text.

See the "Analyzer Module" decision in system_design/02_system_design.md.
"""

from earnings_calls.analysis.models import AnalysisSection, Evidence, QuarterAIAnalysis

# Section attribute names, in the fixed order they're rendered/cited in.
_SECTION_NAMES = ('framing', 'operations_summary', 'context', 'commitments_outlook')


class EvidenceCatalogue:
    """Flattens a company's per-quarter analyses into a stable id -> Evidence lookup.

    Ids are computed here, in plain code, from (quarter, section, position) - never
    assigned by an LLM - so stage 2 can only ever cite evidence that genuinely exists.
    """

    def __init__(self, quarters: list[QuarterAIAnalysis]) -> None:
        """Builds the catalogue from a company's stage-1 outputs.

        Args:
            quarters: One QuarterAIAnalysis per quarter, in chronological order.
        """
        self._quarters = quarters
        self._by_id: dict[str, Evidence] = {}
        for quarter in quarters:
            for section_name in _SECTION_NAMES:
                section: AnalysisSection = getattr(quarter, section_name)
                for index, evidence in enumerate(section.evidence):
                    self._by_id[self._evidence_id(quarter.quarter_name, section_name, index)] = evidence

    def resolve(self, evidence_id: str) -> Evidence | None:
        """Looks up an evidence item by id, for rendering as a trustworthy citation.

        Returns None both when the id doesn't exist and when the evidence exists but
        failed (or was never run through) its grounding check - either way, the caller
        must not render it as a verified citation. A failed grounding check is a real
        case: the source LLM call can still mis-attribute an otherwise-genuine excerpt
        to the wrong page, which grounding catches - resolve() is where that catch
        actually gets enforced, not just recorded.
        """
        evidence = self._by_id.get(evidence_id)
        if evidence is None or evidence.is_grounded is not True:
            return None
        return evidence

    def render_for_prompt(self) -> str:
        """Renders every quarter's narratives and ided evidence for the stage-2 prompt."""
        rendered_quarters = [
            f'## {quarter.quarter_name}\n'
            + '\n'.join(
                self._render_section(quarter.quarter_name, section_name, getattr(quarter, section_name))
                for section_name in _SECTION_NAMES
            )
            for quarter in self._quarters
        ]
        return '\n\n'.join(rendered_quarters)

    def _render_section(self, quarter_name: str, section_name: str, section: AnalysisSection) -> str:
        """Renders one section's narrative plus its ided evidence list."""
        lines = [f'### {section_name}', f'Narrative: {section.narrative}']
        if section.evidence:
            lines.append('Evidence:')
            lines.extend(
                f'  [{self._evidence_id(quarter_name, section_name, index)}] '
                f'({evidence.speaker.name}, p.{evidence.page_no}): "{evidence.excerpt}"'
                for index, evidence in enumerate(section.evidence)
            )
        else:
            lines.append('Evidence: none')
        return '\n'.join(lines)

    @staticmethod
    def _evidence_id(quarter_name: str, section_name: str, index: int) -> str:
        """Builds a deterministic evidence id from quarter, section, and position."""
        return f'{quarter_name}#{section_name}#{index}'
