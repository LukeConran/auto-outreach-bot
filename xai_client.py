"""Thin wrapper around the xAI (Grok) chat completions API.

Kept isolated so every module that needs "an agent" calls one function,
and tests can monkeypatch `chat` without touching requests/network.
"""
import json

import requests

import config


class XAIError(RuntimeError):
    pass


def chat(messages: list[dict], model: str | None = None, json_mode: bool = False,
         temperature: float = 0.3) -> str:
    """Call the xAI chat completions endpoint. Returns the assistant text content.

    Raises XAIError on non-200 responses or missing API key.
    """
    if not config.XAI_API_KEY:
        raise XAIError("XAI_API_KEY is not set. Add it to your .env file.")

    payload = {
        "model": model or config.XAI_REASONING_MODEL,
        "messages": messages,
        "temperature": temperature,
    }
    if json_mode:
        payload["response_format"] = {"type": "json_object"}

    resp = requests.post(
        f"{config.XAI_BASE_URL}/chat/completions",
        headers={
            "Authorization": f"Bearer {config.XAI_API_KEY}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=config.REQUEST_TIMEOUT_SECONDS,
    )
    if resp.status_code != 200:
        raise XAIError(f"xAI API error {resp.status_code}: {resp.text[:500]}")

    data = resp.json()
    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError) as e:
        raise XAIError(f"Unexpected xAI response shape: {data}") from e


def chat_json(messages: list[dict], model: str | None = None, temperature: float = 0.3) -> dict:
    """Call chat() with JSON mode and parse the result. Raises XAIError on bad JSON."""
    text = chat(messages, model=model, json_mode=True, temperature=temperature)
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise XAIError(f"xAI did not return valid JSON: {text[:500]}") from e
