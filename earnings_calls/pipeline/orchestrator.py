"""End-to-end extraction pipeline.

Input: A collection of PDFs
Output: structured Transcript stored in TranscriptStorage
"""

import logging
from collections.abc import Iterable
from pathlib import Path

from earnings_calls.llm_client import LLMClient
from earnings_calls.models import Transcript
from earnings_calls.pipeline.extraction import DoclingPageExtractor, PageExtractor
from earnings_calls.pipeline.structuring.structurer import TranscriptStructurer
from earnings_calls.storage.interface import TranscriptStorage
from earnings_calls.validation.grounding import GroundingChecker

logger = logging.getLogger(__name__)


class TranscriptPipeline:
    """Runs a single PDF through extraction, structuring, grounding-check, and storage."""

    def __init__(
        self,
        llm: LLMClient,
        storage: TranscriptStorage,
        extractor: PageExtractor | None = None,
    ) -> None:
        self._extractor = extractor or DoclingPageExtractor()
        self._structurer = TranscriptStructurer(llm)
        self._grounding_checker = GroundingChecker()
        self._storage = storage

    def run(self, pdf_path: Path) -> Transcript:
        """Extracts, structures, grounding-checks, and stores one PDF.

        Args:
            pdf_path: Path to the source earnings-call PDF.

        Returns:
            The structured, stored Transcript.
        """
        pages = self._extractor.extract(pdf_path)

        transcript = self._structurer.structure(pages)
        self._grounding_checker.check(transcript)
        self._storage.save(transcript)
        return transcript

    def run_batch(self, pdf_paths: Iterable[Path]) -> list[Transcript]:
        """Runs `run` over every PDF, logging and skipping any that fail.

        Args:
            pdf_paths: PDFs to process.

        Returns:
            The successfully structured transcripts, in input order. Failed documents
            are omitted; check logs for which ones and why.
        """
        transcripts: list[Transcript] = []
        for pdf_path in pdf_paths:
            try:
                transcripts.append(self.run(pdf_path))
            except Exception:
                # Intentionally broad: one document's failure must not stop the batch.
                logger.exception('failed to process %s, skipping', pdf_path)
        return transcripts


if __name__ == '__main__':
    import shutil
    from pathlib import Path

    from earnings_calls.llm_client import GeminiVertexClient
    from earnings_calls.storage.json_file_storage import JsonFileStorage

    input = [Path('example_data/NVDA-Q1-2026-Earnings-Call-28-May-2025-5_00-PM-ET.pdf')]
    output = Path('tests/tmp')
    output.mkdir(parents=True, exist_ok=True)

    pdf_paths = sorted(input)
    pipeline = TranscriptPipeline(llm=GeminiVertexClient(), storage=JsonFileStorage(output))
    transcripts = pipeline.run_batch(pdf_paths)

    shutil.rmtree(output)
