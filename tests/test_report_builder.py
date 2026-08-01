"""Tests for ReportBuilder - fully deterministic, no LLM involved.

Focused on two things: (1) citation verification - a claim's evidence_refs are only
ever rendered when they resolve against the EvidenceCatalogue they were synthesized
from; (2) display numbering - the rendered report never leaks the internal catalogue
id (e.g. "2025_Q1#framing#0#0"), only a short sequential [1], [2], ... footnote number.
"""

from earnings_calls.analysis.evidence_catalogue import EvidenceCatalogue
from earnings_calls.analysis.models import (
    AnalysisSection,
    CompanyAIExposureTrendReport,
    Evidence,
    QuarterAIAnalysis,
    QuestionAnswer,
    TrendClaim,
    TrendSection,
)
from earnings_calls.analysis.report_builder import ReportBuilder
from earnings_calls.models import Speaker

_SPEAKER = Speaker(name='Jane Doe', role='CFO')


def _quarter_with_evidence(quarter_name: str, excerpt: str, is_grounded: bool | None = True) -> QuarterAIAnalysis:
    evidence = Evidence(
        quarter_name=quarter_name, page_no=3, speaker=_SPEAKER, excerpt=excerpt, is_grounded=is_grounded
    )
    empty = AnalysisSection(answers=[])
    answer = QuestionAnswer(question='How is AI framed?', answer='framing narrative', evidence=[evidence])
    return QuarterAIAnalysis(
        company='Test Co',
        quarter_name=quarter_name,
        framing=AnalysisSection(answers=[answer]),
        execution_investment=empty,
        competitive_landscape=empty,
        outlook_credibility=empty,
    )


def _report(claims: list[TrendClaim]) -> CompanyAIExposureTrendReport:
    empty = TrendSection(claims=[])
    return CompanyAIExposureTrendReport(
        company='Test Co',
        quarters_covered=['2025_Q1'],
        framing=TrendSection(claims=claims),
        execution_investment=empty,
        competitive_landscape=empty,
        outlook_credibility=empty,
    )


def test_claim_with_resolved_evidence_gets_a_numeric_footnote_marker_and_table_row() -> None:
    quarter = _quarter_with_evidence('2025_Q1', 'we are investing heavily in AI')
    catalogue = EvidenceCatalogue([quarter])
    report = _report([TrendClaim(text='AI investment increased', evidence_refs=['2025_Q1#framing#0#0'])])

    markdown = ReportBuilder().render_markdown(report, catalogue)

    assert 'AI investment increased [1]' in markdown
    assert 'we are investing heavily in AI' in markdown
    assert 'Jane Doe' in markdown
    # The internal catalogue id is a machine-resolution detail, never shown to the reader.
    assert '2025_Q1#framing#0#0' not in markdown


def test_citations_are_numbered_by_first_appearance_and_reused_across_claims() -> None:
    quarter = _quarter_with_evidence('2025_Q1', 'we are investing heavily in AI')
    catalogue = EvidenceCatalogue([quarter])
    report = _report(
        [
            TrendClaim(text='first claim', evidence_refs=['2025_Q1#framing#0#0']),
            TrendClaim(text='second claim citing the same evidence', evidence_refs=['2025_Q1#framing#0#0']),
        ]
    )

    markdown = ReportBuilder().render_markdown(report, catalogue)

    assert 'first claim [1]' in markdown
    assert 'second claim citing the same evidence [1]' in markdown
    # Cited twice, but the evidence table lists it once.
    assert markdown.count('we are investing heavily in AI') == 1


def test_claim_with_unresolved_evidence_id_drops_the_citation_silently() -> None:
    # The model hallucinated an id that was never in the catalogue it was given -
    # citation verification means this never reaches the rendered report as if real.
    quarter = _quarter_with_evidence('2025_Q1', 'we are investing heavily in AI')
    catalogue = EvidenceCatalogue([quarter])
    report = _report([TrendClaim(text='AI investment increased', evidence_refs=['2025_Q1#framing#0#99'])])

    markdown = ReportBuilder().render_markdown(report, catalogue)

    assert 'AI investment increased' in markdown
    assert '2025_Q1#framing#0#99' not in markdown
    assert '_No evidence cited._' in markdown


def test_claim_with_ungrounded_evidence_drops_the_citation_silently() -> None:
    # Regression case from a real smoke test: the id genuinely exists in the
    # catalogue, but its excerpt failed the grounding check (the LLM attributed a real
    # quote to the wrong page). It must be dropped exactly like a hallucinated id -
    # existing-but-unverified is still unverified.
    quarter = _quarter_with_evidence('2025_Q1', 'we are investing heavily in AI', is_grounded=False)
    catalogue = EvidenceCatalogue([quarter])
    report = _report([TrendClaim(text='AI investment increased', evidence_refs=['2025_Q1#framing#0#0'])])

    markdown = ReportBuilder().render_markdown(report, catalogue)

    assert 'AI investment increased' in markdown
    assert 'we are investing heavily in AI' not in markdown
    assert '_No evidence cited._' in markdown


def test_evidence_table_only_lists_ids_actually_cited_by_a_claim() -> None:
    # A quarter can carry evidence that stage 2 never draws a trend claim from -
    # the table should not list evidence nobody in the final report cites.
    quarter = _quarter_with_evidence('2025_Q1', 'unused quote')
    catalogue = EvidenceCatalogue([quarter])
    report = _report([TrendClaim(text='a claim citing nothing', evidence_refs=[])])

    markdown = ReportBuilder().render_markdown(report, catalogue)

    assert 'unused quote' not in markdown
    assert '_No evidence cited._' in markdown
