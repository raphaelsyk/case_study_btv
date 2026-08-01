"""Pydantic schemas for the Analyzer's two-stage AI-discussion trend report.

Stage 1 (distill) produces one `QuarterAIAnalysis` per quarter. Stage 2 (synthesize)
consumes a company's `QuarterAIAnalysis` list and produces one `CompanyAIExposureTrendReport`.
A `TrendClaim` cites evidence by id (`evidence_refs`), never by retyping excerpt text -
see the "Analyzer Module" decision in system_design/02_system_design.md for why this is
what makes citations survive the two-stage split intact.
"""

from pydantic import BaseModel, Field

from earnings_calls.models import Speaker


class Evidence(BaseModel):
    """A short, verbatim excerpt supporting a claim, traceable to its exact source.

    Always confined to a single page and a single speaker - if a claim needs support
    from two quotes, that's two Evidence items, not one spanning both.
    """

    quarter_name: str
    page_no: int = Field(ge=1)
    speaker: Speaker
    excerpt: str
    is_grounded: bool | None = None


class AnalysisSection(BaseModel):
    """One report section: synthesized prose plus every evidence item it draws on."""

    narrative: str
    evidence: list[Evidence] = Field(default_factory=list)


class QuarterAIAnalysis(BaseModel):
    """Stage-1 output: one quarter's AI-discussion analysis for one company."""

    company: str
    quarter_name: str
    framing: AnalysisSection
    execution_investment: AnalysisSection
    competitive_landscape: AnalysisSection
    outlook_credibility: AnalysisSection


class DistillResponse(BaseModel):
    """Response shape for the stage-1 distill call.

    `company`/`quarter_name` and each evidence item's `quarter_name` are set
    afterward, deterministically, from the source Transcript rather than trusted to
    the LLM - see `QuarterDistiller.distill`.
    """

    framing: AnalysisSection
    execution_investment: AnalysisSection
    competitive_landscape: AnalysisSection
    outlook_credibility: AnalysisSection


class TrendClaim(BaseModel):
    """One statement about how a dimension of the AI discussion changed across quarters."""

    text: str
    evidence_refs: list[str] = Field(default_factory=list)


class TrendSection(BaseModel):
    """One report section's trend claims."""

    claims: list[TrendClaim] = Field(default_factory=list)


class CompanyAIExposureTrendReport(BaseModel):
    """Stage-2 output: how one company's AI discussion changed across quarters."""

    company: str
    quarters_covered: list[str]
    framing: TrendSection
    execution_investment: TrendSection
    competitive_landscape: TrendSection
    outlook_credibility: TrendSection


class SynthesizeResponse(BaseModel):
    """Response shape for the stage-2 synthesize call.

    `company`/`quarters_covered` are set afterward, deterministically, from the input
    quarters rather than trusted to the LLM - see `TrendSynthesizer.synthesize`.
    """

    framing: TrendSection
    execution_investment: TrendSection
    competitive_landscape: TrendSection
    outlook_credibility: TrendSection
