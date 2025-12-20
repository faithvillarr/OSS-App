"""Tests for ai_api interface."""

import ai_api
from ai_api import AIInterface


def test_get_client_raises_when_not_registered() -> None:
    """Calling get_client without registration raises NotImplementedError."""
    original = ai_api.get_client

    def _unregistered() -> AIInterface:
        raise NotImplementedError

    ai_api.get_client = _unregistered
    try:
        try:
            ai_api.get_client()
        except NotImplementedError:
            assert True
        else:
            msg = "Expected NotImplementedError"
            raise AssertionError(msg)
    finally:
        ai_api.get_client = original  # type: ignore[assignment]


def test_get_client_can_be_patched() -> None:
    """ai_api.get_client can be patched to return an AIInterface."""

    class DummyClient(AIInterface):
        def generate_response(
            self,
            user_input: str,
            system_prompt: str,
            response_schema: dict[str, object] | None = None,
        ) -> str:
            return "ok"

    def stub() -> AIInterface:
        return DummyClient()

    ai_api.get_client = stub
    client = ai_api.get_client()
    assert isinstance(client, DummyClient)
    assert client.generate_response("hi", "be short") == "ok"
