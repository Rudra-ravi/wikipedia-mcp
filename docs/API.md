# Wikipedia MCP API Documentation

This document describes the API endpoints and tools available in the Wikipedia MCP server.

## Transport Notes

- `stdio` is the default local transport.
- `http` / `streamable-http` are the preferred network transports (default path: `/mcp`).
- `sse` is retained for compatibility and considered legacy.
- Tool/resource interfaces below are transport-agnostic.

## HTTP Endpoints

### Search Articles
```
GET /search/{query}
```
Search Wikipedia for articles matching a query.

**Parameters:**
- `query` (string, required): The search query

**Response:**
```json
{
    "query": "search query",
    "results": [
        {
            "title": "Article title",
            "snippet": "Article snippet",
            "pageid": 12345,
            "wordcount": 1000,
            "timestamp": "2024-03-08T12:00:00Z"
        }
    ]
}
```

### Get Article
```
GET /article/{title}
```
Get the full content of a Wikipedia article.

**Parameters:**
- `title` (string, required): The title of the Wikipedia article

**Response:**
```json
{
    "title": "Article title",
    "pageid": 12345,
    "summary": "Article summary",
    "text": "Full article text",
    "url": "https://en.wikipedia.org/wiki/Article_title",
    "sections": [
        {
            "title": "Section title",
            "text": "Section content",
            "level": 1
        }
    ],
    "categories": ["Category1", "Category2"],
    "links": ["Link1", "Link2"],
    "exists": true
}
```

### Get Summary
```
GET /summary/{title}
```
Get a summary of a Wikipedia article.

**Parameters:**
- `title` (string, required): The title of the Wikipedia article

**Response:**
```json
{
    "title": "Article title",
    "summary": "Article summary"
}
```

### Get Sections
```
GET /sections/{title}
```
Get the sections of a Wikipedia article.

**Parameters:**
- `title` (string, required): The title of the Wikipedia article

**Response:**
```json
{
    "title": "Article title",
    "sections": [
        {
            "title": "Section title",
            "text": "Section content",
            "level": 1
        }
    ]
}
```

### Get Links
```
GET /links/{title}
```
Get the links in a Wikipedia article.

**Parameters:**
- `title` (string, required): The title of the Wikipedia article

**Response:**
```json
{
    "title": "Article title",
    "links": ["Link1", "Link2", "Link3"]
}
```

## MCP Tools

Every canonical tool also has an alias prefixed with `wikipedia_` (for example, `wikipedia_search_wikipedia`, `wikipedia_get_article`, etc.) with the same schema and behavior.

### search_wikipedia
Search Wikipedia for articles matching a query.

**Parameters:**
- `query` (string, required): The search query
- `limit` (integer, optional, default=10): Maximum number of results to return

### get_article
Get the full content of a Wikipedia article.

**Parameters:**
- `title` (string, required): The title of the Wikipedia article

### get_summary
Get a summary of a Wikipedia article.

**Parameters:**
- `title` (string, required): The title of the Wikipedia article

### get_related_topics
Get topics related to a Wikipedia article based on links and categories.

**Parameters:**
- `title` (string, required): The title of the Wikipedia article
- `limit` (integer, optional, default=10): Maximum number of related topics to return

### get_sections
Get the sections of a Wikipedia article.

**Parameters:**
- `title` (string, required): The title of the Wikipedia article

**Response:**
```json
{
  "title": "Article title",
  "sections": [
    { "title": "Section title", "text": "Section content", "level": 1 }
  ]
}
```

### get_links
Get the links in a Wikipedia article.

**Parameters:**
- `title` (string, required): The title of the Wikipedia article

**Response:**
```json
{
  "title": "Article title",
  "links": ["Link1", "Link2", "Link3"]
}
```

### get_coordinates
Get the coordinates of a Wikipedia article.

**Parameters:**
- `title` (string, required): The title of the Wikipedia article

**Response:**
```json
{
  "title": "Eiffel Tower",
  "pageid": 1359783,
  "coordinates": [
    {
      "latitude": 48.8584,
      "longitude": 2.2945,
      "primary": true,
      "globe": "earth",
      "type": "landmark",
      "name": "Eiffel Tower",
      "region": "FR-75",
      "country": "FR"
    }
  ],
  "exists": true,
  "error": null
}
```

### get_tables
Extract tables from a Wikipedia article. Parses the article's rendered HTML and returns each table as headers plus data rows. Citation markers (e.g. `[1]`, `[a]`) are stripped and `colspan`/`rowspan` cells are expanded.

**Parameters:**
- `title` (string, required): The title of the Wikipedia article
- `include_all_tables` (boolean, optional, default=false): When false, only data tables (`class="wikitable"`) are returned; when true, infoboxes, navboxes, and other tables are included

**Response:**
```json
{
  "title": "List of countries by population (United Nations)",
  "exists": true,
  "tables": [
    {
      "index": 0,
      "caption": "List of countries and territories by population",
      "section": "",
      "headers": ["Country or territory", "Population (1 July 2023)", "UN continental region"],
      "rows": [
        ["India", "1,438,069,596", "Asia"],
        ["China", "1,422,584,933", "Asia"]
      ]
    }
  ]
}
```

Each table's `section` is the article section it appears under (`""` for the lead/introduction).

### list_tables
List the tables in an article without their full contents — useful for discovering which table to fetch, which section it belongs to, and how many entries each has.

**Parameters:**
- `title` (string, required): The article title
- `include_all_tables` (boolean, optional, default=false): Include infoboxes/navboxes as well

**Response:**
```json
{
  "title": "List of countries by population (United Nations)",
  "exists": true,
  "count": 1,
  "tables": [
    {
      "index": 0,
      "caption": "List of countries and territories by population",
      "section": "",
      "headers": ["Country or territory", "Population (1 July 2023)", "UN continental region"],
      "row_count": 238,
      "column_count": 6
    }
  ]
}
```

### get_table
Fetch a single table, or a specific row, column, or cell within it.

**Parameters:**
- `title` (string, required): The article title
- `table_index` (integer, optional, default=0): Which table to fetch (0-based; see `list_tables`)
- `row` (integer, optional, default=-1): A 0-based data-row index. If `>= 0`, only that row is returned
- `column` (string, optional, default=""): A column reference — either a 0-based index (as a string, e.g. `"2"`) or a header name (case-insensitive). If set, only that column is returned
- `include_all_tables` (boolean, optional, default=false): Index into all tables rather than just data tables

With neither `row` nor `column`, the whole table is returned. Supplying both returns a single cell.

**Response (whole table):**
```json
{
  "title": "List of countries by population (United Nations)",
  "exists": true,
  "table_index": 0,
  "caption": "List of countries and territories by population",
  "section": "",
  "headers": ["Country or territory", "Population (1 July 2023)", "UN continental region"],
  "rows": [["India", "1,438,069,596", "Asia"]],
  "row_count": 238,
  "column_count": 6
}
```

**Response (single column, `column="Country or territory"`):**
```json
{
  "title": "List of countries by population (United Nations)",
  "exists": true,
  "table_index": 0,
  "column_index": 0,
  "header": "Country or territory",
  "values": ["World", "India", "China", "United States"]
}
```

### summarize_article_for_query
Get a summary of a Wikipedia article tailored to a specific query.

**Parameters:**
- `title` (string, required): The article title
- `query` (string, required): The query to focus the summary on
- `max_length` (integer, optional, default=250): Maximum summary length

**Response:**
```json
{
  "title": "Quantum computing",
  "query": "Shor's algorithm",
  "summary": "…contextual snippet around the query…"
}
```

### summarize_article_section
Get a summary of a specific section of a Wikipedia article.

**Parameters:**
- `title` (string, required): The article title
- `section_title` (string, required): The section to summarize
- `max_length` (integer, optional, default=150): Maximum summary length

**Response:**
```json
{
  "title": "Quantum computing",
  "section_title": "History",
  "summary": "…first N characters of the section…"
}
```

### extract_key_facts
Extract key facts from a Wikipedia article, optionally focused on a topic within the article.

**Parameters:**
- `title` (string, required): The article title
- `topic_within_article` (string, optional): Topic/section to focus on
- `count` (integer, optional, default=5): Number of facts

**Response:**
```json
{
  "title": "Alan Turing",
  "topic_within_article": "Early life",
  "facts": [
    "Alan Turing was born in…",
    "He studied at…"
  ]
}
```

### test_wikipedia_connectivity
Diagnostic tool to verify connectivity to the Wikipedia API for the configured language/variant.

**Parameters:**
- none

**Response:**
```json
{
  "status": "success",
  "url": "https://en.wikipedia.org/w/api.php",
  "language": "en",
  "site_name": "Wikipedia",
  "server": "https://en.wikipedia.org",
  "response_time_ms": 123.45
}
```

## Additional MCP Resources (path-like)

These are exposed as MCP resources and available when running with SSE transport:

- `search/{query}`
- `article/{title}`
- `summary/{title}`
- `sections/{title}`
- `links/{title}`
- `coordinates/{title}`
- `tables/{title}`
- `tables/{title}/list`
- `tables/{title}/index/{table_index}`
- `summary/{title}/query/{query}/length/{max_length}`
- `summary/{title}/section/{section_title}/length/{max_length}`
- `facts/{title}/topic/{topic_within_article}/count/{count}`

Note: These are not general-purpose REST endpoints; they are part of the Model Context Protocol (MCP) resource interface.
