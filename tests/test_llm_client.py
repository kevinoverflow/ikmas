from app.backend import llm_client


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
