"""Storage abstraction for structured transcripts.

Kept decoupled from any specific backing technology (see the "Storage" decision in
system_design/02_system_design.md) so the prototype's on-disk JSON store can later be
swapped for a real document database without touching the pipeline or analyzer.
"""

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
