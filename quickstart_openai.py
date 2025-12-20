"""Entry point for demonstrating the AI service stack."""

import logging

from dotenv import load_dotenv

import ai_api
import openai_impl  # noqa: F401

load_dotenv()


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main() -> None:
    """Run a small AI demo using OpenAI implementation through ai_api."""
    # Import openai_impl registers it with ai_api at import time
    client = ai_api.get_client()

    logger.info("Using OpenAI implementation through ai_api")

    # Conversational call
    prompt = "You are a creative writing assistant. Be concise and inspiring."
    text_response = client.generate_response(
        "Give me a fun writing prompt in one sentence.",
        prompt,
    )
    print("💬 Response:", text_response)

    # Structured call
    schema = {
        "name": "story_idea",
        "description": "Story idea generator",
        "schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "genre": {"type": "string"},
                "protagonist": {"type": "string"},
                "conflict": {"type": "string"},
            },
            "required": ["title", "genre", "protagonist", "conflict"],
            "additionalProperties": False,
        },
    }
    structured = client.generate_response(
        "Story about a time-traveling librarian finding self-writing books.",
        prompt,
        response_schema=schema,
    )
    print(f"  Title: {structured.get('title', 'N/A')}")
    print(f"  Genre: {structured.get('genre', 'N/A')}")
    print(f"  Hero: {structured.get('protagonist', 'N/A')}")
    print(f"  Conflict: {structured.get('conflict', 'N/A')}")


if __name__ == "__main__":
    main()
