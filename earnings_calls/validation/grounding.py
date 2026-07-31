"""Deterministic self-check that a chunk's text is actually grounded in the raw page it
claims to come from.

Because extraction (docling) and structuring (the LLM) are independent steps using
independent techniques, a chunk's text can be checked against the raw text docling
extracted for the same page - catching LLM paraphrasing/hallucination without a human
reviewer. Checking is per page chunk rather than per whole turn, since concatenating
every page a turn touches into one blob before diffing could mask a chunk that was
attributed to the wrong page. A failed check flags the chunk; it never drops it or
blocks storage (see the "Grounding check" decision in system_design/02_system_design.md).
"""

from difflib import SequenceMatcher

from earnings_calls.models import Chunk, Transcript

# Fraction of a chunk's (normalized) characters that must appear as matching blocks in
# its claimed page's raw text. Generous rather than strict: normalization differences
# (whitespace, minor formatting) shouldn't trip this, gross paraphrasing/fabrication should.
_MATCH_THRESHOLD = 0.6


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
        return self._containment_ratio(self._normalize(chunk.text), self._normalize(raw_text)) >= _MATCH_THRESHOLD

    @staticmethod
    def _normalize(text: str) -> str:
        """Lowercases and collapses whitespace so formatting differences don't affect matching."""
        return ' '.join(text.lower().split())

    @staticmethod
    def _containment_ratio(needle: str, haystack: str) -> float:
        """Fraction of `needle`'s characters found as matching blocks within `haystack`."""
        if not needle:
            return 0.0
        matcher = SequenceMatcher(a=needle, b=haystack, autojunk=False)
        matching_chars = sum(block.size for block in matcher.get_matching_blocks())
        return matching_chars / len(needle)
