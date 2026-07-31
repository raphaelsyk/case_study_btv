"""Swappable wrapper around the LLM used for transcript structuring.

Any third-party LLM call goes through the `LLMClient` interface (see the provider-
swappability requirement in system_design/01_system_requirements.md), so structuring
logic never depends on a specific provider's SDK directly.
"""

import logging
import os
import typing
from typing import Protocol, TypeVar

from google import genai
from google.genai import types
from pydantic import BaseModel

ModelT = TypeVar('ModelT', bound=BaseModel)

logger = logging.getLogger(__name__)

# Known-GA as of this writing; override via the GEMINI_MODEL env var or the constructor
# if a newer model is enabled in the target GCP project.
DEFAULT_MODEL = 'gemini-2.5-pro'
DEFAULT_LOCATION = 'us-central1'


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
            location: Vertex AI region. Falls back to GOOGLE_CLOUD_LOCATION, then
                DEFAULT_LOCATION.
            model: Gemini model id. Falls back to GEMINI_MODEL, then DEFAULT_MODEL.
        """
        self._model = model or os.environ.get('GEMINI_MODEL', DEFAULT_MODEL)
        resolved_project = project or os.environ['GOOGLE_CLOUD_PROJECT']
        resolved_location = os.environ.get('GOOGLE_CLOUD_LOCATION', DEFAULT_LOCATION)
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
        # google-genai types `.parsed` broadly (BaseModel | dict | Enum) since response_schema
        # accepts more than just pydantic models; we only ever pass pydantic model classes.
        return typing.cast(response_schema, response.parsed)

    @staticmethod
    def _minimal_thinking_config(model: str) -> types.ThinkingConfig | None:
        """Builds the lowest-effort thinking config for `model`'s generation family.

        Gemini 3.x models take `thinking_level`; Gemini 2.5 models take the older
        `thinking_budget` (an integer token budget) instead - sending `thinking_level`
        to a 2.5 model is a 400 INVALID_ARGUMENT (observed against gemini-2.5-pro, this
        module's own DEFAULT_MODEL). 128 is the lowest budget Gemini 2.5 Pro accepts
        (unlike 2.5 Flash, 2.5 Pro can't fully disable thinking via budget 0); reusing
        128 for the whole 2.5 family keeps this simple rather than branching pro vs
        flash. An unrecognized model family gets no thinking config at all, deferring
        to that model's own default.
        """
        if model.startswith('gemini-3'):
            return types.ThinkingConfig(thinking_level='minimal')
        if model.startswith('gemini-2.5'):
            return types.ThinkingConfig(thinking_budget=128)
        return None
