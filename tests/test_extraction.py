"""Extraction tests run against real PDFs and real docling - no mocking, since
extraction is local, free, and deterministic (see system_design/02_system_design.md).
Limited to a couple of pages per file to keep the default suite fast while still
exercising real conversion against all four companies' distinct PDF layouts; the full
unrestricted sweep is exercised by test_pipeline_integration.py.
"""

from pathlib import Path

import pytest

from earnings_calls.extraction import DoclingPageExtractor
from tests.conftest import example_pdf_paths

_MAX_PAGES_FOR_FAST_TEST = 2


@pytest.mark.parametrize('pdf_path', example_pdf_paths(), ids=lambda p: p.stem)
def test_extract_gives_one_sequential_raw_page_per_physical_page(pdf_path: Path) -> None:
    pages = DoclingPageExtractor().extract(pdf_path, max_pages=_MAX_PAGES_FOR_FAST_TEST)

    assert [page.page_no for page in pages] == list(range(1, len(pages) + 1))
    assert all(page.text.strip() for page in pages)
