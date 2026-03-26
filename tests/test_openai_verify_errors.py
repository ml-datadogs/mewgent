"""User-facing messages for OpenAI verify failures."""

from unittest.mock import MagicMock

import pytest

from src.llm.advisor import openai_verify_error_message


def test_generic_exception() -> None:
    assert openai_verify_error_message(RuntimeError("secret")) == (
        "Could not verify OpenAI connection."
    )


def test_timeout_error() -> None:
    assert openai_verify_error_message(TimeoutError()) == (
        "Network error. Check your connection."
    )


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        (401, "Invalid API key."),
        (429, "Rate limited. Try again later."),
        (500, "OpenAI error (500)."),
    ],
)
def test_api_status_error_codes(code: int, expected: str) -> None:
    from openai import APIStatusError

    response = MagicMock()
    response.status_code = code
    exc = APIStatusError(message="err", response=response, body=None)
    assert openai_verify_error_message(exc) == expected
