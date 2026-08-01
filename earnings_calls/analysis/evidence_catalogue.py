"""Deterministic id assignment and resolution for stage-1 evidence, so stage 2 can
cite existing evidence by id without ever having to retype excerpt text.
"""

from earnings_calls.analysis.schemas import AnalysisSection, Evidence, QuarterAIAnalysis

_SECTION_NAMES = ('framing', 'execution_investment', 'competitive_landscape', 'outlook_credibility')


class EvidenceCatalogue:
    """Flattens a company's per-quarter analyses into a stable id -> Evidence lookup.

    Ids are computed here, in plain code, from (quarter, section, question, position) -
    never assigned by an LLM - so stage 2 can only ever cite evidence that genuinely exists.
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
                for answer_index, answer in enumerate(section.answers):
                    for evidence_index, evidence in enumerate(answer.evidence):
                        evidence_id = self._evidence_id(
                            quarter.quarter_name, section_name, answer_index, evidence_index
                        )
                        self._by_id[evidence_id] = evidence

    def resolve(self, evidence_id: str) -> Evidence | None:
        """Looks up an evidence item by id, for rendering as a trustworthy citation.

        Returns:
            The Evidence, or None if the id is unknown or its evidence failed (or
            never ran through) its grounding check - either way it must not be
            rendered as a verified citation.
        """
        evidence = self._by_id.get(evidence_id)
        if evidence is None or evidence.is_grounded is not True:
            return None
        return evidence

    def render_for_prompt(self) -> str:
        """Renders every quarter's question answers and ided evidence for the stage-2 prompt."""
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
        """Renders one section's question/answer pairs, each with its ided evidence list."""
        lines = [f'### {section_name}']
        if not section.answers:
            lines.append('No answers.')
            return '\n'.join(lines)
        for answer_index, answer in enumerate(section.answers):
            lines.append(f'Q: {answer.question}')
            lines.append(f'A: {answer.answer}')
            if answer.evidence:
                lines.append('Evidence:')
                lines.extend(
                    f'  [{self._evidence_id(quarter_name, section_name, answer_index, evidence_index)}] '
                    f'({evidence.speaker.name}, p.{evidence.page_no}): "{evidence.excerpt}"'
                    for evidence_index, evidence in enumerate(answer.evidence)
                )
            else:
                lines.append('Evidence: none')
        return '\n'.join(lines)

    @staticmethod
    def _evidence_id(quarter_name: str, section_name: str, answer_index: int, evidence_index: int) -> str:
        """Builds a deterministic evidence id from quarter, section, question, and position."""
        return f'{quarter_name}#{section_name}#{answer_index}#{evidence_index}'
