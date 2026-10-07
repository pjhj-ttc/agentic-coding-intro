r"""Check that the model endpoint and key work, and that the model can call tools.

Run from the repo root:

    .\.venv\Scripts\python -m app.check_model

This lives apart from app/llm.py so that running it never imports llm.py twice.
"""

import time

from .llm import ModelError, get_model


def check():
    """Send one small request with a tool, and report what came back."""
    model = get_model()
    tools = [{
        "type": "function",
        "function": {
            "name": "get_desk_list",
            "description": "List the desks of the newspaper.",
            "parameters": {"type": "object", "properties": {}},
        },
    }]
    messages = [{"role": "user", "content": "Which desks does the newspaper have? Use the tool."}]
    started = time.monotonic()
    reply = model.chat(messages, tools)
    seconds = time.monotonic() - started
    print(f"Model:      {model.name}")
    print(f"Answered in {seconds:.1f} s, tokens used: {model.last_usage.get('total_tokens', '?')}")
    if reply.get("tool_calls"):
        print(f"Tool call:  {reply['tool_calls'][0]['function']['name']}  (tool calling works)")
    else:
        print(f"Reply:      {reply.get('content')}")
        print("Warning: the model did not call the tool. Ask a facilitator.")


if __name__ == "__main__":
    try:
        check()
    except ModelError as e:
        raise SystemExit(f"[FAIL] {e}")
