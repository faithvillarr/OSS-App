"""OpenAI Client Implementation.

This module provides a concrete implementation of the AI API using the OpenAI API.
It handles API key authentication and provides methods to generate responses from OpenAI's models.
"""

import json
import logging
import os
from typing import TYPE_CHECKING, Any

import ai_api
from ai_api import AIInterface
from openai import OpenAI

if TYPE_CHECKING:
    from openai.types.chat import ChatCompletionMessageParam


class OpenAIClient(AIInterface):
    """Concrete implementation of the AIInterface abstraction using OpenAI API.

    This class provides a complete implementation of the ai_api.AIInterface
    abstraction using OpenAI's API. It handles API key authentication
    automatically and provides methods to generate both conversational and
    structured responses.

    Attributes:
        client: The authenticated OpenAI client object.
        model: The OpenAI model to use for generation (default: gpt-4o-mini).

    Environment Variables:
        - OPENAI_API_KEY: OpenAI API key (required)

    """

    DEFAULT_MODEL = "gpt-4o-mini"
    FAILURE_TO_AUTH = "Failed to authenticate with OpenAI. Please check your API key."

    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        """Initialize the OpenAIClient with API key authentication.

        Args:
            api_key: Optional API key. If not provided, reads from OPENAI_API_KEY env var.
            model: Optional model name. Defaults to gpt-4o-mini.

        """
        self.logger = logging.getLogger(__name__)
        self.model = model or self.DEFAULT_MODEL

        # Get API key from parameter or environment
        key = api_key or os.environ.get("OPENAI_API_KEY")
        if not key:
            msg = (
                "No OpenAI API key found. Please provide it via the api_key parameter "
                "or set the OPENAI_API_KEY environment variable."
            )
            raise RuntimeError(msg)

        try:
            self.client = OpenAI(api_key=key)
        except Exception as e:
            self.logger.exception("Failed to initialize OpenAI client")
            raise RuntimeError(self.FAILURE_TO_AUTH) from e

    def generate_response(
        self,
        user_input: str,
        system_prompt: str,
        response_schema: dict[str, Any] | None = None,
    ) -> str | dict[str, Any]:
        """Generate a response from the OpenAI API.

        This method analyzes the user input, determines intent, extracts data, and returns
        either a conversational string or a structured tool call based on the response_schema.

        :param user_input: The text provided by the user.
        :param system_prompt: Instructional system prompt.
        :param response_schema: Optional JSON schema dict. If provided, the AI must
            return a structured dict. The schema should include a "name",
            "description", and "schema" field. If None, the AI returns a
            conversational string.

        :return: A string (conversation) or a dict (structured action data).

        Example response_schema format:
            {
                "name": "email_action",
                "description": "Extract email action intent and parameters",
                "schema": {
                    "type": "object",
                    "properties": {
                        "action": {"type": "string", "enum": ["delete", "mark_read", "reply"]},
                        "message_id": {"type": "string"}
                    },
                    "required": ["action", "message_id"],
                    "additionalProperties": False
                }
            }
        """
        messages: list[ChatCompletionMessageParam] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input},
        ]

        content: str | None = None
        try:
            if response_schema:
                # Use structured output mode with proper JSON schema format
                # The response_schema should have name, description, and schema fields
                schema_name = response_schema.get("name", "structured_output")
                schema_description = response_schema.get(
                    "description",
                    "Structured output schema",
                )
                json_schema = response_schema.get("schema", response_schema)

                # Ensure the schema has strict mode enabled for guaranteed conformance
                if "additionalProperties" not in json_schema:
                    json_schema["additionalProperties"] = False

                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    response_format={
                        "type": "json_schema",
                        "json_schema": {
                            "name": schema_name,
                            "description": schema_description,
                            "schema": json_schema,
                            "strict": True,
                        },
                    },
                )

                content = response.choices[0].message.content
                if content:
                    return json.loads(content)  # type: ignore[no-any-return]
                return {}

            # Standard conversational mode
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
            )
            content = response.choices[0].message.content

        except Exception as e:
            self.logger.exception("Failed to generate response from OpenAI")
            error_msg = f"Failed to generate response: {e}"
            raise RuntimeError(error_msg) from e

        if content is None:
            return ""
        return content


def get_client_impl(api_key: str | None = None) -> AIInterface:
    """Return a configured :class:`OpenAIClient` instance."""
    return OpenAIClient(api_key=api_key)


def register(api_key: str | None = None) -> None:
    """Register the OpenAI client implementation with the AI API."""

    def _get_client() -> AIInterface:
        return get_client_impl(api_key=api_key)

    ai_api.get_client = _get_client  # type: ignore[assignment]
