"""On-disk JSON storage for structured transcripts.

Prototype storage per the "Storage" decision in system_design/02_system_design.md: one
pydantic-validated JSON file per transcript, on-prem by default, swappable for a real
document database later without touching the pipeline or analyzer.
"""

import re
from pathlib import Path

from earnings_calls.models import Transcript


class JsonFileStorage:
    """Writes/reads one JSON file per transcript under `root/{company}/{quarter}.json`."""

    def __init__(self, root: Path) -> None:
        self._root = root

    def save(self, transcript: Transcript) -> Path:
        """Writes `transcript` to `root/{company}/{quarter}.json`, creating dirs as needed.

        Args:
            transcript: The validated transcript to persist.

        Returns:
            The path the transcript was written to.
        """
        path = self._path_for(transcript.identity.company, transcript.identity.quarter)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(transcript.model_dump_json(indent=2))
        return path

    def load(self, company: str, quarter: str) -> Transcript:
        """Reads and re-validates the transcript stored for `company`/`quarter`.

        Args:
            company: Company name as originally stored (slugified the same way as save).
            quarter: Quarter label as originally stored.

        Returns:
            The stored Transcript.
        """
        path = self._path_for(company, quarter)
        return Transcript.model_validate_json(path.read_text())

    def _path_for(self, company: str, quarter: str) -> Path:
        """Builds the on-disk path for a company/quarter, slugified for filesystem safety."""
        return self._root / self._slugify(company) / f'{self._slugify(quarter)}.json'

    @staticmethod
    def _slugify(text: str) -> str:
        """Lowercases and replaces anything that isn't alphanumeric with an underscore."""
        return re.sub(r'[^a-z0-9]+', '_', text.lower()).strip('_')
