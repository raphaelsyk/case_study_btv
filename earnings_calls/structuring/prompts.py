"""Prompt templates for the two-call transcript structuring step.

See the "Structuring" and "Two structuring calls" decisions in
system_design/02_system_design.md for why there are two calls and why pages are tagged
with <page N>...</page N> delimiters.
"""

_IDENTITY_AND_PARTICIPANTS_PROMPT = """\
You are structuring the opening pages of an earnings-call transcript.

Extract:
1. The call identity: company name, fiscal quarter label (e.g. "4Q25" or "Q1 FY2026"), \
the call date (ISO 8601, YYYY-MM-DD), and the time range being reported on. The time \
range usually needs to be inferred from the date of the call: for example, if the call \
is on the 15th of April 2026, the reported time range is likely to be 2026-01-01 until \
2026-03-31.

2. The participant roster, IF one is explicitly listed on these pages (e.g. under a \
"Participants", "Corporate Participants", or "Other Participants" heading). Some \
transcripts do NOT list participants up front at all - in that case return an empty \
list. Do not guess or infer participants from prose; only extract an explicit list.

For each participant, capture their name and, if stated, their role and company.

Pages (delimited by <page N>...</page N> tags, matching physical PDF page numbers):

{tagged_text}
"""

_TURN_SEGMENTATION_PROMPT = """\
You are segmenting a full earnings-call transcript into individual speaker turns.

The transcript is delimited by <page N>...</page N> tags giving the physical PDF page \
number of each page's text. Produce one turn per continuous stretch of speech by a \
single speaker:
- Never split a single speaker's continuous turn into multiple turns.
- A turn's `text` field is a list of page-tagged chunks: one chunk per physical page \
(from the <page N> tags) that the turn's text appears on, in page order, each carrying \
that page's page number and only the portion of the turn's text found on that page. A \
turn that continues across a page break gets one turn with multiple chunks, not two \
turns.
- For each turn's speaker, extract their name, and their role/company IF stated inline \
near the speaker label in the source text (for example "Jane Doe / Analyst, Some Bank" \
or "JANE DOE, Some Bank:"). If no role or company is stated anywhere near that speaker's \
label, leave them empty - do not guess. This matters most for analysts who only ever \
appear as turn speakers, never in an upfront roster.
- Set `section` to "management_discussion" for the prepared-remarks portion of the call \
and "qa" for the question-and-answer portion.
- For turns in the "qa" section, set `qa_type` to "question" or "answer" when you can \
tell from context which one it is; leave it empty if genuinely unclear.
- The operator/moderator introducing the call or announcing questions is a valid \
speaker like any other.

Pages:

{tagged_text}
"""


def identity_and_participants_prompt(tagged_text: str) -> str:
    """Builds the prompt for the call-identity + participant-roster structuring call."""
    return _IDENTITY_AND_PARTICIPANTS_PROMPT.format(tagged_text=tagged_text)


def turn_segmentation_prompt(tagged_text: str) -> str:
    """Builds the prompt for the full turn-segmentation structuring call."""
    return _TURN_SEGMENTATION_PROMPT.format(tagged_text=tagged_text)
