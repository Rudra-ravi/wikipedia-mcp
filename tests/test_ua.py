from wikipedia_mcp.wikipedia_client import WikipediaClient


def test_default_user_agent(monkeypatch):
    monkeypatch.delenv("WIKIPEDIA_USER_AGENT", raising=False)
    assert WikipediaClient().user_agent.startswith("WikipediaMCPServer/")


def test_user_agent_env_override(monkeypatch):
    monkeypatch.setenv("WIKIPEDIA_USER_AGENT", "my-app/1.0 (me@example.com)")
    assert WikipediaClient().user_agent == "my-app/1.0 (me@example.com)"
