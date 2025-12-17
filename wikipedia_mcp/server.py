"""
Wikipedia MCP server implementation.

This module defines the FastMCP server and registers tools and resources for
interacting with Wikipedia via the WikipediaClient. It includes search,
article retrieval, summaries, and diagnostics.
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

    # ------------------------------------------------------------------
    # Tool: search_wikipedia
    # ------------------------------------------------------------------
    @server.tool()
    def search_wikipedia(query: str, limit: int = 10) -> Dict[str, Any]:
        """
        Search Wikipedia for articles matching a query.

        Parameters:
            query: The search term to look up on Wikipedia.
            limit: Maximum number of results to return (1-500).

        Returns a dictionary with the search query, results, status, and
        additional metadata. If the query is empty or invalid, the status
        will be 'error' and an explanatory message is included.
        """
        logger.info("Tool: Searching Wikipedia for '%s' (limit=%d)", query, limit)

        # Validate query
        if not query or not query.strip():
            logger.warning("Search tool called with empty query")
            return {
                "query": query,
                "results": [],
                "status": "error",
                "message": "Empty search query provided",
            }

        # Sanitize and validate limit
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

    # ------------------------------------------------------------------
    # Tool: test_wikipedia_connectivity
    # ------------------------------------------------------------------
    @server.tool()
    def test_wikipedia_connectivity() -> Dict[str, Any]:
        """
        Provide diagnostics for Wikipedia API connectivity.

        Returns the base API URL, language, site information, and response
        time in milliseconds. If connectivity fails, status will be 'failed'
        with error details.
        """
        logger.info("Tool: Testing Wikipedia connectivity")
        diagnostics = wikipedia_client.test_connectivity()

        # Round response_time_ms for nicer output if present
        if (
            diagnostics.get("status") == "success"
            and "response_time_ms" in diagnostics
            and isinstance(diagnostics["response_time_ms"], (int, float))
        ):
            diagnostics["response_time_ms"] = round(float(diagnostics["response_time_ms"]), 3)
        return diagnostics

    # ------------------------------------------------------------------
    # Tool: get_article
    # ------------------------------------------------------------------
    @server.tool()
    def get_article(title: str) -> Dict[str, Any]:
        """
        Get the full content of a Wikipedia article.

        Returns a dictionary containing article details or an error message
        if retrieval fails.
        """
        logger.info(f"Tool: Getting article: {title}")
        article = wikipedia_client.get_article(title)
        # Ensure we always return a dictionary
        return article or {"title": title, "exists": False, "error": "Unknown error retrieving article"}

    # ------------------------------------------------------------------
    # Tool: get_summary
    # ------------------------------------------------------------------
    @server.tool()
    def get_summary(title: str) -> Dict[str, Any]:
        """
        Get a summary of a Wikipedia article.

        Returns a dictionary with the title and summary string. On error,
        includes an error message instead of a summary.
        """
        logger.info(f"Tool: Getting summary for: {title}")
        summary = wikipedia_client.get_summary(title)
        if summary and not summary.startswith("Error"):
            return {"title": title, "summary": summary}
        else:
            return {"title": title, "summary": None, "error": summary}

    # ------------------------------------------------------------------
    # Tool: summarize_article_for_query
    # ------------------------------------------------------------------
    @server.tool()
    def summarize_article_for_query(
        title: str,
        query: str,
        max_length: Annotated[int, Field(title="Max Length")] = 250,
    ) -> Dict[str, Any]:
        """
        Get a summary of a Wikipedia article tailored to a specific query.

        The summary is a snippet around the query within the article text or
        summary. The max_length parameter controls the length of the snippet.
        """
        logger.info(f"Tool: Getting query-focused summary for article: {title}, query: {query}")
        summary = wikipedia_client.summarize_for_query(title, query, max_length=max_length)
        return {"title": title, "query": query, "summary": summary}

    # ------------------------------------------------------------------
    # Tool: summarize_article_section
    # ------------------------------------------------------------------
    @server.tool()
    def summarize_article_section(
        title: str,
        section_title: str,
        max_length: Annotated[int, Field(title="Max Length")] = 150,
    ) -> Dict[str, Any]:
        """
        Get a summary of a specific section of a Wikipedia article.

        Returns a dictionary containing the section summary or an error.
        """
        logger.info(f"Tool: Getting summary for section: {section_title} in article: {title}")
        summary = wikipedia_client.summarize_section(title, section_title, max_length=max_length)
        return {"title": title, "section_title": section_title, "summary": summary}

    # ------------------------------------------------------------------
    # Tool: extract_key_facts
    # ------------------------------------------------------------------
    @server.tool()
    def extract_key_facts(
        title: str,
        topic_within_article: Annotated[str, Field(title="Topic Within Article")] = "",
        count: int = 5,
    ) -> Dict[str, Any]:
        """
        Extract key facts from a Wikipedia article, optionally focused on a topic.

        Returns a dictionary containing a list of facts.
        """
        logger.info(f"Tool: Extracting key facts for article: {title}, topic: {topic_within_article}")
        topic = topic_within_article if topic_within_article.strip() else None
        facts = wikipedia_client.extract_facts(title, topic, count=count)
        return {"title": title, "topic_within_article": topic_within_article, "facts": facts}

    # ------------------------------------------------------------------
    # Tool: get_related_topics
    # ------------------------------------------------------------------
    @server.tool()
    def get_related_topics(title: str, limit: int = 10) -> Dict[str, Any]:
        """
        Get topics related to a Wikipedia article based on links and categories.

        Returns a list of related topics up to the specified limit.
        """
        logger.info(f"Tool: Getting related topics for: {title}")
        related = wikipedia_client.get_related_topics(title, limit=limit)
        return {"title": title, "related_topics": related}

    # ------------------------------------------------------------------
    # Tool: get_sections
    # ------------------------------------------------------------------
    @server.tool()
    def get_sections(title: str) -> Dict[str, Any]:
        """
        Get the sections of a Wikipedia article.

        Returns a dictionary with the article title and list of sections.
        """
        logger.info(f"Tool: Getting sections for: {title}")
        sections = wikipedia_client.get_sections(title)
        return {"title": title, "sections": sections}

    # ------------------------------------------------------------------
    # Tool: get_links
    # ------------------------------------------------------------------
    @server.tool()
    def get_links(title: str) -> Dict[str, Any]:
        """
        Get the links contained within a Wikipedia article.

        Returns a dictionary with the article title and list of links.
        """
        logger.info(f"Tool: Getting links for: {title}")
        links = wikipedia_client.get_links(title)
        return {"title": title, "links": links}

    # ------------------------------------------------------------------
    # Tool: get_coordinates
    # ------------------------------------------------------------------
    @server.tool()
    def get_coordinates(title: str) -> Dict[str, Any]:
        """
        Get the coordinates of a Wikipedia article.

        Returns a dictionary containing coordinate information.
        """
        logger.info(f"Tool: Getting coordinates for: {title}")
        coordinates = wikipedia_client.get_coordinates(title)
        return coordinates

    # ------------------------------------------------------------------
    # HTTP Resources
    # ------------------------------------------------------------------

    @server.resource("/search/{query}")
    def search(query: str) -> Dict[str, Any]:
        """
        HTTP resource to search Wikipedia via GET /search/{query}.

        Uses the underlying WikipediaClient.search and always returns a dictionary.
        """
        logger.info(f"Searching Wikipedia for: {query}")
        results = wikipedia_client.search(query, limit=10)
        return {"query": query, "results": results}

    @server.resource("/article/{title}")
    def article(title: str) -> Dict[str, Any]:
        """
        HTTP resource to fetch a full article via GET /article/{title}.

        Returns article data or an error dictionary.
        """
        logger.info(f"Getting article: {title}")
        article_data = wikipedia_client.get_article(title)
        return article_data or {"title": title, "exists": False, "error": "Unknown error retrieving article"}

    @server.resource("/summary/{title}")
    def summary(title: str) -> Dict[str, Any]:
        """
        HTTP resource to fetch the summary of an article via GET /summary/{title}.
        """
        logger.info(f"Getting summary for: {title}")
        summary_text = wikipedia_client.get_summary(title)
        if summary_text and not summary_text.startswith("Error"):
            return {"title": title, "summary": summary_text}
        else:
            return {"title": title, "summary": None, "error": summary_text}

    @server.resource("/summary/{title}/query/{query}/length/{max_length}")
    def summary_for_query_resource(title: str, query: str, max_length: int) -> Dict[str, Any]:
        """
        HTTP resource to fetch a query-focused summary via GET /summary/{title}/query/{query}/length/{max_length}.
        """
        logger.info(
            f"Resource: Getting query-focused summary for article: {title}, query: {query}, max_length: {max_length}"
        )
        summary_text = wikipedia_client.summarize_for_query(title, query, max_length=max_length)
        return {"title": title, "query": query, "summary": summary_text}

    @server.resource("/summary/{title}/section/{section_title}/length/{max_length}")
    def summary_section_resource(title: str, section_title: str, max_length: int) -> Dict[str, Any]:
        """
        HTTP resource to fetch a section summary via GET /summary/{title}/section/{section_title}/length/{max_length}.
        """
        logger.info(
            f"Resource: Getting summary for section: {section_title} in article: {title}, max_length: {max_length}"
        )
        summary_text = wikipedia_client.summarize_section(title, section_title, max_length=max_length)
        return {"title": title, "section_title": section_title, "summary": summary_text}

    @server.resource("/sections/{title}")
    def sections_resource(title: str) -> Dict[str, Any]:
        """
        HTTP resource to fetch sections via GET /sections/{title}.
        """
        logger.info(f"Getting sections for: {title}")
        sections_list = wikipedia_client.get_sections(title)
        return {"title": title, "sections": sections_list}

    @server.resource("/links/{title}")
    def links_resource(title: str) -> Dict[str, Any]:
        """
        HTTP resource to fetch links via GET /links/{title}.
        """
        logger.info(f"Getting links for: {title}")
        links_list = wikipedia_client.get_links(title)
        return {"title": title, "links": links_list}

    @server.resource("/facts/{title}/topic/{topic_within_article}/count/{count}")
    def key_facts_resource(title: str, topic_within_article: str, count: int) -> Dict[str, Any]:
        """
        HTTP resource to fetch key facts via GET /facts/{title}/topic/{topic_within_article}/count/{count}.
        """
        logger.info(
            f"Resource: Extracting key facts for article: {title}, topic: {topic_within_article}, count: {count}"
        )
        facts_list = wikipedia_client.extract_facts(title, topic_within_article, count=count)
        return {
            "title": title,
            "topic_within_article": topic_within_article,
            "facts": facts_list,
        }

    @server.resource("/coordinates/{title}")
    def coordinates_resource(title: str) -> Dict[str, Any]:
        """
        HTTP resource to fetch coordinates via GET /coordinates/{title}.
        """
        logger.info(f"Getting coordinates for: {title}")
        coordinates_data = wikipedia_client.get_coordinates(title)
        return coordinates_data

    return server
