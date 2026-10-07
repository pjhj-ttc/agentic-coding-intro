import io
import json
import urllib.error

import pytest

from app import llm
from app.llm import FakeModel, FoundryModel, ModelError, text_reply, tool_call_reply


def test_fake_model_returns_replies_in_order_and_records_calls():
    model = FakeModel([tool_call_reply(("get_tip", {"tip_id": 1})), text_reply("Done")])
    first = model.chat([{"role": "user", "content": "Hi"}], tools=[{"type": "function"}])
    second = model.chat([{"role": "user", "content": "Again"}])

    assert first["tool_calls"][0]["function"]["name"] == "get_tip"
    assert json.loads(first["tool_calls"][0]["function"]["arguments"]) == {"tip_id": 1}
    assert second["content"] == "Done"
    assert [c["messages"][0]["content"] for c in model.calls] == ["Hi", "Again"]


def test_fake_model_fails_when_out_of_replies():
    with pytest.raises(ModelError):
        FakeModel([]).chat([])


def test_fake_model_reply_can_be_a_function():
    model = FakeModel([lambda messages: text_reply(f"{len(messages)} messages")])
    assert model.chat([{}, {}])["content"] == "2 messages"


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


ENDPOINT = "https://example-resource.openai.azure.com/"


def test_foundry_model_sends_messages_and_tools(monkeypatch):
    sent = {}

    def fake_urlopen(request, timeout):
        sent["url"] = request.full_url
        sent["key"] = request.get_header("Api-key")
        sent["payload"] = json.loads(request.data)
        answer = {"choices": [{"message": text_reply("Hello")}], "usage": {"total_tokens": 7}}
        return FakeResponse(json.dumps(answer).encode())

    monkeypatch.setattr(llm.urllib.request, "urlopen", fake_urlopen)
    model = FoundryModel(ENDPOINT, "secret-key", name="test-deployment")
    reply = model.chat([{"role": "user", "content": "Hi"}], tools=[{"type": "function"}])

    assert reply["content"] == "Hello"
    assert model.last_usage == {"total_tokens": 7}
    assert sent["url"] == "https://example-resource.openai.azure.com/openai/v1/chat/completions"
    assert sent["key"] == "secret-key"
    assert sent["payload"]["model"] == "test-deployment"
    assert sent["payload"]["tools"] == [{"type": "function"}]


def test_foundry_model_accepts_a_full_url_from_the_portal():
    model = FoundryModel("https://res.services.ai.azure.com/openai/v1/responses", "key")
    assert model.url == "https://res.services.ai.azure.com/openai/v1/chat/completions"


def test_foundry_model_error_does_not_leak_key(monkeypatch):
    def fake_urlopen(request, timeout):
        raise urllib.error.HTTPError(request.full_url, 401, "Unauthorized", {}, io.BytesIO(b"bad key"))

    monkeypatch.setattr(llm.urllib.request, "urlopen", fake_urlopen)
    with pytest.raises(ModelError) as error:
        FoundryModel(ENDPOINT, "secret-key").chat([])
    assert "401" in str(error.value)
    assert "secret-key" not in str(error.value)


def test_foundry_model_explains_an_answer_that_is_not_json(monkeypatch):
    monkeypatch.setattr(llm.urllib.request, "urlopen", lambda request, timeout: FakeResponse(b"OK\r\n"))
    with pytest.raises(ModelError, match="did not answer in JSON"):
        FoundryModel(ENDPOINT, "secret-key").chat([])


def test_get_model_without_key_explains_what_to_do():
    with pytest.raises(ModelError, match=r"key\.txt"):
        llm.get_model()


def test_get_model_reads_the_key_file(tmp_path, monkeypatch):
    key_file = tmp_path / "key.txt"
    key_file.write_text("file-key\n", encoding="utf-8-sig")  # as Set-Content may write it
    monkeypatch.setattr(llm, "KEY_FILE", key_file)
    model = llm.get_model()
    assert model.key == "file-key"
    assert model.url == llm.DEFAULT_ENDPOINT + "/openai/v1/chat/completions"


def test_environment_overrides_the_key_file(tmp_path, monkeypatch):
    key_file = tmp_path / "key.txt"
    key_file.write_text("file-key")
    monkeypatch.setattr(llm, "KEY_FILE", key_file)
    monkeypatch.setenv(llm.KEY_VARIABLE, "env-key")
    monkeypatch.setenv(llm.ENDPOINT_VARIABLE, ENDPOINT)
    model = llm.get_model()
    assert model.key == "env-key"
    assert model.url.startswith(ENDPOINT.rstrip("/"))
