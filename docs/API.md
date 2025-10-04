# Wikipedia MCP API Documentation

This document describes the API endpoints and tools available in the Wikipedia MCP server.

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
- `summary/{title}/query/{query}/length/{max_length}`
- `summary/{title}/section/{section_title}/length/{max_length}`
- `facts/{title}/topic/{topic_within_article}/count/{count}`

Note: These are not general-purpose REST endpoints; they are part of the Model Context Protocol (MCP) resource interface.
