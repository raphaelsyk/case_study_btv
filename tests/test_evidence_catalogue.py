"""Tests for EvidenceCatalogue's id assignment and resolution - fully deterministic."""

from earnings_calls.analysis.evidence_catalogue import EvidenceCatalogue
from earnings_calls.analysis.models import AnalysisSection, Evidence, QuarterAIAnalysis
from earnings_calls.models import Speaker

_SPEAKER = Speaker(name='Jane Doe', role='CFO')


def _evidence(quarter_name: str, excerpt: str, page_no: int = 1, is_grounded: bool | None = True) -> Evidence:
    return Evidence(
        quarter_name=quarter_name, page_no=page_no, speaker=_SPEAKER, excerpt=excerpt, is_grounded=is_grounded
    )


def _resolved(catalogue: EvidenceCatalogue, evidence_id: str) -> Evidence:
    evidence = catalogue.resolve(evidence_id)
    assert evidence is not None, f'expected {evidence_id!r} to resolve'
    return evidence


def _quarter(quarter_name: str, framing_evidence: list[Evidence]) -> QuarterAIAnalysis:
    empty = AnalysisSection(narrative='not discussed')
    return QuarterAIAnalysis(
        company='Test Co',
        quarter_name=quarter_name,
        framing=AnalysisSection(narrative='framing narrative', evidence=framing_evidence),
        operations_summary=empty,
        context=empty,
        commitments_outlook=empty,
    )


def test_evidence_ids_are_deterministic_from_quarter_section_and_position() -> None:
    quarter = _quarter('2025_Q1', [_evidence('2025_Q1', 'first quote'), _evidence('2025_Q1', 'second quote')])

    catalogue = EvidenceCatalogue([quarter])

    assert _resolved(catalogue, '2025_Q1#framing#0').excerpt == 'first quote'
    assert _resolved(catalogue, '2025_Q1#framing#1').excerpt == 'second quote'


def test_resolve_returns_none_for_unknown_id() -> None:
    catalogue = EvidenceCatalogue([_quarter('2025_Q1', [_evidence('2025_Q1', 'a quote')])])

    assert catalogue.resolve('2025_Q1#framing#99') is None
    assert catalogue.resolve('not-a-real-id') is None


def test_resolve_returns_none_for_evidence_that_failed_grounding() -> None:
    # Regression case: a real smoke test showed the LLM can mis-attribute a genuine
    # excerpt to the wrong page. Grounding catches that, but only matters if resolve()
    # actually refuses to hand back an ungrounded item as if it were verified.
    catalogue = EvidenceCatalogue([_quarter('2025_Q1', [_evidence('2025_Q1', 'a quote', is_grounded=False)])])

    assert catalogue.resolve('2025_Q1#framing#0') is None


def test_resolve_returns_none_for_evidence_never_grounding_checked() -> None:
    catalogue = EvidenceCatalogue([_quarter('2025_Q1', [_evidence('2025_Q1', 'a quote', is_grounded=None)])])

    assert catalogue.resolve('2025_Q1#framing#0') is None


def test_ids_stay_stable_across_quarters_with_the_same_section() -> None:
    quarters = [
        _quarter('2025_Q1', [_evidence('2025_Q1', 'q1 quote')]),
        _quarter('2025_Q2', [_evidence('2025_Q2', 'q2 quote')]),
    ]

    catalogue = EvidenceCatalogue(quarters)

    assert _resolved(catalogue, '2025_Q1#framing#0').excerpt == 'q1 quote'
    assert _resolved(catalogue, '2025_Q2#framing#0').excerpt == 'q2 quote'


def test_render_for_prompt_includes_every_quarter_and_evidence_id() -> None:
    quarters = [
        _quarter('2025_Q1', [_evidence('2025_Q1', 'q1 quote')]),
        _quarter('2025_Q2', []),
    ]

    rendered = EvidenceCatalogue(quarters).render_for_prompt()

    assert '## 2025_Q1' in rendered
    assert '## 2025_Q2' in rendered
    assert '[2025_Q1#framing#0]' in rendered
    assert 'q1 quote' in rendered
    assert 'Evidence: none' in rendered
