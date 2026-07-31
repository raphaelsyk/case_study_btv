"""Shared pytest fixtures and helpers."""

import typing
from pathlib import Path

from earnings_calls.llm_client import ModelT

EXAMPLE_DATA_DIR = Path(__file__).resolve().parent.parent / 'example_data'


def example_pdf_paths() -> list[Path]:
    """The four example PDFs (one per company), used for real-docling extraction tests."""
    return sorted(EXAMPLE_DATA_DIR.glob('*.pdf'))


class FakeLLMClient:
    """An LLMClient stub returning pre-programmed responses keyed by response schema."""

    def __init__(self, responses: dict[type, object]) -> None:
        self._responses = responses
        self.prompts: list[str] = []

    def generate_structured(self, prompt: str, response_schema: type[ModelT]) -> ModelT:
        """Records `prompt` and returns the pre-programmed response for `response_schema`."""
        self.prompts.append(prompt)
        return typing.cast(response_schema, self._responses[response_schema])
