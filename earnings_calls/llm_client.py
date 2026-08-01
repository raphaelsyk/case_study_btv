"""Swappable LLM client interface and Gemini-backed implementation."""

import logging
import os
import typing
from typing import Protocol, TypeVar

from google import genai
from google.genai import types
from pydantic import BaseModel

ModelT = TypeVar('ModelT', bound=BaseModel)

logger = logging.getLogger(__name__)


class LLMClient(Protocol):
    """Provider-agnostic interface for structured-output LLM calls."""

    def generate_structured(self, prompt: str, response_schema: type[ModelT]) -> ModelT:
        """Runs `prompt` through the model and parses the response into `response_schema`."""
        ...


class GeminiVertexClient:
    """LLMClient implementation backed by Gemini via Vertex AI."""

    def __init__(
        self,
        project: str | None = None,
        location: str | None = None,
        model: str | None = None,
    ) -> None:
        """Configures the Vertex AI client from explicit args or environment variables.

        Args:
            project: GCP project id. Falls back to the GOOGLE_CLOUD_PROJECT env var.
            location: Vertex AI region. Falls back to the GOOGLE_CLOUD_LOCATION env var.
            model: Gemini model id. Falls back to the GEMINI_MODEL env var.

        Raises:
            KeyError: If an argument is omitted and its env var is not set.
        """
        self._model = model or os.environ['GEMINI_MODEL']
        resolved_project = project or os.environ['GOOGLE_CLOUD_PROJECT']
        resolved_location = location or os.environ['GOOGLE_CLOUD_LOCATION']
        logger.info(
            'Configuring GeminiVertexClient: model=%s, project=%s, location=%s',
            self._model,
            resolved_project,
            resolved_location,
        )
        self._client = genai.Client(
            vertexai=True,
            project=resolved_project,
            location=resolved_location,
        )
        self._thinking_config = self._minimal_thinking_config(self._model)

    def generate_structured(self, prompt: str, response_schema: type[ModelT]) -> ModelT:
        """Runs `prompt` through Gemini and parses the response into `response_schema`.

        Args:
            prompt: The full prompt text to send.
            response_schema: A pydantic model class describing the expected output shape.

        Returns:
            An instance of `response_schema` parsed from the model's structured response.

        Raises:
            ValueError: If the model returned no parseable structured output.
        """
        response = self._client.models.generate_content(
            model=self._model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type='application/json',
                response_schema=response_schema,
                thinking_config=self._thinking_config,
            ),
        )
        if response.parsed is None:
            raise ValueError(f'Gemini returned no parseable {response_schema.__name__} output')
        # google-genai types `.parsed` broadly; we only ever pass pydantic model classes.
        return typing.cast(response_schema, response.parsed)

    @staticmethod
    def _minimal_thinking_config(model: str) -> types.ThinkingConfig | None:
        """Builds the lowest-effort thinking config for `model`'s generation family.

        Gemini 3.x takes `thinking_level`; Gemini 2.5 takes the older `thinking_budget`
        instead - mixing them up is a 400 INVALID_ARGUMENT. 128 is the lowest budget
        Gemini 2.5 Pro accepts (it can't fully disable thinking via budget 0). An
        unrecognized model family gets no thinking config, deferring to its default.
        """
        if model.startswith('gemini-3'):
            return types.ThinkingConfig(thinking_level='minimal')
        if model.startswith('gemini-2.5'):
            return types.ThinkingConfig(thinking_budget=128)
        return None
