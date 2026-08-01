"""Prompt templates for the Analyzer's two stages.

The distill prompts' question blocks are the already-validated content from the
repo-root `prompt_for_analysing_banks.md` / `prompt_for_analysing_tech_companies.md`
(kept verbatim - only the Output contract changes, from freeform markdown + a footnote
table to populating the structured `AnalysisSection`/`Evidence` schema). See the
"Analyzer Module" decision in system_design/02_system_design.md.
"""

from earnings_calls.analysis.sector import Sector

_DISTILL_INTRO = """\
You are a business analyst, analysing a company's view on AI using one quarter's \
earnings-call transcript.

Task:
Comprehensively analyse {company}'s view on AI in {quarter_name} using the speaker- and page-tagged \
transcript below, and populate the four sections of the response schema: 'framing', \
'execution_investment', 'competitive_landscape', and 'outlook_credibility'. Guide yourself on the \
attached questions for each section.

Rules:
* Base your analysis only on the transcript below. If it doesn't answer a question, \
say so briefly in that section's narrative rather than omitting the section.
* Important: every factual or quantitative claim in a section's narrative needs at \
least one evidence item. An evidence item must be a SHORT, verbatim excerpt from a \
single speaker on a single page - never blend text from two speakers or two pages \
into one excerpt. If a claim needs support from two different quotes, add two \
evidence items instead of merging them.
* Choose excerpt boundaries so the excerpt is understandable on its own, without the \
surrounding transcript. In particular, never start an excerpt with a pronoun (e.g. \
"that", "it", "this", "those") whose antecedent is a noun that only appears in an \
earlier sentence you didn't include - extend the excerpt backward to include that \
noun instead of cutting it off.
* If AI is not discussed at all for a given section, leave its narrative as a short \
sentence saying so (e.g. "AI is not discussed in this section this quarter") and \
leave its evidence list empty - do not fabricate evidence to fill a section.
* In narrative text (not excerpts, which must stay verbatim), never use a double \
quotation mark (") - if you want to quote a word or short phrase, use single quotes \
(') instead, since an unescaped double quote inside a JSON string breaks the \
response. If an excerpt itself contains a double quote, copy it exactly as spoken \
and make sure the surrounding JSON stays valid.
* Your tone should be professional, objective, and concise.

{questions}

Transcript ({company}, {quarter_name}), speaker- and page-tagged:

{tagged_turns}
"""

_BANK_QUESTIONS = """\
<attached questions to use for analysis>
##Framing
Visibility:
* Is AI raised proactively by management, or only in response to analyst questions?

Strategic framing:
* Is AI framed primarily as a revenue/product driver, an efficiency/cost tool, or a competitive necessity?
* Does management frame AI's net effect on the business as more opportunity or more risk?

Sentiment:
* What tone does management convey when discussing AI (e.g. defensive, cautious, hopeful, excited)?

##Execution & Investment
Financial materialisation:
* What investment (capex/opex) is disclosed for AI?
* What returns (revenue, cost savings) or costs are attributed to AI, and how is ROI characterized?

Implementation & maturity:
* What internal AI use cases are named, and what is their maturity (prototype / production / scaled)?
* What customer-facing AI products are named, what is their maturity, and what market/customer feedback is reported?

Talent, partnerships & operating model:
* Does the company build proprietary AI capability, rely on external partners/vendors, or both?
* Are new roles, teams, or organizational structures created for AI?
* Is workforce impact (hiring, redeployment, headcount reduction) attributed to AI?

##Competitive Landscape
Competitive positioning:
* Does management position the company as ahead of, behind, or on par with peers in AI?
* Are non-traditional competitors named as AI-enabled threats?


##Outlook & Credibility
Commitments:
* What specific, forward-looking pledges does management make about the company's own \
AI efforts (targets, timelines, deliverables)?

Outlook
* What is management's outlook on how AI (technology/market/industry) will develop, \
independent of the company's own commitments?

Claim credibility:
* Are AI-related claims specific and quantifiable, or vague and promotional?
</attached questions to use for analysis>

Remember: Provide a comprehensive analysis of the company's AI discussion in this quarter.
"""

_TECH_QUESTIONS = """\
<attached questions to use for analysis>
##Framing

Visibility / narrative composition:
* Which AI sub-segments or themes dominate the call (e.g. data center/cloud, sovereign \
AI, enterprise, robotics/physical AI, automotive, networking, gaming), and how does \
the emphasis shift vs. prior quarters?
* Which AI themes are introduced proactively in prepared remarks vs. only surfaced \
through analyst questions?

Strategic framing:
* Is the AI opportunity framed as a secular/structural shift (multi-year industrial \
build-out) or as near-term product-cycle demand?
* What total-addressable-market or infrastructure-spend figures does management cite \
to size the opportunity, and how do these evolve over time?

Sentiment:
* What tone does management convey (e.g. confident, promotional, urgent)? Since \
baseline tone is uniformly bullish for AI-native companies, does management \
acknowledge specific execution risks or bottlenecks (power, supply chain, \
geopolitics) alongside the bullish narrative, or is messaging uniformly promotional \
without caveats?

##Execution & Investment

Product & platform roadmap:
* What AI products/platforms are named, and what is their production status \
(development / ramping / full production)?
* Is the roadmap cadence (e.g. annual product cycle) reaffirmed, accelerated, or \
delayed relative to prior guidance?

Customer & market adoption:
* Which customer segments/verticals are cited as adopting AI products \
(hyperscalers/CSPs, enterprises, sovereign/government, robotics, automotive), and \
what adoption evidence is given (named customers, deployment scale, revenue)?
* What market/ecosystem validation is cited (developer adoption, benchmark results, \
named partner deployments)?

Financial materialisation:
* What revenue, margin, or growth figures are disclosed for AI-related segments, and \
how does guidance evolve?
* What capacity-side investment (capex, inventory, opex) is disclosed to support AI demand?
* What capex/spending figures does management cite for customers' AI infrastructure \
investment as a demand proxy, and how does this evolve?

Talent, partnerships & ecosystem:
* What ecosystem partnerships are named (cloud providers, model builders, \
industry/vertical partners, foundry/supply chain), and what role do they play in the \
narrative?
* Is competitive advantage attributed to proprietary technology, ecosystem/developer \
lock-in, or both?
* Are supply chain dependencies or constraints disclosed as a risk to execution?

##Competitive Landscape

Competitive positioning:
* Does management position the company as ahead of, behind, or on par with \
competitors - including alternative approaches?
* Are specific competitive threats named, and how does management characterize the \
risk they pose?

Regulatory & geopolitical risk:
* What export control, licensing, or trade policy constraints are disclosed, and how \
do they affect guidance (e.g. excluded revenue, revenue-share terms)?
* How does management characterize the durability/predictability of these \
constraints (one-off vs. ongoing uncertainty)?

##Outlook & Credibility

Commitments:
* What specific, forward-looking pledges does management make about product roadmap, \
capacity, or delivery timelines?

Outlook:
* What is management's outlook on the AI market/industry trajectory (TAM estimates, \
growth rates, multi-year infrastructure spend), independent of company-specific \
commitments?

Claim credibility:
* Are AI-related claims specific and quantifiable, or sweeping/directional (e.g. \
multi-trillion-dollar TAM, "industrial revolution" framing) without clear \
evidentiary basis?
* Do this quarter's quantitative claims align with previously stated targets or \
guidance (where prior-quarter data is available)?
</attached questions to use for analysis>

Remember: Provide a comprehensive analysis of the company's AI discussion in this quarter.
"""

_QUESTIONS_BY_SECTOR = {
    Sector.BANK: _BANK_QUESTIONS,
    Sector.TECH: _TECH_QUESTIONS,
}

_SYNTHESIZE_PROMPT = """\
You are a business analyst, synthesising how {company}'s view on AI changed across \
{quarter_count} quarters ({quarters}), from a catalogue of already-distilled \
per-quarter analyses below.

Task:
For each of the four sections ('framing', 'execution_investment', 'competitive_landscape', \
'outlook_credibility'), write a list of trend claims describing how that dimension \
changed, stayed consistent, appeared, or disappeared across the quarters below - e.g. \
"AI's framing shifted from a cost-efficiency tool in 2025_Q1 to a competitive \
necessity by 2026_Q1" or "Capex disclosures for AI were not made until 2025_Q3, then \
repeated every quarter since."

Rules:
* You have NOT been given the original transcripts, only the distilled catalogue \
below - base every claim only on the narratives and evidence it contains.
* CRITICAL: every claim's `evidence_refs` must be evidence ids copied EXACTLY as they \
appear below (e.g. "2025_Q1#framing#0"). Never invent an id that isn't listed below, \
and never put excerpt text itself into a claim or into `evidence_refs` - reference \
existing evidence by id only. A claim may cite zero, one, or several ids.
* A quarter marked "Evidence: none" for a section can still be the subject of a claim \
(e.g. noting AI wasn't discussed that quarter, or reappeared the following quarter).
* Order claims chronologically within each section where relevant.
* Never use a double quotation mark (") inside a claim's `text` - if you want to \
quote a word or short phrase, use single quotes (') instead, since an unescaped \
double quote inside a JSON string breaks the response.

Per-quarter distilled analyses, oldest first:

{catalogue}
"""


def distill_prompt(sector: Sector, company: str, quarter_name: str, tagged_turns: str) -> str:
    """Builds the stage-1 distill prompt for a company's sector and one quarter's turns."""
    return _DISTILL_INTRO.format(
        company=company,
        quarter_name=quarter_name,
        questions=_QUESTIONS_BY_SECTOR[sector],
        tagged_turns=tagged_turns,
    )


def synthesize_prompt(company: str, quarter_names: list[str], catalogue_text: str) -> str:
    """Builds the stage-2 synthesize prompt from a company's evidence catalogue."""
    return _SYNTHESIZE_PROMPT.format(
        company=company,
        quarter_count=len(quarter_names),
        quarters=', '.join(quarter_names),
        catalogue=catalogue_text,
    )
