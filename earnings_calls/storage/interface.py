"""Storage abstraction for structured transcripts."""

from pathlib import Path
from typing import Protocol

from earnings_calls.models import Transcript


class TranscriptStorage(Protocol):
    """Persists and retrieves structured transcripts, keyed by company and quarter."""

    def save(self, transcript: Transcript) -> Path:
        """Persists `transcript`, returning the path it was written to."""
        ...

    def load(self, company: str, quarter: str) -> Transcript:
        """Loads a previously stored transcript for `company`/`quarter`."""
        ...

    def list_quarters(self, company: str) -> list[str]:
        """Lists every quarter with a stored transcript for `company`, chronologically."""
        ...
