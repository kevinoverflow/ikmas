from app.backend import llm_client
from app.rag import llm


def test_get_client_returns_provider_client(monkeypatch):
    client = object()

    class FakeBackend:
        def __init__(self):
            self.client = client

    monkeypatch.setattr(llm_client, "OpenAIChatBackend", FakeBackend)

    assert llm_client.get_client() is client


def test_generate_json_requests_json_object_response_format():
    calls = []

    class FakeBackend:
        def generate(self, prompt, **kwargs):
            calls.append(kwargs)
            return (
                '{"role":"MentorAgent","state":null,"assistant_message":"Bitcoin ist ein '
                'dezentrales Netzwerk.","questions":[],"artefacts":[],"actions":[{"type":"none",'
                '"payload":{}}],"citations":[],"telemetry":{"intent":"what_is","distance":"ESN",'
                '"confidence":0.8,"retrieval_count":0,"repair_used":false,"fallback_used":false}}'
            )

    client = llm_client.LLMClient(FakeBackend())
    payload = client.generate_json("Analysiere Bitcoin")

    assert payload["assistant_message"] == "Bitcoin ist ein dezentrales Netzwerk."
    assert calls[0]["response_format"] == {"type": "json_object"}


def test_repair_json_requests_json_object_response_format():
    calls = []

    class FakeBackend:
        def generate(self, prompt, **kwargs):
            calls.append(kwargs)
            if len(calls) == 1:
                return "kein json"
            return (
                '{"role":"MentorAgent","state":null,"assistant_message":"Repariert","questions":[],'
                '"artefacts":[],"actions":[{"type":"ask","payload":{}}],"citations":[],"telemetry":'
                '{"intent":"what_is","distance":"ESN","confidence":0.0,"retrieval_count":0,'
                '"repair_used":false,"fallback_used":false}}'
            )

    client = llm_client.LLMClient(FakeBackend())
    payload = client.generate_json("Analysiere Bitcoin")

    assert payload["assistant_message"] == "Repariert"
    assert calls[0]["response_format"] == {"type": "json_object"}
    assert calls[1]["response_format"] == {"type": "json_object"}


def test_parse_and_validate_json_extracts_json_from_markdown_fence():
    raw = """```json
    {
      "role": "MentorAgent",
      "state": null,
      "assistant_message": "Bitcoin ist digitales Geld.",
      "questions": [],
      "artefacts": [],
      "actions": [{"type": "none", "payload": {}}],
      "citations": [],
      "telemetry": {
        "intent": "what_is",
        "distance": "ESN",
        "confidence": 0.82,
        "retrieval_count": 0,
        "repair_used": false,
        "fallback_used": false
      }
    }
    ```"""

    payload = llm_client.LLMClient.parse_and_validate_json(
        raw,
        role="MentorAgent",
        state=None,
        intent="what_is",
        distance="ESN",
        confidence=0.82,
        retrieval_count=0,
    )

    assert payload["assistant_message"] == "Bitcoin ist digitales Geld."


def test_generate_json_salvages_plain_text_response():
    class FakeBackend:
        def generate(self, prompt, **kwargs):
            return "Bitcoin ist ein dezentrales digitales Zahlungssystem."

    client = llm_client.LLMClient(FakeBackend())
    payload = client.generate_json("Was ist Bitcoin?")

    assert payload["assistant_message"] == "Bitcoin ist ein dezentrales digitales Zahlungssystem."
    assert payload["telemetry"]["fallback_used"] is False


def test_normalize_payload_accepts_subagent_artifacts_and_drops_unknown_types():
    raw = """{
      "role": "MentorAgent",
      "state": null,
      "assistant_message": "Antwort",
      "questions": [],
      "artefacts": [
        {"type": "definition", "title": "Definition", "content": "Meaning", "concept_ids": []},
        {"type": "concept", "title": "Concept", "content": "Explanation", "concept_ids": []},
        {"type": "quiz_item", "title": "Quiz", "content": "Question", "concept_ids": []},
        {"type": "unsupported", "title": "Nope", "content": "Ignored", "concept_ids": []}
      ],
      "actions": [{"type": "none", "payload": {}}],
      "citations": [],
      "telemetry": {
        "intent": "what_is",
        "distance": "ESN",
        "confidence": 0.5,
        "retrieval_count": 0,
        "repair_used": false,
        "fallback_used": false
      }
    }"""

    payload = llm_client.LLMClient.parse_and_validate_json(
        raw,
        role="MentorAgent",
        state=None,
        intent="what_is",
        distance="ESN",
        confidence=0.5,
        retrieval_count=0,
    )

    assert [artifact["type"] for artifact in payload["artefacts"]] == [
        "definition",
        "concept",
        "quiz_item",
    ]


def test_openai_chat_backend_accepts_max_tokens(monkeypatch):
    seen = {}

    class FakeCompletions:
        def create(self, **kwargs):
            seen["request"] = kwargs
            return type(
                "Response",
                (),
                {
                    "choices": [
                        type(
                            "Choice",
                            (),
                            {"message": type("Message", (), {"content": "ok"})()},
                        )()
                    ]
                },
            )()

    class FakeOpenAI:
        def __init__(self, **kwargs):
            self.chat = type(
                "Chat",
                (),
                {"completions": FakeCompletions()},
            )()

    monkeypatch.setattr(llm, "API_KEY", "test-key")
    monkeypatch.setattr(llm, "OpenAI", FakeOpenAI)
    monkeypatch.setattr(llm, "maybe_wrap_openai", lambda client: client)

    backend = llm.OpenAIChatBackend()
    assert backend.generate("prompt", max_tokens=123) == "ok"

    assert seen["request"]["max_tokens"] == 123
