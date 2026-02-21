"""Tests for network transport authentication configuration and middleware."""

from __future__ import annotations

import pytest

from wikipedia_mcp.auth_config import AuthConfig, build_auth_config
from wikipedia_mcp.server import StaticBearerAuthMiddleware, build_http_middleware, create_server


class TestAuthConfig:
    def test_non_network_transport_disables_auth(self):
        config = build_auth_config(
            network_transport=False,
            auth_mode="static",
            auth_token="secret",
            auth_public_key=None,
            auth_jwks_uri=None,
            auth_issuer=None,
            auth_audience=None,
            auth_algorithm=None,
            auth_required_scopes=None,
        )
        assert config.mode == "none"

    def test_static_mode_requires_token(self):
        with pytest.raises(ValueError, match="requires --auth-token"):
            build_auth_config(
                network_transport=True,
                auth_mode="static",
                auth_token=None,
                auth_public_key=None,
                auth_jwks_uri=None,
                auth_issuer=None,
                auth_audience=None,
                auth_algorithm=None,
                auth_required_scopes=None,
            )

    def test_jwt_mode_requires_public_key_or_jwks(self):
        with pytest.raises(ValueError, match="requires --auth-public-key or --auth-jwks-uri"):
            build_auth_config(
                network_transport=True,
                auth_mode="jwt",
                auth_token=None,
                auth_public_key=None,
                auth_jwks_uri=None,
                auth_issuer=None,
                auth_audience=None,
                auth_algorithm=None,
                auth_required_scopes=None,
            )

    def test_jwt_mode_rejects_both_public_key_and_jwks(self):
        with pytest.raises(ValueError, match="Provide only one of --auth-public-key or --auth-jwks-uri"):
            build_auth_config(
                network_transport=True,
                auth_mode="jwt",
                auth_token=None,
                auth_public_key="public-key",
                auth_jwks_uri="https://example.com/jwks.json",
                auth_issuer=None,
                auth_audience=None,
                auth_algorithm=None,
                auth_required_scopes=None,
            )


class TestStaticAuthMiddleware:
    @pytest.mark.asyncio
    async def test_static_middleware_allows_valid_bearer_token(self):
        called = {"value": False}

        async def app(scope, receive, send):
            called["value"] = True

        middleware = StaticBearerAuthMiddleware(app, token="secret")

        scope = {
            "type": "http",
            "headers": [(b"authorization", b"Bearer secret")],
            "method": "GET",
            "path": "/mcp",
        }

        async def receive():
            return {"type": "http.request", "body": b"", "more_body": False}

        events = []

        async def send(message):
            events.append(message)

        await middleware(scope, receive, send)

        assert called["value"] is True
        assert events == []

    @pytest.mark.asyncio
    async def test_static_middleware_rejects_invalid_token(self):
        called = {"value": False}

        async def app(scope, receive, send):
            called["value"] = True

        middleware = StaticBearerAuthMiddleware(app, token="secret")

        scope = {
            "type": "http",
            "headers": [(b"authorization", b"Bearer wrong")],
            "method": "GET",
            "path": "/mcp",
        }

        async def receive():
            return {"type": "http.request", "body": b"", "more_body": False}

        events = []

        async def send(message):
            events.append(message)

        await middleware(scope, receive, send)

        assert called["value"] is False
        assert events[0]["type"] == "http.response.start"
        assert events[0]["status"] == 401


class TestServerAuthIntegration:
    def test_build_http_middleware_static_mode(self):
        config = AuthConfig(mode="static", token="secret")
        middleware = build_http_middleware(config)
        assert len(middleware) == 1

    def test_build_http_middleware_non_static_mode(self):
        middleware = build_http_middleware(AuthConfig(mode="none"))
        assert middleware == []

    def test_create_server_with_jwt_auth_provider(self):
        server = create_server(
            auth_config=AuthConfig(
                mode="jwt",
                public_key="-----BEGIN PUBLIC KEY-----\nTEST\n-----END PUBLIC KEY-----",
            )
        )
        assert server is not None
        assert server.auth is not None
