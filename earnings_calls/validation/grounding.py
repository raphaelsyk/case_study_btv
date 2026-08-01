"""Deterministic self-check that a piece of text is grounded in the raw page it
claims to come from.

Compares each chunk against the raw text docling extracted for the same page,
catching LLM paraphrasing/hallucination without a human reviewer. Checked per
page chunk, not per whole turn, so a chunk attributed to the wrong page can't
hide inside a concatenated blob. A failed check flags the chunk; it is never
dropped or blocked from storage.

`check_evidence_grounding` reuses the same matching primitive for the Analyzer's
evidence excerpts, typed structurally (`_GroundableExcerpt`) rather than
importing that downstream schema directly.
"""

from collections.abc import Sequence
from difflib import SequenceMatcher
from typing import Protocol

from earnings_calls.models import Chunk, RawPage, Transcript

# Fraction of a chunk's normalized characters that must match its claimed page's raw
# text. Generous by design: only gross paraphrasing/fabrication should trip this.
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
            (e.g. `earnings_calls.analysis.schemas.Evidence`).
        raw_pages: The source transcript's independently-extracted raw page text.
    """
    raw_text_by_page = {page.page_no: page.text for page in raw_pages}
    for excerpt in excerpts:
        raw_text = raw_text_by_page.get(excerpt.page_no, '')
        excerpt.is_grounded = _containment_ratio(_normalize(excerpt.excerpt), _normalize(raw_text)) >= _MATCH_THRESHOLD
