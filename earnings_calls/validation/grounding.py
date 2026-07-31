"""Deterministic self-check that a chunk segment's text is actually grounded in the raw
page it claims to come from.

Because extraction (docling) and structuring (the LLM) are independent steps using
independent techniques, a segment's text can be checked against the raw text docling
extracted for the same page - catching LLM paraphrasing/hallucination without a human
reviewer. Checking is per page segment rather than per whole chunk, since concatenating
every page a chunk touches into one blob before diffing could mask a segment that was
attributed to the wrong page. A failed check flags the segment; it never drops it or
blocks storage (see the "Grounding check" decision in system_design/02_system_design.md).
"""

from difflib import SequenceMatcher

from earnings_calls.models import ChunkSegment, Transcript

# Fraction of a segment's (normalized) characters that must appear as matching blocks in
# its claimed page's raw text. Generous rather than strict: normalization differences
# (whitespace, minor formatting) shouldn't trip this, gross paraphrasing/fabrication should.
_MATCH_THRESHOLD = 0.6


class GroundingChecker:
    """Flags each chunk segment in a Transcript with whether its text is grounded in raw_pages."""

    def check(self, transcript: Transcript) -> Transcript:
        """Sets `is_grounded` on every chunk segment in `transcript`, in place.

        Args:
            transcript: A structured transcript whose chunk segments have not yet been checked.

        Returns:
            The same Transcript instance, with every chunk segment's `is_grounded` field set.
        """
        raw_text_by_page = {page.page_no: page.text for page in transcript.raw_pages}
        for chunk in transcript.chunks:
            for segment in chunk.text:
                segment.is_grounded = self._is_grounded(segment, raw_text_by_page)
        return transcript

    def _is_grounded(self, segment: ChunkSegment, raw_text_by_page: dict[int, str]) -> bool:
        """A segment is grounded if its text is a near-verbatim match of its page's raw text."""
        raw_text = raw_text_by_page.get(segment.page_no, '')
        return self._containment_ratio(self._normalize(segment.text), self._normalize(raw_text)) >= _MATCH_THRESHOLD

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
