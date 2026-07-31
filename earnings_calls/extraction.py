"""Per-page PDF text extraction via docling.

Converting page-by-page (rather than whole-document) guarantees every extracted text
block carries an unambiguous, single physical page number - see the "Extraction"
decision in system_design/02_system_design.md for why whole-document conversion isn't
used (docling can merge several pages, and even several speakers, into one text block
on documents without strong paragraph-per-turn formatting).
"""

from pathlib import Path
from typing import Protocol

import pypdfium2 as pdfium
from docling.document_converter import DocumentConverter

from earnings_calls.models import RawPage


class PageExtractor(Protocol):
    """Structural interface for anything that extracts per-page text from a PDF."""

    def extract(self, pdf_path: Path, max_pages: int | None = None) -> list[RawPage]:
        """Returns one RawPage per physical page (or the first `max_pages`, if given)."""
        ...


class DoclingPageExtractor:
    """Extracts raw per-page text from a PDF using docling, one page at a time."""

    def __init__(self) -> None:
        self._converter = DocumentConverter()

    def extract(self, pdf_path: Path, max_pages: int | None = None) -> list[RawPage]:
        """Converts pages of a PDF to text, one docling call per page.

        Args:
            pdf_path: Path to the source PDF.
            max_pages: If given, only the first `max_pages` pages are extracted. Mainly
                useful for keeping tests fast while still exercising real conversion.

        Returns:
            One RawPage per physical page, in page order.
        """
        page_count = self._count_pages(pdf_path)
        if max_pages is not None:
            page_count = min(page_count, max_pages)
        pages: list[RawPage] = []
        for page_no in range(1, page_count + 1):
            result = self._converter.convert(pdf_path, page_range=(page_no, page_no))
            text = result.document.export_to_markdown()
            pages.append(RawPage(page_no=page_no, text=text))
        return pages

    @staticmethod
    def _count_pages(pdf_path: Path) -> int:
        """Counts PDF pages via pypdfium2 - far cheaper than a full docling conversion."""
        with pdfium.PdfDocument(pdf_path) as pdf_document:
            return len(pdf_document)
