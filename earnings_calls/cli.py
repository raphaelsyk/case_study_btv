"""Thin CLI entrypoint for running the transformation pipeline over a directory of PDFs.

Usage:
    uv run python -m earnings_calls.cli data/ --output output/structured

Requires GOOGLE_CLOUD_PROJECT (and optionally GOOGLE_CLOUD_LOCATION, GEMINI_MODEL) to be
set - see earnings_calls.llm_client.GeminiVertexClient.
"""

import argparse
import logging
from pathlib import Path

from earnings_calls.llm_client import GeminiVertexClient
from earnings_calls.pipeline import TranscriptPipeline
from earnings_calls.storage.json_file_storage import JsonFileStorage

logger = logging.getLogger(__name__)


def main() -> None:
    """Parses CLI args and runs the pipeline over every PDF in the given input directory."""
    logging.basicConfig(level=logging.INFO)
    args = _parse_args()
    pdf_paths = sorted(args.input_dir.glob('*.pdf'))
    pipeline = TranscriptPipeline(llm=GeminiVertexClient(), storage=JsonFileStorage(args.output))
    transcripts = pipeline.run_batch(pdf_paths)
    logger.info('processed %d/%d PDFs from %s into %s', len(transcripts), len(pdf_paths), args.input_dir, args.output)


def _parse_args() -> argparse.Namespace:
    """Parses the input-directory positional argument and --output option."""
    parser = argparse.ArgumentParser(description='Structure earnings-call PDFs into stored JSON transcripts.')
    parser.add_argument('input_dir', type=Path, help='Directory of source PDFs')
    parser.add_argument('--output', type=Path, default=Path('output/structured'), help='Storage root directory')
    return parser.parse_args()


if __name__ == '__main__':
    main()
