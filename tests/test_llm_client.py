from app.backend import llm_client


def test_get_client_returns_provider_client(monkeypatch):
    client = object()

    class FakeBackend:
        def __init__(self):
            self.client = client

    monkeypatch.setattr(llm_client, "OpenAIChatBackend", FakeBackend)

    assert llm_client.get_client() is client
