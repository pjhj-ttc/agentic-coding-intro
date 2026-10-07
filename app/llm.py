"""Connection to the language model used by the triage agent.

You don't need to change this file. It gives the agent one method,
`model.chat(messages, tools)`, which sends a conversation to the model and returns
its next message. The format is the OpenAI chat format, served by an Azure OpenAI
deployment in Microsoft Foundry (v1 API).

Tests use `FakeModel`, which returns scripted replies and never calls the internet.

Check that the key in %USERPROFILE%\\.tip-portal\\key.txt works (from the repo root):

    .\\.venv\\Scripts\\python -m app.check_model
"""

import copy
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

ENDPOINT_VARIABLE = "AZURE_OPENAI_ENDPOINT"  # e.g. https://<resource>.openai.azure.com
DEFAULT_ENDPOINT = "https://foundry-training-llm.services.ai.azure.com"
KEY_VARIABLE = "AZURE_OPENAI_API_KEY"
# The key lives outside the project folder, where the coding agent's file tools don't look
KEY_FILE = Path.home() / ".tip-portal" / "key.txt"
DEFAULT_MODEL = "gpt-5-nano"  # the deployment name in Foundry
MAX_RETRIES = 3


class ModelError(RuntimeError):
    """The model could not be reached or gave an unusable answer."""


class FoundryModel:
    """The real model, through the Azure OpenAI v1 API in Microsoft Foundry."""

    def __init__(self, endpoint, key, name=DEFAULT_MODEL, timeout=60):
        # Accept the bare resource address or a full URL copied from the Foundry portal
        base = endpoint.strip().split("/openai/")[0].rstrip("/")
        self.url = base + "/openai/v1/chat/completions"
        self.key = key
        self.name = name
        self.timeout = timeout
        self.last_usage = {}

    def chat(self, messages, tools=None):
        """Send the conversation and return the model's reply message (a dict)."""
        payload = {"model": self.name, "messages": messages}
        if tools:
            payload["tools"] = tools
        request = urllib.request.Request(
            self.url,
            data=json.dumps(payload).encode("utf8"),
            headers={
                "api-key": self.key,
                "Content-Type": "application/json",
            },
            method="POST",
        )
        data = self._send(request)
        self.last_usage = data.get("usage", {})
        try:
            return data["choices"][0]["message"]
        except (KeyError, IndexError):
            raise ModelError(f"Unexpected answer from the model service: {data}") from None

    def _send(self, request):
        for attempt in range(MAX_RETRIES):
            try:
                with urllib.request.urlopen(request, timeout=self.timeout) as response:
                    body = response.read().decode("utf8", errors="replace")
                try:
                    return json.loads(body)
                except json.JSONDecodeError:
                    raise ModelError(
                        f"The model service at {self.url} did not answer in JSON: {body[:200]!r}."
                        f" Check {ENDPOINT_VARIABLE}."
                    ) from None
            except urllib.error.HTTPError as e:
                body = e.read().decode("utf8", errors="replace")[:300]
                if e.code == 429 and attempt < MAX_RETRIES - 1:
                    # Rate limited: wait as long as the service asks (capped), then retry
                    time.sleep(min(int(e.headers.get("Retry-After") or 10), 60))
                    continue
                raise ModelError(f"The model service answered {e.code}: {body}") from None
            except urllib.error.URLError as e:
                raise ModelError(f"Could not reach the model service: {e.reason}") from None


class FakeModel:
    """A stand-in for the model in tests. Returns scripted replies in order.

    A reply can be a message dict (see `text_reply` and `tool_call_reply`) or a
    function that takes the messages so far and returns a message dict.
    Every call is recorded in `calls`, so tests can check what the agent sent.
    """

    name = "fake"

    def __init__(self, replies):
        self.replies = list(replies)
        self.calls = []
        self.last_usage = {}

    def chat(self, messages, tools=None):
        self.calls.append({"messages": copy.deepcopy(messages), "tools": tools})
        if not self.replies:
            raise ModelError("FakeModel has no more scripted replies")
        reply = self.replies.pop(0)
        return reply(messages) if callable(reply) else reply


def text_reply(content):
    """A model message with plain text and no tool calls."""
    return {"role": "assistant", "content": content}


def tool_call_reply(*calls):
    """A model message asking for one or more tool calls: tool_call_reply(("name", {args}), ...)."""
    return {
        "role": "assistant",
        "content": None,
        "tool_calls": [
            {
                "id": f"call_{i}",
                "type": "function",
                "function": {"name": name, "arguments": json.dumps(args)},
            }
            for i, (name, args) in enumerate(calls, start=1)
        ],
    }


def read_key():
    """The model key: from the environment if set, otherwise from KEY_FILE."""
    key = os.environ.get(KEY_VARIABLE)
    if not key and KEY_FILE.is_file():
        key = KEY_FILE.read_text(encoding="utf-8-sig").strip()
    return key or None


def get_model():
    """The real model, configured from the key file (or environment variables)."""
    key = read_key()
    if not key:
        raise ModelError(
            f"No model key found in {KEY_FILE}. Save the key there with:\n"
            f"  New-Item -ItemType Directory -Force $HOME\\.tip-portal | Out-Null\n"
            f"  Read-Host 'Paste the key' | Set-Content -NoNewline $HOME\\.tip-portal\\key.txt"
        )
    endpoint = os.environ.get(ENDPOINT_VARIABLE) or DEFAULT_ENDPOINT
    return FoundryModel(endpoint, key, name=os.environ.get("TRIAGE_MODEL", DEFAULT_MODEL))
