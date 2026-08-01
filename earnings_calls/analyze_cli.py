"""Thin CLI entrypoint for running the Analyzer over a company's stored transcripts.

Usage:
    uv run python -m earnings_calls.analyze_cli jpmorganchase --storage output/structured

Requires the following environment variables to be set: GOOGLE_CLOUD_PROJECT, GOOGLE_CLOUD_LOCATION, GEMINI_MODEL
"""

import argparse
import logging
from pathlib import Path

from earnings_calls.analysis.analyzer import CompanyAnalyzer
from earnings_calls.llm_client import GeminiVertexClient
from earnings_calls.storage.json_file_storage import JsonFileStorage

logger = logging.getLogger(__name__)


def main() -> None:
    """Parses CLI args and writes the AI-discussion trend report for one company."""
    logging.basicConfig(level=logging.INFO)
    args = _parse_args()
    analyzer = CompanyAnalyzer(
        llm=GeminiVertexClient(),
        storage=JsonFileStorage(args.storage),
        output_root=args.output,
    )
    report_path = analyzer.analyze(args.company)
    logger.info('wrote %s (and a sibling report.pdf)', report_path)


def _parse_args() -> argparse.Namespace:
    """Parses the company positional argument and --storage/--output options."""
    parser = argparse.ArgumentParser(description="Analyze a company's AI-discussion trend across stored quarters.")
    parser.add_argument('company', help='Company storage slug, e.g. jpmorganchase (matches output/structured/{slug})')
    parser.add_argument('--storage', type=Path, default=Path('output/structured'), help='Transcript storage root')
    parser.add_argument('--output', type=Path, default=Path('output/analysis'), help='Report output root')
    return parser.parse_args()


if __name__ == '__main__':
    main()
