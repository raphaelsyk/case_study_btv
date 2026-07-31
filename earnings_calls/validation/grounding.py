"""Deterministic self-check that a piece of text is actually grounded in the raw page
it claims to come from.

Because extraction (docling) and structuring (the LLM) are independent steps using
independent techniques, a chunk's text can be checked against the raw text docling
extracted for the same page - catching LLM paraphrasing/hallucination without a human
reviewer. Checking is per page chunk rather than per whole turn, since concatenating
every page a turn touches into one blob before diffing could mask a chunk that was
attributed to the wrong page. A failed check flags the chunk; it never drops it or
blocks storage (see the "Grounding check" decision in system_design/02_system_design.md).

`check_evidence_grounding` reuses the same matching primitive for the Analyzer's stage-1
evidence excerpts (see the "Analyzer Module" decision in system_design/02_system_design.md)
without this module depending on that downstream schema - it's typed structurally
(`_GroundableExcerpt`) rather than importing `earnings_calls.analysis.models.Evidence`.
"""

from collections.abc import Sequence
from difflib import SequenceMatcher
from typing import Protocol

from earnings_calls.models import Chunk, RawPage, Transcript

# Fraction of a chunk's (normalized) characters that must appear as matching blocks in
# its claimed page's raw text. Generous rather than strict: normalization differences
# (whitespace, minor formatting) shouldn't trip this, gross paraphrasing/fabrication should.
_MATCH_THRESHOLD = 0.6


def _normalize(text: str) -> str:
    """Lowercases and collapses whitespace so formatting differences don't affect matching."""
    return ' '.join(text.lower().split())


def _containment_ratio(needle: str, haystack: str) -> float:
    """Fraction of `needle`'s characters found as matching blocks within `haystack`."""
    if not needle:
        return 0.0
    matcher = SequenceMatcher(a=needle, b=haystack, autojunk=False)
    matching_chars = sum(block.size for block in matcher.get_matching_blocks())
    return matching_chars / len(needle)


class GroundingChecker:
    """Flags each chunk in a Transcript with whether its text is grounded in raw_pages."""

    def check(self, transcript: Transcript) -> Transcript:
        """Sets `is_grounded` on every chunk in `transcript`, in place.

        Args:
            transcript: A structured transcript whose chunks have not yet been checked.

        Returns:
            The same Transcript instance, with every chunk's `is_grounded` field set.
        """
        raw_text_by_page = {page.page_no: page.text for page in transcript.raw_pages}
        for turn in transcript.turns:
            for chunk in turn.text:
                chunk.is_grounded = self._is_grounded(chunk, raw_text_by_page)
        return transcript

    def _is_grounded(self, chunk: Chunk, raw_text_by_page: dict[int, str]) -> bool:
        """A chunk is grounded if its text is a near-verbatim match of its page's raw text."""
        raw_text = raw_text_by_page.get(chunk.page_no, '')
        return _containment_ratio(_normalize(chunk.text), _normalize(raw_text)) >= _MATCH_THRESHOLD


class _GroundableExcerpt(Protocol):
    """Structural type for anything checkable against raw page text: a claimed page
    number, the excerpt text, and a settable grounding flag."""

    page_no: int
    excerpt: str
    is_grounded: bool | None


def check_evidence_grounding(excerpts: Sequence[_GroundableExcerpt], raw_pages: Sequence[RawPage]) -> None:
    """Sets `is_grounded` on every excerpt, in place, against its claimed page's raw text.

    Args:
        excerpts: Objects with `page_no`, `excerpt`, and a settable `is_grounded`
            (e.g. `earnings_calls.analysis.models.Evidence`).
        raw_pages: The source transcript's independently-extracted raw page text.
    """
    raw_text_by_page = {page.page_no: page.text for page in raw_pages}
    for excerpt in excerpts:
        raw_text = raw_text_by_page.get(excerpt.page_no, '')
        excerpt.is_grounded = _containment_ratio(_normalize(excerpt.excerpt), _normalize(raw_text)) >= _MATCH_THRESHOLD
