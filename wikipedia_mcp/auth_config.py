"""Authentication configuration for network MCP transports."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Literal, Optional

logger = logging.getLogger(__name__)

AuthMode = Literal["none", "static", "jwt"]


@dataclass(frozen=True)
class AuthConfig:
    """Validated auth configuration for MCP network transports."""

    mode: AuthMode = "none"
    token: Optional[str] = None
    public_key: Optional[str] = None
    jwks_uri: Optional[str] = None
    issuer: Optional[str] = None
    audience: Optional[str] = None
    algorithm: Optional[str] = None
    required_scopes: list[str] | None = None

    @property
    def enabled(self) -> bool:
        return self.mode != "none"


def _first_non_empty(*values: Optional[str]) -> Optional[str]:
    for value in values:
        if value and value.strip():
            return value.strip()
    return None


def _parse_scope_list(
    cli_scopes: Optional[list[str]],
    env_scopes: Optional[str],
) -> list[str] | None:
    if cli_scopes:
        normalized = [scope.strip() for scope in cli_scopes if scope and scope.strip()]
        return normalized or None

    if env_scopes:
        normalized = [scope.strip() for scope in env_scopes.split(",") if scope and scope.strip()]
        return normalized or None

    return None


def build_auth_config(
    *,
    network_transport: bool,
    auth_mode: Optional[str],
    auth_token: Optional[str],
    auth_public_key: Optional[str],
    auth_jwks_uri: Optional[str],
    auth_issuer: Optional[str],
    auth_audience: Optional[str],
    auth_algorithm: Optional[str],
    auth_required_scopes: Optional[list[str]],
) -> AuthConfig:
    """Build and validate auth config from CLI values + environment variables."""

    resolved_mode = _first_non_empty(auth_mode, os.getenv("WIKIPEDIA_MCP_AUTH_MODE"), "none")
    resolved_mode = (resolved_mode or "none").lower()

    if resolved_mode not in {"none", "static", "jwt"}:
        raise ValueError("--auth-mode must be one of: none, static, jwt")

    if not network_transport:
        if resolved_mode != "none":
            logger.warning(
                "Ignoring --auth-mode=%s because authentication is only applied to network transports",
                resolved_mode,
            )
        return AuthConfig(mode="none")

    mode = resolved_mode  # for readability
    token = _first_non_empty(auth_token, os.getenv("WIKIPEDIA_MCP_AUTH_TOKEN"))
    public_key = _first_non_empty(auth_public_key, os.getenv("WIKIPEDIA_MCP_AUTH_PUBLIC_KEY"))
    jwks_uri = _first_non_empty(auth_jwks_uri, os.getenv("WIKIPEDIA_MCP_AUTH_JWKS_URI"))
    issuer = _first_non_empty(auth_issuer, os.getenv("WIKIPEDIA_MCP_AUTH_ISSUER"))
    audience = _first_non_empty(auth_audience, os.getenv("WIKIPEDIA_MCP_AUTH_AUDIENCE"))
    algorithm = _first_non_empty(auth_algorithm, os.getenv("WIKIPEDIA_MCP_AUTH_ALGORITHM"))
    required_scopes = _parse_scope_list(auth_required_scopes, os.getenv("WIKIPEDIA_MCP_AUTH_REQUIRED_SCOPES"))

    if mode == "none":
        return AuthConfig(mode="none")

    if mode == "static":
        if not token:
            raise ValueError("--auth-mode static requires --auth-token (or WIKIPEDIA_MCP_AUTH_TOKEN)")
        return AuthConfig(mode="static", token=token)

    # mode == "jwt"
    if not public_key and not jwks_uri:
        raise ValueError(
            "--auth-mode jwt requires --auth-public-key or --auth-jwks-uri "
            "(or matching WIKIPEDIA_MCP_AUTH_* env vars)"
        )
    if public_key and jwks_uri:
        raise ValueError("Provide only one of --auth-public-key or --auth-jwks-uri")

    return AuthConfig(
        mode="jwt",
        public_key=public_key,
        jwks_uri=jwks_uri,
        issuer=issuer,
        audience=audience,
        algorithm=algorithm,
        required_scopes=required_scopes,
    )
