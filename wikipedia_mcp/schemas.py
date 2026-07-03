"""Typed output schemas for Wikipedia MCP tools."""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, ConfigDict


class MCPBaseModel(BaseModel):
    model_config = ConfigDict(extra="allow")


class SearchResultItem(MCPBaseModel):
    title: str
    snippet: str = ""
    pageid: int = 0
    wordcount: int = 0
    timestamp: str = ""


class SearchWikipediaResponse(MCPBaseModel):
    query: str
    results: list[SearchResultItem] = []
    status: str
    count: Optional[int] = None
    language: Optional[str] = None
    message: Optional[str] = None


class ConnectivityResponse(MCPBaseModel):
    status: str
    url: str
    language: str
    site_name: Optional[str] = None
    server: Optional[str] = None
    response_time_ms: Optional[float] = None
    error: Optional[str] = None
    error_type: Optional[str] = None


class ArticleResponse(MCPBaseModel):
    title: str
    exists: bool
    pageid: Optional[int] = None
    summary: Optional[str] = None
    text: Optional[str] = None
    url: Optional[str] = None
    sections: list[dict[str, Any]] = []
    categories: list[str] = []
    links: list[str] = []
    error: Optional[str] = None


class SummaryResponse(MCPBaseModel):
    title: str
    summary: Optional[str] = None
    error: Optional[str] = None


class QuerySummaryResponse(MCPBaseModel):
    title: str
    query: str
    summary: str


class SectionSummaryResponse(MCPBaseModel):
    title: str
    section_title: str
    summary: str


class KeyFactsResponse(MCPBaseModel):
    title: str
    topic_within_article: str
    facts: list[str]


class RelatedTopicsResponse(MCPBaseModel):
    title: str
    related_topics: list[dict[str, Any]]


class SectionsResponse(MCPBaseModel):
    title: str
    sections: list[dict[str, Any]]


class LinksResponse(MCPBaseModel):
    title: str
    links: list[str]


class CoordinateItem(MCPBaseModel):
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    primary: bool = False
    globe: str = "earth"
    type: str = ""
    name: str = ""
    region: str = ""
    country: str = ""


class CoordinatesResponse(MCPBaseModel):
    title: str
    exists: bool
    pageid: Optional[int] = None
    coordinates: list[CoordinateItem] | None = None
    error: Optional[str] = None
    message: Optional[str] = None


class TableItem(MCPBaseModel):
    index: int
    caption: str = ""
    section: str = ""
    headers: list[str] = []
    rows: list[list[str]] = []


class TablesResponse(MCPBaseModel):
    title: str
    exists: bool
    tables: list[TableItem] = []
    error: Optional[str] = None
    message: Optional[str] = None


class TableSummary(MCPBaseModel):
    index: int
    caption: str = ""
    section: str = ""
    headers: list[str] = []
    row_count: int = 0
    column_count: int = 0


class ListTablesResponse(MCPBaseModel):
    title: str
    exists: bool
    count: int = 0
    tables: list[TableSummary] = []
    error: Optional[str] = None
    message: Optional[str] = None


class GetTableResponse(MCPBaseModel):
    """Response for get_table.

    Depending on the requested granularity this returns a whole table, a single
    row, a single column, or a single cell, so most fields are optional.
    """

    title: str
    exists: bool
    table_index: Optional[int] = None
    caption: Optional[str] = None
    section: Optional[str] = None
    headers: Optional[list[str]] = None
    rows: Optional[list[list[str]]] = None
    row_count: Optional[int] = None
    column_count: Optional[int] = None
    row_index: Optional[int] = None
    row: Optional[list[str]] = None
    column_index: Optional[int] = None
    header: Optional[str] = None
    value: Optional[str] = None
    values: Optional[list[str]] = None
    error: Optional[str] = None
    message: Optional[str] = None


def model_output_schema(model: type[MCPBaseModel]) -> dict[str, Any]:
    """Return object JSON schema suitable for MCP tool outputSchema."""
    return model.model_json_schema()
