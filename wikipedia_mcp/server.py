"""
Wikipedia MCP server implementation.
"""

import logging
from typing import Dict, Optional, Any, Annotated
from pydantic import Field

from fastmcp import FastMCP
from wikipedia_mcp.wikipedia_client import WikipediaClient

logger = logging.getLogger(__name__)


def create_server(
    language: str = "en",
    country: Optional[str] = None,
    enable_cache: bool = False,
    access_token: Optional[str] = None,
) -> FastMCP:
    """Create and configure the Wikipedia MCP server."""
    server = FastMCP(
        name="Wikipedia",
    )

    # Initialize Wikipedia client
    wikipedia_client = WikipediaClient(
        language=language,
        country=country,
        enable_cache=enable_cache,
        access_token=access_token,
    )

    # Register tools
    @server.tool()
    def search_wikipedia(query: str, limit: int = 10) -> Dict[str, Any]:
        """Search Wikipedia for articles matching a query."""
        logger.info("Tool: Searching Wikipedia for '%s' (limit=%d)", query, limit)

        if not query or not query.strip():
            logger.warning("Search tool called with empty query")
            return {
                "query": query,
                "results": [],
                "status": "error",
                "message": "Empty or invalid search query provided",
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
        response: Dict[str, Any] = {
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

    @server.tool()
    def test_wikipedia_connectivity() -> Dict[str, Any]:
        """Provide diagnostics for Wikipedia API connectivity."""
        logger.info("Tool: Testing Wikipedia connectivity")
        return wikipedia_client.test_connectivity()

    @server.tool()
    def get_article(title: str) -> Dict[str, Any]:
        """Get the full content of a Wikipedia article."""
        logger.info(f"Tool: Getting article: {title}")
        article = wikipedia_client.get_article(title)
        return article

    @server.tool()
    def get_summary(title: str) -> Dict[str, Any]:
        """Get a summary of a Wikipedia article."""
        logger.info(f"Tool: Getting summary for: {title}")
        summary = wikipedia_client.get_summary(title)
        return {"title": title, "summary": summary}

    @server.tool()
    def summarize_article_for_query(
        title: str,
        query: str,
        max_length: Annotated[int, Field(title="Max Length")] = 250,
    ) -> Dict[str, Any]:
        """Get a summary of a Wikipedia article tailored to a specific query."""
        logger.info(f"Tool: Getting query-focused summary for article: {title}, query: {query}")
        # Assuming wikipedia_client has a method like summarize_for_query
        summary = wikipedia_client.summarize_for_query(title, query, max_length=max_length)
        return {"title": title, "query": query, "summary": summary}

    @server.tool()
    def summarize_article_section(
        title: str,
        section_title: str,
        max_length: Annotated[int, Field(title="Max Length")] = 150,
    ) -> Dict[str, Any]:
        """Get a summary of a specific section of a Wikipedia article."""
        logger.info(f"Tool: Getting summary for section: {section_title} in article: {title}")
        # Assuming wikipedia_client has a method like summarize_section
        summary = wikipedia_client.summarize_section(title, section_title, max_length=max_length)
        return {"title": title, "section_title": section_title, "summary": summary}

    @server.tool()
    def extract_key_facts(
        title: str,
        topic_within_article: Annotated[str, Field(title="Topic Within Article")] = "",
        count: int = 5,
    ) -> Dict[str, Any]:
        """Extract key facts from a Wikipedia article, optionally focused on a topic."""
        logger.info(f"Tool: Extracting key facts for article: {title}, topic: {topic_within_article}")
        # Convert empty string to None for backward compatibility
        topic = topic_within_article if topic_within_article.strip() else None
        # Assuming wikipedia_client has a method like extract_facts
        facts = wikipedia_client.extract_facts(title, topic, count=count)
        return {
            "title": title,
            "topic_within_article": topic_within_article,
            "facts": facts,
        }

    @server.tool()
    def get_related_topics(title: str, limit: int = 10) -> Dict[str, Any]:
        """Get topics related to a Wikipedia article based on links and categories."""
        logger.info(f"Tool: Getting related topics for: {title}")
        related = wikipedia_client.get_related_topics(title, limit=limit)
        return {"title": title, "related_topics": related}

    @server.tool()
    def get_sections(title: str) -> Dict[str, Any]:
        """Get the sections of a Wikipedia article."""
        logger.info(f"Tool: Getting sections for: {title}")
        sections = wikipedia_client.get_sections(title)
        return {"title": title, "sections": sections}

    @server.tool()
    def get_links(title: str) -> Dict[str, Any]:
        """Get the links contained within a Wikipedia article."""
        logger.info(f"Tool: Getting links for: {title}")
        links = wikipedia_client.get_links(title)
        return {"title": title, "links": links}

    @server.tool()
    def get_coordinates(title: str) -> Dict[str, Any]:
        """Get the coordinates of a Wikipedia article."""
        logger.info(f"Tool: Getting coordinates for: {title}")
        coordinates = wikipedia_client.get_coordinates(title)
        return coordinates

    @server.resource("/search/{query}")
    def search(query: str) -> Dict[str, Any]:
        """Search Wikipedia for articles matching a query."""
        logger.info(f"Searching Wikipedia for: {query}")
        results = wikipedia_client.search(query, limit=10)
        return {"query": query, "results": results}

    @server.resource("/article/{title}")
    def article(title: str) -> Dict[str, Any]:
        """Get the full content of a Wikipedia article."""
        logger.info(f"Getting article: {title}")
        article = wikipedia_client.get_article(title)
        return article

    @server.resource("/summary/{title}")
    def summary(title: str) -> Dict[str, Any]:
        """Get a summary of a Wikipedia article."""
        logger.info(f"Getting summary for: {title}")
        summary = wikipedia_client.get_summary(title)
        return {"title": title, "summary": summary}

    @server.resource("/summary/{title}/query/{query}/length/{max_length}")
    def summary_for_query_resource(title: str, query: str, max_length: int) -> Dict[str, Any]:
        """Get a summary of a Wikipedia article tailored to a specific query."""
        logger.info(
            f"Resource: Getting query-focused summary for article: {title}, query: {query}, max_length: {max_length}"
        )
        summary = wikipedia_client.summarize_for_query(title, query, max_length=max_length)
        return {"title": title, "query": query, "summary": summary}

    @server.resource("/summary/{title}/section/{section_title}/length/{max_length}")
    def summary_section_resource(title: str, section_title: str, max_length: int) -> Dict[str, Any]:
        """Get a summary of a specific section of a Wikipedia article."""
        logger.info(
            f"Resource: Getting summary for section: {section_title} in article: {title}, max_length: {max_length}"
        )
        summary = wikipedia_client.summarize_section(title, section_title, max_length=max_length)
        return {"title": title, "section_title": section_title, "summary": summary}

    @server.resource("/sections/{title}")
    def sections(title: str) -> Dict[str, Any]:
        """Get the sections of a Wikipedia article."""
        logger.info(f"Getting sections for: {title}")
        sections = wikipedia_client.get_sections(title)
        return {"title": title, "sections": sections}

    @server.resource("/links/{title}")
    def links(title: str) -> Dict[str, Any]:
        """Get the links in a Wikipedia article."""
        logger.info(f"Getting links for: {title}")
        links = wikipedia_client.get_links(title)
        return {"title": title, "links": links}

    @server.resource("/facts/{title}/topic/{topic_within_article}/count/{count}")
    def key_facts_resource(title: str, topic_within_article: str, count: int) -> Dict[str, Any]:
        """Extract key facts from a Wikipedia article."""
        logger.info(
            f"Resource: Extracting key facts for article: {title}, topic: {topic_within_article}, count: {count}"
        )
        facts = wikipedia_client.extract_facts(title, topic_within_article, count=count)
        return {
            "title": title,
            "topic_within_article": topic_within_article,
            "facts": facts,
        }

    @server.resource("/coordinates/{title}")
    def coordinates(title: str) -> Dict[str, Any]:
        """Get the coordinates of a Wikipedia article."""
        logger.info(f"Getting coordinates for: {title}")
        coordinates = wikipedia_client.get_coordinates(title)
        return coordinates

    return server
