"""Wikipedia MCP server implementation."""

import logging
from typing import Annotated, Any, Literal, Optional, cast

from fastmcp import FastMCP
from fastmcp.server.auth.providers.bearer import BearerAuthProvider
from mcp.types import ToolAnnotations
from pydantic import Field
from starlette.datastructures import Headers
from starlette.middleware import Middleware as ASGIMiddleware
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from wikipedia_mcp.auth_config import AuthConfig
from wikipedia_mcp.schemas import (
    ArticleResponse,
    ConnectivityResponse,
    CoordinatesResponse,
    KeyFactsResponse,
    LinksResponse,
    QuerySummaryResponse,
    RelatedTopicsResponse,
    SearchWikipediaResponse,
    SectionSummaryResponse,
    SectionsResponse,
    SummaryResponse,
    model_output_schema,
)
from wikipedia_mcp.wikipedia_client import WikipediaClient

logger = logging.getLogger(__name__)

_READ_ONLY_TOOL_ANNOTATIONS = ToolAnnotations(
    readOnlyHint=True,
    destructiveHint=False,
    idempotentHint=True,
    openWorldHint=True,
)


class StaticBearerAuthMiddleware:
    """ASGI middleware that enforces a static Bearer token."""

    def __init__(self, app: ASGIApp, token: str):
        self.app = app
        self._expected = f"Bearer {token}"

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        headers = Headers(scope=scope)
        authorization = headers.get("authorization")
        if authorization != self._expected:
            response = JSONResponse(
                {
                    "error": "Unauthorized",
                    "message": "Missing or invalid Bearer token",
                },
                status_code=401,
                headers={"WWW-Authenticate": "Bearer"},
            )
            await response(scope, receive, send)
            return

        await self.app(scope, receive, send)


def _build_jwt_auth_provider(auth_config: AuthConfig) -> Optional[BearerAuthProvider]:
    if auth_config.mode != "jwt":
        return None

    audience: str | list[str] | None = None
    if auth_config.audience:
        if "," in auth_config.audience:
            audience = [a.strip() for a in auth_config.audience.split(",") if a.strip()]
        else:
            audience = auth_config.audience

    return BearerAuthProvider(
        public_key=auth_config.public_key,
        jwks_uri=auth_config.jwks_uri,
        issuer=auth_config.issuer,
        algorithm=auth_config.algorithm,
        audience=audience,
        required_scopes=auth_config.required_scopes,
    )


def build_http_middleware(auth_config: AuthConfig) -> list[ASGIMiddleware]:
    """Build additional HTTP middleware based on auth mode."""
    if auth_config.mode == "static":
        if not auth_config.token:
            raise ValueError("Static auth mode requires a non-empty token")
        return [ASGIMiddleware(StaticBearerAuthMiddleware, token=auth_config.token)]
    return []


def create_server(
    language: str = "en",
    country: Optional[str] = None,
    enable_cache: bool = False,
    access_token: Optional[str] = None,
    auth_config: Optional[AuthConfig] = None,
    auth_mode: str = "none",
    auth_public_key: Optional[str] = None,
    auth_jwks_uri: Optional[str] = None,
    auth_issuer: Optional[str] = None,
    auth_audience: Optional[str] = None,
    auth_algorithm: Optional[str] = None,
    auth_required_scopes: Optional[list[str]] = None,
) -> FastMCP:
    """Create and configure the Wikipedia MCP server."""

    resolved_auth = auth_config or AuthConfig(
        mode=cast(Literal["none", "static", "jwt"], auth_mode if auth_mode in {"none", "static", "jwt"} else "none"),
        public_key=auth_public_key,
        jwks_uri=auth_jwks_uri,
        issuer=auth_issuer,
        audience=auth_audience,
        algorithm=auth_algorithm,
        required_scopes=auth_required_scopes,
    )

    auth_provider = _build_jwt_auth_provider(resolved_auth)

    server: FastMCP = FastMCP(
        name="Wikipedia",
        auth=auth_provider,
    )

    wikipedia_client = WikipediaClient(
        language=language,
        country=country,
        enable_cache=enable_cache,
        access_token=access_token,
    )

    def register_tool(name: str, output_schema: dict[str, Any]):
        def decorator(func):
            server.tool(
                func,
                name=name,
                annotations=_READ_ONLY_TOOL_ANNOTATIONS,
                output_schema=output_schema,
            )
            server.tool(
                func,
                name=f"wikipedia_{name}",
                annotations=_READ_ONLY_TOOL_ANNOTATIONS,
                output_schema=output_schema,
            )
            return func

        return decorator

    @register_tool("search_wikipedia", model_output_schema(SearchWikipediaResponse))
    def search_wikipedia(query: str, limit: int = 10):
        logger.info("Tool: Searching Wikipedia for '%s' (limit=%d)", query, limit)

        if not query or not query.strip():
            logger.warning("Search tool called with empty query")
            return {
                "query": query,
                "results": [],
                "status": "error",
                "message": "Empty search query provided",
            }

        validated_limit = limit
        if limit <= 0:
            validated_limit = 10
            logger.warning("Invalid limit %d; using default %d", limit, validated_limit)
        elif limit > 500:
            validated_limit = 500
            logger.warning("Limit %d capped to %d", limit, validated_limit)

        results = wikipedia_client.search(query, limit=validated_limit)
        status = "success" if results else "no_results"
        response = {
            "query": query,
            "results": results,
            "status": status,
            "count": len(results),
            "language": wikipedia_client.base_language,
        }

        if not results:
            response["message"] = (
                "No search results found. This could indicate connectivity issues, "
                "API errors, or simply no matching articles."
            )

        return response

    @register_tool("test_wikipedia_connectivity", model_output_schema(ConnectivityResponse))
    def test_wikipedia_connectivity():
        logger.info("Tool: Testing Wikipedia connectivity")
        diagnostics = wikipedia_client.test_connectivity()

        if (
            diagnostics.get("status") == "success"
            and "response_time_ms" in diagnostics
            and isinstance(diagnostics["response_time_ms"], (int, float))
        ):
            diagnostics["response_time_ms"] = round(float(diagnostics["response_time_ms"]), 3)
        return diagnostics

    @register_tool("get_article", model_output_schema(ArticleResponse))
    def get_article(title: str):
        logger.info("Tool: Getting article: %s", title)
        article = wikipedia_client.get_article(title)
        return article or {"title": title, "exists": False, "error": "Unknown error retrieving article"}

    @register_tool("get_summary", model_output_schema(SummaryResponse))
    def get_summary(title: str):
        logger.info("Tool: Getting summary for: %s", title)
        summary = wikipedia_client.get_summary(title)
        if summary and not summary.startswith("Error"):
            return {"title": title, "summary": summary}
        return {"title": title, "summary": None, "error": summary}

    @register_tool("summarize_article_for_query", model_output_schema(QuerySummaryResponse))
    def summarize_article_for_query(
        title: str,
        query: str,
        max_length: Annotated[int, Field(title="Max Length")] = 250,
    ):
        logger.info("Tool: Getting query-focused summary for article: %s, query: %s", title, query)
        summary = wikipedia_client.summarize_for_query(title, query, max_length=max_length)
        return {"title": title, "query": query, "summary": summary}

    @register_tool("summarize_article_section", model_output_schema(SectionSummaryResponse))
    def summarize_article_section(
        title: str,
        section_title: str,
        max_length: Annotated[int, Field(title="Max Length")] = 150,
    ):
        logger.info("Tool: Getting summary for section: %s in article: %s", section_title, title)
        summary = wikipedia_client.summarize_section(title, section_title, max_length=max_length)
        return {"title": title, "section_title": section_title, "summary": summary}

    @register_tool("extract_key_facts", model_output_schema(KeyFactsResponse))
    def extract_key_facts(
        title: str,
        topic_within_article: Annotated[str, Field(title="Topic Within Article")] = "",
        count: int = 5,
    ):
        logger.info("Tool: Extracting key facts for article: %s, topic: %s", title, topic_within_article)
        topic = topic_within_article if topic_within_article.strip() else None
        facts = wikipedia_client.extract_facts(title, topic, count=count)
        return {"title": title, "topic_within_article": topic_within_article, "facts": facts}

    @register_tool("get_related_topics", model_output_schema(RelatedTopicsResponse))
    def get_related_topics(title: str, limit: int = 10):
        logger.info("Tool: Getting related topics for: %s", title)
        related = wikipedia_client.get_related_topics(title, limit=limit)
        return {"title": title, "related_topics": related}

    @register_tool("get_sections", model_output_schema(SectionsResponse))
    def get_sections(title: str):
        logger.info("Tool: Getting sections for: %s", title)
        sections = wikipedia_client.get_sections(title)
        return {"title": title, "sections": sections}

    @register_tool("get_links", model_output_schema(LinksResponse))
    def get_links(title: str):
        logger.info("Tool: Getting links for: %s", title)
        links = wikipedia_client.get_links(title)
        return {"title": title, "links": links}

    @register_tool("get_coordinates", model_output_schema(CoordinatesResponse))
    def get_coordinates(title: str):
        """Get geographic coordinates for a Wikipedia article title."""
        logger.info("Tool: Getting coordinates for: %s", title)
        coordinates = wikipedia_client.get_coordinates(title)
        return coordinates

    @server.resource("/search/{query}")
    def search(query: str):
        logger.info("Searching Wikipedia for: %s", query)
        results = wikipedia_client.search(query, limit=10)
        return {"query": query, "results": results}

    @server.resource("/article/{title}")
    def article(title: str):
        logger.info("Getting article: %s", title)
        article_data = wikipedia_client.get_article(title)
        return article_data or {"title": title, "exists": False, "error": "Unknown error retrieving article"}

    @server.resource("/summary/{title}")
    def summary(title: str):
        logger.info("Getting summary for: %s", title)
        summary_text = wikipedia_client.get_summary(title)
        if summary_text and not summary_text.startswith("Error"):
            return {"title": title, "summary": summary_text}
        return {"title": title, "summary": None, "error": summary_text}

    @server.resource("/summary/{title}/query/{query}/length/{max_length}")
    def summary_for_query_resource(title: str, query: str, max_length: int):
        logger.info(
            "Resource: Getting query-focused summary for article: %s, query: %s, max_length: %d",
            title,
            query,
            max_length,
        )
        summary_text = wikipedia_client.summarize_for_query(title, query, max_length=max_length)
        return {"title": title, "query": query, "summary": summary_text}

    @server.resource("/summary/{title}/section/{section_title}/length/{max_length}")
    def summary_section_resource(title: str, section_title: str, max_length: int):
        logger.info(
            "Resource: Getting summary for section: %s in article: %s, max_length: %d",
            section_title,
            title,
            max_length,
        )
        summary_text = wikipedia_client.summarize_section(title, section_title, max_length=max_length)
        return {"title": title, "section_title": section_title, "summary": summary_text}

    @server.resource("/sections/{title}")
    def sections_resource(title: str):
        logger.info("Getting sections for: %s", title)
        sections_list = wikipedia_client.get_sections(title)
        return {"title": title, "sections": sections_list}

    @server.resource("/links/{title}")
    def links_resource(title: str):
        logger.info("Getting links for: %s", title)
        links_list = wikipedia_client.get_links(title)
        return {"title": title, "links": links_list}

    @server.resource("/facts/{title}/topic/{topic_within_article}/count/{count}")
    def key_facts_resource(title: str, topic_within_article: str, count: int):
        logger.info(
            "Resource: Extracting key facts for article: %s, topic: %s, count: %d",
            title,
            topic_within_article,
            count,
        )
        facts_list = wikipedia_client.extract_facts(title, topic_within_article, count=count)
        return {
            "title": title,
            "topic_within_article": topic_within_article,
            "facts": facts_list,
        }

    @server.resource("/coordinates/{title}")
    def coordinates_resource(title: str):
        logger.info("Getting coordinates for: %s", title)
        coordinates_data = wikipedia_client.get_coordinates(title)
        return coordinates_data

    return server
