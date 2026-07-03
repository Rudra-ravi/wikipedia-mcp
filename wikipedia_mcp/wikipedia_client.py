"""
Wikipedia API client implementation.

This class encapsulates logic for interacting with the Wikipedia API,
including language and country resolution, search, article retrieval,
summaries, related topics, key facts, and coordinate lookup. It also
supports optional caching and authentication via personal access tokens.
"""

import logging
import re
import wikipediaapi
import requests
from html.parser import HTMLParser
from typing import Dict, List, Optional, Any
import functools
import time
from wikipedia_mcp import __version__

logger = logging.getLogger(__name__)

# Bounds to keep table extraction responses reasonably sized for LLM consumption.
_MAX_TABLES = 50
_MAX_ROWS_PER_TABLE = 400
_MAX_CELLS_PER_ROW = 60
_MAX_CELL_CHARS = 2000

# Reference/citation markers that add noise to extracted cell text, e.g. "[1]",
# "[12]", "[a]", "[note 3]", "[nb 1]", "[edit]", "[citation needed]".
_REFERENCE_MARKER_RE = re.compile(
    r"\[(?:\d+|[a-z]{1,3}|edit|(?:note|nb) \d+|citation needed)\]",
    re.IGNORECASE,
)


class _WikiTableParser(HTMLParser):
    """Extract HTML tables into structured rows of cells.

    Handles nested tables (each ``<table>`` becomes a separate result),
    ``colspan``/``rowspan`` expansion, and light cleanup of citation markers.
    Cells are captured as ``(text, is_header)`` tuples so callers can split
    header rows from data rows.
    """

    _HEADING_TAGS = {"h1", "h2", "h3", "h4", "h5", "h6"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        # Completed tables, in the order their </table> is seen.
        self.tables: List[Dict[str, Any]] = []
        # Stack of tables currently open (to support nesting).
        self._stack: List[Dict[str, Any]] = []
        # Text of the most recent section heading seen at the document level;
        # "" means the lead/introduction (before any heading).
        self._current_section: str = ""
        self._in_heading: bool = False
        self._heading_parts: List[str] = []

    def _new_table(self, attrs: Dict[str, str]) -> Dict[str, Any]:
        return {
            "class": attrs.get("class", ""),
            "caption": "",
            "rows": [],  # list of rows; each row is list of (text, is_header)
            "_row": None,  # current row being built
            "_cell_parts": None,  # text fragments for the current cell
            "_cell_is_header": False,
            "_cell_colspan": 1,
            "_cell_rowspan": 1,
            "_in_caption": False,
            # Pending rowspans keyed by column index -> [text, is_header, rows_remaining]
            "_pending_rowspans": {},
            "_col_cursor": 0,
        }

    @staticmethod
    def _to_int(value: Optional[str], default: int = 1) -> int:
        try:
            parsed = int(str(value).strip())
            return parsed if parsed > 0 else default
        except (TypeError, ValueError):
            return default

    def handle_starttag(self, tag, attrs):
        attr_dict = {k: (v or "") for k, v in attrs}

        # Track section headings at the document level (outside any table) so
        # each table can be attributed to the section it appears under.
        if tag in self._HEADING_TAGS and not self._stack:
            self._in_heading = True
            self._heading_parts = []
            return

        if tag == "table":
            table = self._new_table(attr_dict)
            table["section"] = self._current_section
            self._stack.append(table)
            return

        if not self._stack:
            return

        table = self._stack[-1]

        if tag == "caption":
            table["_in_caption"] = True
        elif tag == "tr":
            table["_row"] = []
            table["_col_cursor"] = 0
            self._fill_pending_rowspans(table)
        elif tag in ("td", "th"):
            if table["_row"] is None:
                # Cell outside an explicit <tr>; start an implicit row.
                table["_row"] = []
                table["_col_cursor"] = 0
                self._fill_pending_rowspans(table)
            table["_cell_parts"] = []
            table["_cell_is_header"] = tag == "th"
            table["_cell_colspan"] = min(self._to_int(attr_dict.get("colspan")), _MAX_CELLS_PER_ROW)
            table["_cell_rowspan"] = self._to_int(attr_dict.get("rowspan"))
        elif tag in ("br", "p", "li"):
            if table["_cell_parts"] is not None:
                table["_cell_parts"].append(" ")

    def handle_endtag(self, tag):
        if tag in self._HEADING_TAGS and self._in_heading and not self._stack:
            self._in_heading = False
            self._current_section = self._clean_text("".join(self._heading_parts))
            self._heading_parts = []
            return

        if tag == "table":
            if self._stack:
                self.tables.append(self._finalize_table(self._stack.pop()))
            return

        if not self._stack:
            return

        table = self._stack[-1]

        if tag == "caption":
            table["_in_caption"] = False
        elif tag in ("td", "th"):
            self._close_cell(table)
        elif tag == "tr":
            self._close_row(table)

    def handle_data(self, data):
        if self._in_heading and not self._stack:
            self._heading_parts.append(data)
            return
        if not self._stack:
            return
        table = self._stack[-1]
        if table["_in_caption"]:
            table["caption"] += data
        elif table["_cell_parts"] is not None:
            table["_cell_parts"].append(data)

    # -- helpers -------------------------------------------------------
    def _fill_pending_rowspans(self, table: Dict[str, Any]) -> None:
        """Insert carried-over rowspan cells at the front of a new row."""
        pending = table["_pending_rowspans"]
        cursor = table["_col_cursor"]
        while cursor in pending and len(table["_row"]) < _MAX_CELLS_PER_ROW:
            text, is_header, remaining = pending[cursor]
            table["_row"].append((text, is_header))
            remaining -= 1
            if remaining <= 0:
                del pending[cursor]
            else:
                pending[cursor] = [text, is_header, remaining]
            cursor += 1
        table["_col_cursor"] = cursor

    def _close_cell(self, table: Dict[str, Any]) -> None:
        if table["_cell_parts"] is None:
            return
        text = self._clean_text("".join(table["_cell_parts"]))
        is_header = table["_cell_is_header"]
        colspan = table["_cell_colspan"]
        rowspan = table["_cell_rowspan"]

        for _ in range(colspan):
            if len(table["_row"]) >= _MAX_CELLS_PER_ROW:
                break
            table["_row"].append((text, is_header))
            if rowspan > 1:
                table["_pending_rowspans"][table["_col_cursor"]] = [text, is_header, rowspan - 1]
            table["_col_cursor"] += 1
            # Skip over any columns already claimed by earlier rowspans.
            self._fill_pending_rowspans(table)

        table["_cell_parts"] = None
        table["_cell_is_header"] = False
        table["_cell_colspan"] = 1
        table["_cell_rowspan"] = 1

    def _close_row(self, table: Dict[str, Any]) -> None:
        if table["_row"] is None:
            return
        # Flush trailing rowspan carry-overs for this row.
        self._fill_pending_rowspans(table)
        if table["_row"] and len(table["rows"]) < _MAX_ROWS_PER_TABLE:
            table["rows"].append(table["_row"])
        table["_row"] = None
        table["_col_cursor"] = 0

    @staticmethod
    def _clean_text(text: str) -> str:
        text = _REFERENCE_MARKER_RE.sub("", text)
        text = re.sub(r"\s+", " ", text).strip()
        if len(text) > _MAX_CELL_CHARS:
            text = text[:_MAX_CELL_CHARS] + "..."
        return text

    def _finalize_table(self, table: Dict[str, Any]) -> Dict[str, Any]:
        # A cell/row may still be open if the HTML omitted closing tags.
        if table["_cell_parts"] is not None:
            self._close_cell(table)
        if table["_row"] is not None:
            self._close_row(table)
        return {
            "class": table["class"],
            "caption": self._clean_text(table["caption"]),
            "section": table.get("section", ""),
            "rows": table["rows"],
        }


class WikipediaClient:
    """Client for interacting with the Wikipedia API."""

    # Language variant mappings - maps variant codes to their base language
    LANGUAGE_VARIANTS = {
        "zh-hans": "zh",  # Simplified Chinese
        "zh-hant": "zh",  # Traditional Chinese
        "zh-tw": "zh",  # Traditional Chinese (Taiwan)
        "zh-hk": "zh",  # Traditional Chinese (Hong Kong)
        "zh-mo": "zh",  # Traditional Chinese (Macau)
        "zh-cn": "zh",  # Simplified Chinese (China)
        "zh-sg": "zh",  # Simplified Chinese (Singapore)
        "zh-my": "zh",  # Simplified Chinese (Malaysia)
        # Serbian variants
        "sr-latn": "sr",  # Serbian Latin
        "sr-cyrl": "sr",  # Serbian Cyrillic
        # Norwegian variants
        "no": "nb",  # Norwegian Bokmål (default)
        # Kurdish variants
        "ku-latn": "ku",  # Kurdish Latin
        "ku-arab": "ku",  # Kurdish Arabic
    }

    # Country/locale to language code mappings (partial list)
    COUNTRY_TO_LANGUAGE = {
        # English-speaking countries
        "US": "en",
        "USA": "en",
        "United States": "en",
        "UK": "en",
        "GB": "en",
        "United Kingdom": "en",
        "CA": "en",
        "Canada": "en",
        "AU": "en",
        "Australia": "en",
        "NZ": "en",
        "New Zealand": "en",
        "IE": "en",
        "Ireland": "en",
        "ZA": "en",
        "South Africa": "en",
        # Chinese-speaking countries/regions
        "CN": "zh-hans",
        "China": "zh-hans",
        "TW": "zh-tw",
        "Taiwan": "zh-tw",
        "HK": "zh-hk",
        "Hong Kong": "zh-hk",
        "MO": "zh-mo",
        "Macau": "zh-mo",
        "SG": "zh-sg",
        "Singapore": "zh-sg",
        "MY": "zh-my",
        "Malaysia": "zh-my",
        # Major European countries
        "DE": "de",
        "Germany": "de",
        "FR": "fr",
        "France": "fr",
        "ES": "es",
        "Spain": "es",
        "IT": "it",
        "Italy": "it",
        "PT": "pt",
        "Portugal": "pt",
        "NL": "nl",
        "Netherlands": "nl",
        "PL": "pl",
        "Poland": "pl",
        "RU": "ru",
        "Russia": "ru",
        "UA": "uk",
        "Ukraine": "uk",
        "TR": "tr",
        "Turkey": "tr",
        "GR": "el",
        "Greece": "el",
        "SE": "sv",
        "Sweden": "sv",
        "NO": "no",
        "Norway": "no",
        "DK": "da",
        "Denmark": "da",
        "FI": "fi",
        "Finland": "fi",
        "IS": "is",
        "Iceland": "is",
        "CZ": "cs",
        "Czech Republic": "cs",
        "SK": "sk",
        "Slovakia": "sk",
        "HU": "hu",
        "Hungary": "hu",
        "RO": "ro",
        "Romania": "ro",
        "BG": "bg",
        "Bulgaria": "bg",
        "HR": "hr",
        "Croatia": "hr",
        "SI": "sl",
        "Slovenia": "sl",
        "RS": "sr",
        "Serbia": "sr",
        "BA": "bs",
        "Bosnia and Herzegovina": "bs",
        "MK": "mk",
        "Macedonia": "mk",
        "AL": "sq",
        "Albania": "sq",
        "MT": "mt",
        "Malta": "mt",
        # Asian countries
        "JP": "ja",
        "Japan": "ja",
        "KR": "ko",
        "South Korea": "ko",
        "IN": "hi",
        "India": "hi",
        "TH": "th",
        "Thailand": "th",
        "VN": "vi",
        "Vietnam": "vi",
        "ID": "id",
        "Indonesia": "id",
        "PH": "tl",
        "Philippines": "tl",
        "BD": "bn",
        "Bangladesh": "bn",
        "PK": "ur",
        "Pakistan": "ur",
        "LK": "si",
        "Sri Lanka": "si",
        "MM": "my",
        "Myanmar": "my",
        "KH": "km",
        "Cambodia": "km",
        "LA": "lo",
        "Laos": "lo",
        "MN": "mn",
        "Mongolia": "mn",
        "KZ": "kk",
        "Kazakhstan": "kk",
        "UZ": "uz",
        "Uzbekistan": "uz",
        "AF": "fa",
        "Afghanistan": "fa",
        # Middle Eastern countries
        "IR": "fa",
        "Iran": "fa",
        "SA": "ar",
        "Saudi Arabia": "ar",
        "AE": "ar",
        "UAE": "ar",
        "EG": "ar",
        "Egypt": "ar",
        "IQ": "ar",
        "Iraq": "ar",
        "SY": "ar",
        "Syria": "ar",
        "JO": "ar",
        "Jordan": "ar",
        "LB": "ar",
        "Lebanon": "ar",
        "IL": "he",
        "Israel": "he",
        # African countries
        "MA": "ar",
        "Morocco": "ar",
        "DZ": "ar",
        "Algeria": "ar",
        "TN": "ar",
        "Tunisia": "ar",
        "LY": "ar",
        "Libya": "ar",
        "SD": "ar",
        "Sudan": "ar",
        "ET": "am",
        "Ethiopia": "am",
        "KE": "sw",
        "Kenya": "sw",
        "TZ": "sw",
        "Tanzania": "sw",
        "NG": "ha",
        "Nigeria": "ha",
        "GH": "en",
        "Ghana": "en",
        # Latin American countries
        "MX": "es",
        "Mexico": "es",
        "AR": "es",
        "Argentina": "es",
        "CO": "es",
        "Colombia": "es",
        "VE": "es",
        "Venezuela": "es",
        "PE": "es",
        "Peru": "es",
        "CL": "es",
        "Chile": "es",
        "EC": "es",
        "Ecuador": "es",
        "BO": "es",
        "Bolivia": "es",
        "PY": "es",
        "Paraguay": "es",
        "UY": "es",
        "Uruguay": "es",
        "CR": "es",
        "Costa Rica": "es",
        "PA": "es",
        "Panama": "es",
        "GT": "es",
        "Guatemala": "es",
        "HN": "es",
        "Honduras": "es",
        "SV": "es",
        "El Salvador": "es",
        "NI": "es",
        "Nicaragua": "es",
        "CU": "es",
        "Cuba": "es",
        "DO": "es",
        "Dominican Republic": "es",
        "BR": "pt",
        "Brazil": "pt",
        # Additional countries (partial)
        "BY": "be",
        "Belarus": "be",
        "EE": "et",
        "Estonia": "et",
        "LV": "lv",
        "Latvia": "lv",
        "LT": "lt",
        "Lithuania": "lt",
        "GE": "ka",
        "Georgia": "ka",
        "AM": "hy",
        "Armenia": "hy",
        "AZ": "az",
        "Azerbaijan": "az",
    }

    def __init__(
        self,
        language: str = "en",
        country: Optional[str] = None,
        enable_cache: bool = False,
        access_token: Optional[str] = None,
    ):
        """
        Initialize the Wikipedia client.

        Args:
            language: The language code for Wikipedia (default: "en" for English).
                      Supports language variants like 'zh-hans', 'zh-tw', etc.
            country: The country/locale code (e.g., 'US', 'CN', 'TW').
                     If provided, overrides language parameter.
            enable_cache: Whether to enable caching for API calls (default: False).
            access_token: Personal Access Token for Wikipedia API authentication (optional).
                          Used to increase rate limits and avoid 403 errors.
        """
        # Resolve country to language if country is provided
        if country:
            resolved_language = self._resolve_country_to_language(country)
            self.original_input = country
            self.input_type = "country"
            self.resolved_language = resolved_language
            # Maintain backward compatibility
            self.original_language = resolved_language
        else:
            self.original_input = language
            self.input_type = "language"
            self.resolved_language = language
            # Maintain backward compatibility
            self.original_language = language

        self.enable_cache = enable_cache
        self.access_token = access_token
        self.user_agent = f"WikipediaMCPServer/{__version__} (https://github.com/rudra-ravi/wikipedia-mcp)"

        # Parse language and variant
        self.base_language, self.language_variant = self._parse_language_variant(self.resolved_language)

        # Use base language for API and library initialization
        self.wiki = wikipediaapi.Wikipedia(
            user_agent=self.user_agent,
            language=self.base_language,
            extract_format=wikipediaapi.ExtractFormat.WIKI,
        )
        self.api_url = f"https://{self.base_language}.wikipedia.org/w/api.php"

        if self.enable_cache:
            # Wrap methods with lru_cache to enable caching when requested
            self.search = functools.lru_cache(maxsize=128)(self.search)  # type: ignore[method-assign]
            self.get_article = functools.lru_cache(maxsize=128)(self.get_article)  # type: ignore[method-assign]
            self.get_summary = functools.lru_cache(maxsize=128)(self.get_summary)  # type: ignore[method-assign]
            self.get_sections = functools.lru_cache(maxsize=128)(self.get_sections)  # type: ignore[method-assign]
            self.get_links = functools.lru_cache(maxsize=128)(self.get_links)  # type: ignore[method-assign]
            self.get_related_topics = functools.lru_cache(maxsize=128)(  # type: ignore[method-assign]
                self.get_related_topics
            )
            self.summarize_for_query = functools.lru_cache(maxsize=128)(  # type: ignore[method-assign]
                self.summarize_for_query
            )
            self.summarize_section = functools.lru_cache(maxsize=128)(  # type: ignore[method-assign]
                self.summarize_section
            )
            self.extract_facts = functools.lru_cache(maxsize=128)(self.extract_facts)  # type: ignore[method-assign]
            self.get_coordinates = functools.lru_cache(maxsize=128)(self.get_coordinates)  # type: ignore[method-assign]
            self.get_tables = functools.lru_cache(maxsize=128)(self.get_tables)  # type: ignore[method-assign]
            self.list_tables = functools.lru_cache(maxsize=128)(self.list_tables)  # type: ignore[method-assign]
            self.get_table = functools.lru_cache(maxsize=128)(self.get_table)  # type: ignore[method-assign]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _resolve_country_to_language(self, country: str) -> str:
        """
        Resolve country/locale code to language code.

        Args:
            country: The country/locale code (e.g., 'US', 'CN', 'Taiwan').

        Returns:
            The corresponding language code.

        Raises:
            ValueError: If the country code is not supported.
        """
        # Normalize country code (upper case, handle common variations)
        country_upper = country.upper().strip()
        country_title = country.title().strip()

        # Try exact matches first
        if country_upper in self.COUNTRY_TO_LANGUAGE:
            return self.COUNTRY_TO_LANGUAGE[country_upper]

        # Try title case
        if country_title in self.COUNTRY_TO_LANGUAGE:
            return self.COUNTRY_TO_LANGUAGE[country_title]

        # Try original case
        if country in self.COUNTRY_TO_LANGUAGE:
            return self.COUNTRY_TO_LANGUAGE[country]

        # Provide helpful error message with suggestions
        available_countries = list(self.COUNTRY_TO_LANGUAGE.keys())
        # Get first 10 country codes for suggestions
        country_codes = [c for c in available_countries if len(c) <= 3][:10]

        raise ValueError(
            f"Unsupported country/locale: '{country}'. "
            f"Supported country codes include: {', '.join(country_codes)}. "
            f"Use --language parameter for direct language codes instead."
        )

    def _parse_language_variant(self, language: str) -> tuple[str, Optional[str]]:
        """
        Parse language code and extract base language and variant.

        Args:
            language: The language code, possibly with variant (e.g., 'zh-hans', 'zh-tw').

        Returns:
            A tuple of (base_language, variant) where variant is None if not a variant.
        """
        if language in self.LANGUAGE_VARIANTS:
            base_language = self.LANGUAGE_VARIANTS[language]
            return base_language, language
        else:
            return language, None

    def _get_request_headers(self) -> Dict[str, str]:
        """
        Get request headers for API calls, including authentication if available.

        Returns:
            Dictionary of headers to use for requests.
        """
        headers = {"User-Agent": self.user_agent}
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        return headers

    def _add_variant_to_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add language variant parameter to API request parameters if needed.

        Args:
            params: The API request parameters.

        Returns:
            Updated parameters with variant if applicable.
        """
        if self.language_variant:
            params = params.copy()
            params["variant"] = self.language_variant
        return params

    def _request_json(
        self,
        *,
        url: str,
        params: Dict[str, Any],
        timeout: int = 30,
        retries: int = 2,
        backoff_seconds: float = 0.5,
    ) -> tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
        """
        Perform a GET request with bounded retry and robust JSON parsing.

        Returns:
            Tuple of (data, error). Exactly one will be non-None.
        """
        last_error: Dict[str, Any] = {
            "message": "Request failed",
            "error_type": "UnknownError",
        }

        for attempt in range(retries + 1):
            try:
                response = requests.get(
                    url,
                    headers=self._get_request_headers(),
                    params=params,
                    timeout=timeout,
                )
            except requests.exceptions.Timeout as exc:
                last_error = {
                    "message": f"Request timed out: {exc}",
                    "error_type": "Timeout",
                }
            except requests.exceptions.ConnectionError as exc:
                last_error = {
                    "message": f"Connection error: {exc}",
                    "error_type": "ConnectionError",
                }
            except requests.exceptions.RequestException as exc:
                last_error = {
                    "message": f"Request exception: {exc}",
                    "error_type": type(exc).__name__,
                }
            else:
                status_code_raw = getattr(response, "status_code", 200)
                status_code = status_code_raw if isinstance(status_code_raw, int) else 200
                retryable_status = status_code in {429, 500, 502, 503, 504}
                if retryable_status and attempt < retries:
                    wait_seconds = backoff_seconds * (2**attempt)
                    logger.warning(
                        "Retryable HTTP status %s from Wikipedia API (attempt %s/%s); retrying in %.2fs",
                        status_code,
                        attempt + 1,
                        retries + 1,
                        wait_seconds,
                    )
                    time.sleep(wait_seconds)
                    continue

                try:
                    response.raise_for_status()
                except requests.exceptions.HTTPError as exc:
                    if retryable_status and attempt < retries:
                        wait_seconds = backoff_seconds * (2**attempt)
                        logger.warning(
                            "Retryable HTTP error from Wikipedia API (attempt %s/%s); retrying in %.2fs: %s",
                            attempt + 1,
                            retries + 1,
                            wait_seconds,
                            exc,
                        )
                        time.sleep(wait_seconds)
                        continue
                    preview = (response.text or "")[:200]
                    return None, {
                        "message": f"HTTP {status_code} from Wikipedia API: {exc}",
                        "error_type": "HTTPError",
                        "status_code": status_code,
                        "body_preview": preview,
                    }

                if status_code >= 400:
                    preview = (response.text or "")[:200]
                    return None, {
                        "message": f"HTTP {status_code} from Wikipedia API",
                        "error_type": "HTTPError",
                        "status_code": status_code,
                        "body_preview": preview,
                    }

                try:
                    return response.json(), None
                except ValueError as exc:
                    preview = (response.text or "")[:200]
                    return None, {
                        "message": f"Invalid JSON response from Wikipedia API: {exc}",
                        "error_type": "JSONDecodeError",
                        "status_code": status_code,
                        "body_preview": preview,
                    }

            if attempt < retries:
                wait_seconds = backoff_seconds * (2**attempt)
                logger.warning(
                    "Wikipedia API request failed (%s), retrying in %.2fs (attempt %s/%s)",
                    last_error.get("error_type", "UnknownError"),
                    wait_seconds,
                    attempt + 1,
                    retries + 1,
                )
                time.sleep(wait_seconds)

        return None, last_error

    # ------------------------------------------------------------------
    # Diagnostics
    # ------------------------------------------------------------------
    def test_connectivity(self) -> Dict[str, Any]:
        """
        Test connectivity to the Wikipedia API and return diagnostics.

        Returns:
            A dictionary with status, URL, language, site information, and response time.
            On failure, returns status 'failed' with error details.
        """
        test_url = f"https://{self.base_language}.wikipedia.org/w/api.php"
        test_params = {
            "action": "query",
            "format": "json",
            "meta": "siteinfo",
            "siprop": "general",
        }

        try:
            logger.info(f"Testing connectivity to {test_url}")
            data, error = self._request_json(
                url=test_url,
                params=test_params,
                timeout=10,
                retries=1,
            )
            if error:
                return {
                    "status": "failed",
                    "url": test_url,
                    "language": self.base_language,
                    "error": error.get("message", "Connectivity test failed"),
                    "error_type": error.get("error_type", "RequestError"),
                }

            site_info = (data or {}).get("query", {}).get("general", {})

            return {
                "status": "success",
                "url": test_url,
                "language": self.base_language,
                "site_name": site_info.get("sitename", "Unknown"),
                "server": site_info.get("server", "Unknown"),
                "response_time_ms": None,
            }

        except Exception as exc:  # pragma: no cover - safeguarded
            logger.error("Connectivity test failed: %s", exc)
            return {
                "status": "failed",
                "url": test_url,
                "language": self.base_language,
                "error": str(exc),
                "error_type": type(exc).__name__,
            }

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------
    def search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search Wikipedia for articles matching a query with validation and diagnostics.

        Args:
            query: The search query.
            limit: The maximum number of results to return.

        Returns:
            A list of dictionaries representing search results.
        """
        if not query or not query.strip():
            logger.warning("Empty search query provided")
            return []

        trimmed_query = query.strip()
        if len(trimmed_query) > 300:
            logger.warning(
                "Search query too long (%d chars), truncating to 300",
                len(trimmed_query),
            )
            trimmed_query = trimmed_query[:300]

        if limit <= 0:
            logger.warning("Invalid limit %d provided, using default 10", limit)
            limit = 10
        elif limit > 500:
            logger.warning("Limit %d exceeds maximum, capping at 500", limit)
            limit = 500

        params = {
            "action": "query",
            "format": "json",
            "list": "search",
            "utf8": 1,
            "srsearch": trimmed_query,
            "srlimit": limit,
        }

        params = self._add_variant_to_params(params)

        try:
            logger.debug("Making search request to %s with params %s", self.api_url, params)
            data, error = self._request_json(
                url=self.api_url,
                params=params,
                timeout=30,
                retries=2,
            )
            if error:
                logger.error(
                    "Search request failed for query '%s': %s",
                    trimmed_query,
                    error.get("message", "Request failed"),
                )
                return []

            if "error" in (data or {}):
                error_info = (data or {})["error"]
                logger.error(
                    "Wikipedia API error: %s - %s",
                    error_info.get("code", "unknown"),
                    error_info.get("info", "No details"),
                )
                return []

            if "warnings" in (data or {}):
                for warning_type, warning_body in (data or {})["warnings"].items():
                    logger.warning("Wikipedia API warning (%s): %s", warning_type, warning_body)

            query_data = (data or {}).get("query", {})
            search_results = query_data.get("search", [])
            logger.info(
                "Search for '%s' returned %d results",
                trimmed_query,
                len(search_results),
            )

            results: List[Dict[str, Any]] = []
            for item in search_results:
                title = item.get("title")
                if not title:
                    logger.warning("Search result missing title: %s", item)
                    continue

                results.append(
                    {
                        "title": title,
                        "snippet": item.get("snippet", ""),
                        "pageid": item.get("pageid", 0),
                        "wordcount": item.get("wordcount", 0),
                        "timestamp": item.get("timestamp", ""),
                    }
                )

            return results

        except requests.exceptions.Timeout as exc:
            logger.error("Search request timed out for query '%s': %s", trimmed_query, exc)
            return []
        except requests.exceptions.ConnectionError as exc:
            logger.error("Connection error when searching for '%s': %s", trimmed_query, exc)
            return []
        except requests.exceptions.HTTPError as exc:
            logger.error("HTTP error when searching for '%s': %s", trimmed_query, exc)
            return []
        except requests.exceptions.RequestException as exc:
            logger.error("Request error when searching for '%s': %s", trimmed_query, exc)
            return []
        except ValueError as exc:
            logger.error("JSON decode error when searching for '%s': %s", trimmed_query, exc)
            return []
        except Exception as exc:  # pragma: no cover - unexpected safeguard
            logger.error("Unexpected error searching Wikipedia for '%s': %s", trimmed_query, exc)
            return []

    # ------------------------------------------------------------------
    # Article retrieval
    # ------------------------------------------------------------------
    def get_article(self, title: str) -> Dict[str, Any]:
        """
        Get the full content of a Wikipedia article.

        Args:
            title: The title of the Wikipedia article.

        Returns:
            A dictionary containing the article information.
        """
        try:
            page = self.wiki.page(title)

            if not page.exists():
                return {"title": title, "exists": False, "error": "Page does not exist"}

            # Get sections
            sections = self._extract_sections(page.sections)

            # Get categories
            categories = [cat for cat in page.categories.keys()]

            # Get links
            links = [link for link in page.links.keys()]

            return {
                "title": page.title,
                "pageid": page.pageid,
                "summary": page.summary,
                "text": page.text,
                "url": page.fullurl,
                "sections": sections,
                "categories": categories,
                "links": links[:100],  # Limit to 100 links to avoid too much data
                "exists": True,
            }
        except Exception as e:
            logger.error(f"Error getting Wikipedia article: {e}")
            return {"title": title, "exists": False, "error": str(e)}

    # ------------------------------------------------------------------
    # Summaries
    # ------------------------------------------------------------------
    def get_summary(self, title: str) -> str:
        """
        Get a summary of a Wikipedia article.

        Args:
            title: The title of the Wikipedia article.

        Returns:
            The article summary.
        """
        try:
            page = self.wiki.page(title)

            if not page.exists():
                return f"No Wikipedia article found for '{title}'."

            return page.summary
        except Exception as e:
            logger.error(f"Error getting Wikipedia summary: {e}")
            return f"Error retrieving summary for '{title}': {str(e)}"

    def get_sections(self, title: str) -> List[Dict[str, Any]]:
        """
        Get the sections of a Wikipedia article.

        Args:
            title: The title of the Wikipedia article.

        Returns:
            A list of sections.
        """
        try:
            page = self.wiki.page(title)

            if not page.exists():
                return []

            return self._extract_sections(page.sections)
        except Exception as e:
            logger.error(f"Error getting Wikipedia sections: {e}")
            return []

    def get_links(self, title: str) -> List[str]:
        """
        Get the links in a Wikipedia article.

        Args:
            title: The title of the Wikipedia article.

        Returns:
            A list of links.
        """
        try:
            page = self.wiki.page(title)

            if not page.exists():
                return []

            return [link for link in page.links.keys()]
        except Exception as e:
            logger.error(f"Error getting Wikipedia links: {e}")
            return []

    # ------------------------------------------------------------------
    # Related topics
    # ------------------------------------------------------------------
    def get_related_topics(self, title: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get topics related to a Wikipedia article based on links and categories.

        Args:
            title: The title of the Wikipedia article.
            limit: Maximum number of related topics to return.

        Returns:
            A list of related topics.
        """
        try:
            page = self.wiki.page(title)

            if not page.exists():
                return []

            # Get links from the page
            links = list(page.links.keys())

            # Get categories
            categories = list(page.categories.keys())

            related = []

            # Add links first
            for link in links[:limit]:
                link_page = self.wiki.page(link)
                if link_page.exists():
                    related.append(
                        {
                            "title": link,
                            "summary": (
                                link_page.summary[:200] + "..." if len(link_page.summary) > 200 else link_page.summary
                            ),
                            "url": link_page.fullurl,
                            "type": "link",
                        }
                    )
                if len(related) >= limit:
                    break

            # Add categories if we still have room
            remaining = limit - len(related)
            if remaining > 0:
                for category in categories[:remaining]:
                    # Remove "Category:" prefix if present
                    clean_category = category.replace("Category:", "")
                    related.append({"title": clean_category, "type": "category"})

            return related
        except Exception as e:
            logger.error(f"Error getting related topics: {e}")
            return []

    # ------------------------------------------------------------------
    # Fact extraction
    # ------------------------------------------------------------------
    def _extract_sections(self, sections, level=0) -> List[Dict[str, Any]]:
        """
        Extract sections recursively.

        Args:
            sections: The sections to extract.
            level: The current section level.

        Returns:
            A list of sections.
        """
        result = []
        for section in sections:
            section_data = {
                "title": section.title,
                "level": level,
                "text": section.text,
                "sections": self._extract_sections(section.sections, level + 1),
            }
            result.append(section_data)
        return result

    def summarize_for_query(self, title: str, query: str, max_length: int = 250) -> str:
        """
        Get a summary of a Wikipedia article tailored to a specific query.

        This is a simplified implementation that returns a snippet around the query.

        Args:
            title: The title of the Wikipedia article.
            query: The query to focus the summary on.
            max_length: The maximum length of the summary.

        Returns:
            A query-focused summary.
        """
        try:
            page = self.wiki.page(title)
            if not page.exists():
                return f"No Wikipedia article found for '{title}'."

            text_content = page.text
            query_lower = query.lower()
            text_lower = text_content.lower()

            start_index = text_lower.find(query_lower)
            if start_index == -1:
                # If query not found, return the beginning of the summary or article text
                summary_part = page.summary[:max_length]
                if not summary_part:
                    summary_part = text_content[:max_length]
                return summary_part + "..." if len(summary_part) >= max_length else summary_part

            # Try to get context around the query
            context_start = max(0, start_index - (max_length // 2))
            context_end = min(len(text_content), start_index + len(query) + (max_length // 2))

            snippet = text_content[context_start:context_end]

            if len(snippet) > max_length:
                snippet = snippet[:max_length]

            return snippet + "..." if len(snippet) >= max_length or context_end < len(text_content) else snippet

        except Exception as e:
            logger.error(f"Error generating query-focused summary for '{title}': {e}")
            return f"Error generating query-focused summary for '{title}': {str(e)}"

    def summarize_section(self, title: str, section_title: str, max_length: int = 150) -> str:
        """
        Get a summary of a specific section of a Wikipedia article.

        Args:
            title: The title of the Wikipedia article.
            section_title: The title of the section to summarize.
            max_length: The maximum length of the summary.

        Returns:
            A summary of the specified section.
        """
        try:
            page = self.wiki.page(title)
            if not page.exists():
                return f"No Wikipedia article found for '{title}'."

            target_section = None

            # Helper function to find the section
            def find_section_recursive(sections_list, target_title):
                for sec in sections_list:
                    if sec.title.lower() == target_title.lower():
                        return sec
                    # Check subsections
                    found_in_subsection = find_section_recursive(sec.sections, target_title)
                    if found_in_subsection:
                        return found_in_subsection
                return None

            target_section = find_section_recursive(page.sections, section_title)

            if not target_section or not target_section.text:
                return f"Section '{section_title}' not found or is empty in article '{title}'."

            summary = target_section.text[:max_length]
            return summary + "..." if len(target_section.text) > max_length else summary

        except Exception as e:
            logger.error(f"Error summarizing section '{section_title}' for article '{title}': {e}")
            return f"Error summarizing section '{section_title}': {str(e)}"

    def extract_facts(
        self,
        title: str,
        topic_within_article: Optional[str] = None,
        count: int = 5,
    ) -> List[str]:
        """
        Extract key facts from a Wikipedia article.

        This is a simplified implementation returning the first few sentences
        of the summary or a relevant section if topic_within_article is provided.

        Args:
            title: The title of the Wikipedia article.
            topic_within_article: Optional topic/section to focus fact extraction.
            count: The number of facts to extract.

        Returns:
            A list of key facts (strings).
        """
        try:
            page = self.wiki.page(title)
            if not page.exists():
                return [f"No Wikipedia article found for '{title}'."]

            text_to_process = ""
            if topic_within_article:
                # Try to find the section text
                def find_section_text_recursive(sections_list, target_title):
                    for sec in sections_list:
                        if sec.title.lower() == target_title.lower():
                            return sec.text
                        found_in_subsection = find_section_text_recursive(sec.sections, target_title)
                        if found_in_subsection:
                            return found_in_subsection
                    return None

                section_text = find_section_text_recursive(page.sections, topic_within_article)
                if section_text:
                    text_to_process = section_text
                else:
                    # Fallback to summary if specific topic section not found
                    text_to_process = page.summary
            else:
                text_to_process = page.summary

            if not text_to_process:
                return ["No content found to extract facts from."]

            # Basic sentence splitting (can be improved with NLP libraries)
            sentences = [s.strip() for s in text_to_process.split(".") if s.strip()]

            facts: List[str] = []
            for sentence in sentences[:count]:
                if sentence:  # Ensure not an empty string after strip
                    facts.append(sentence + ".")  # Add back the period

            return facts if facts else ["Could not extract facts from the provided text."]

        except Exception as e:
            logger.error(f"Error extracting key facts for '{title}': {e}")
            return [f"Error extracting key facts for '{title}': {str(e)}"]

    # ------------------------------------------------------------------
    # Coordinates
    # ------------------------------------------------------------------
    def get_coordinates(self, title: str) -> Dict[str, Any]:
        """
        Get the coordinates of a Wikipedia article.

        Args:
            title: The title of the Wikipedia article.

        Returns:
            A dictionary containing the coordinates information.
        """
        params = {
            "action": "query",
            "format": "json",
            "prop": "coordinates",
            "titles": title,
        }
        # Add variant parameter if needed
        params = self._add_variant_to_params(params)

        try:
            data, error = self._request_json(
                url=self.api_url,
                params=params,
                timeout=30,
                retries=2,
            )
            if error:
                return {
                    "title": title,
                    "coordinates": None,
                    "exists": False,
                    "error": error.get("message", "Failed to fetch coordinates"),
                }

            pages = (data or {}).get("query", {}).get("pages", {})

            if not pages:
                return {
                    "title": title,
                    "coordinates": None,
                    "exists": False,
                    "error": "No page found",
                }

            # Get the first (and typically only) page
            page_data = next(iter(pages.values()))

            # Check if page exists (pageid > 0 means page exists)
            if page_data.get("pageid", -1) < 0:
                return {
                    "title": title,
                    "coordinates": None,
                    "exists": False,
                    "error": "Page does not exist",
                }

            coordinates = page_data.get("coordinates", [])

            if not coordinates:
                return {
                    "title": page_data.get("title", title),
                    "pageid": page_data.get("pageid"),
                    "coordinates": None,
                    "exists": True,
                    "error": None,
                    "message": "No coordinates available for this article",
                }

            # MediaWiki marker fields can be returned as an empty string.
            # Normalize to the public boolean schema before MCP validation.
            processed_coordinates = []
            for coord in coordinates:
                primary_marker = coord.get("primary")
                processed_coordinates.append(
                    {
                        "latitude": coord.get("lat"),
                        "longitude": coord.get("lon"),
                        "primary": primary_marker == "" or primary_marker is True,
                        "globe": coord.get("globe", "earth"),
                        "type": coord.get("type", ""),
                        "name": coord.get("name", ""),
                        "region": coord.get("region", ""),
                        "country": coord.get("country", ""),
                    }
                )

            return {
                "title": page_data.get("title", title),
                "pageid": page_data.get("pageid"),
                "coordinates": processed_coordinates,
                "exists": True,
                "error": None,
            }

        except Exception as e:
            logger.error(f"Error getting coordinates for Wikipedia article: {e}")
            return {
                "title": title,
                "coordinates": None,
                "exists": False,
                "error": str(e),
            }

    # ------------------------------------------------------------------
    # Tables
    # ------------------------------------------------------------------
    def get_tables(self, title: str, include_all_tables: bool = False) -> Dict[str, Any]:
        """
        Extract tabular data from a Wikipedia article.

        Fetches the rendered HTML of the article via the MediaWiki parse API and
        extracts tables into structured rows. By default only data tables
        (``class="wikitable"``) are returned; set ``include_all_tables`` to True
        to also return infoboxes, navboxes, and other tables.

        Args:
            title: The title of the Wikipedia article.
            include_all_tables: If True, return every table found; otherwise only
                tables whose class contains "wikitable".

        Returns:
            A dictionary with the article title, existence flag, and a list of
            tables. Each table has an ``index``, ``caption``, list of ``headers``
            (column headers extracted from header rows), and ``rows`` (data rows
            as lists of cell strings).
        """
        params = {
            "action": "parse",
            "format": "json",
            "page": title,
            "prop": "text",
            "redirects": 1,
            "formatversion": 2,
        }
        params = self._add_variant_to_params(params)

        try:
            data, error = self._request_json(
                url=self.api_url,
                params=params,
                timeout=30,
                retries=2,
            )
            if error:
                return {
                    "title": title,
                    "exists": False,
                    "tables": [],
                    "error": error.get("message", "Failed to fetch tables"),
                }

            data = data or {}
            if "error" in data:
                error_info = data["error"]
                message = error_info.get("info", "Page does not exist")
                # MediaWiki returns "missingtitle" when the page does not exist.
                exists = error_info.get("code") != "missingtitle"
                return {
                    "title": title,
                    "exists": exists,
                    "tables": [],
                    "error": message,
                }

            parse_result = data.get("parse", {})
            html_text = parse_result.get("text", "")
            # formatversion=1 nests the HTML under a "*" key.
            if isinstance(html_text, dict):
                html_text = html_text.get("*", "")

            if not html_text:
                return {
                    "title": parse_result.get("title", title),
                    "exists": True,
                    "tables": [],
                    "message": "No tables found in this article.",
                }

            parser = _WikiTableParser()
            parser.feed(html_text)

            tables: List[Dict[str, Any]] = []
            for raw_table in parser.tables:
                if len(tables) >= _MAX_TABLES:
                    break
                if not include_all_tables and "wikitable" not in (raw_table.get("class") or ""):
                    continue

                rows = raw_table.get("rows", [])
                if not rows:
                    continue

                headers, data_rows = self._split_table_rows(rows)
                tables.append(
                    {
                        "index": len(tables),
                        "caption": raw_table.get("caption", ""),
                        "section": raw_table.get("section", ""),
                        "headers": headers,
                        "rows": data_rows,
                    }
                )

            response: Dict[str, Any] = {
                "title": parse_result.get("title", title),
                "exists": True,
                "tables": tables,
            }
            if not tables:
                response["message"] = (
                    "No tables found in this article."
                    if include_all_tables
                    else "No data tables found. Try include_all_tables=true to include infoboxes and other tables."
                )
            return response

        except Exception as e:
            logger.error(f"Error getting tables for Wikipedia article '{title}': {e}")
            return {
                "title": title,
                "exists": False,
                "tables": [],
                "error": str(e),
            }

    @staticmethod
    def _split_table_rows(rows: List[List[tuple]]) -> tuple[List[str], List[List[str]]]:
        """Split parsed rows into a header list and data rows.

        The first row that contains any header cell is treated as the column
        headers; every other row is returned as a list of cell strings.
        """
        headers: List[str] = []
        data_rows: List[List[str]] = []
        header_taken = False

        for row in rows:
            is_header_row = bool(row) and all(is_header for _, is_header in row)
            if is_header_row and not header_taken:
                headers = [text for text, _ in row]
                header_taken = True
            else:
                data_rows.append([text for text, _ in row])

        return headers, data_rows

    @staticmethod
    def _table_column_count(headers: List[str], rows: List[List[str]]) -> int:
        """Return the widest column count across headers and data rows."""
        widest = len(headers)
        for row in rows:
            if len(row) > widest:
                widest = len(row)
        return widest

    @staticmethod
    def _resolve_column_index(column: str, headers: List[str], column_count: int) -> Optional[int]:
        """Resolve a column reference (numeric string or header name) to an index."""
        column = column.strip()
        if not column:
            return None

        # Numeric reference, e.g. "0", "3".
        if column.lstrip("-").isdigit():
            index = int(column)
            if 0 <= index < column_count:
                return index
            return None

        # Header name reference (case-insensitive).
        for idx, header in enumerate(headers):
            if header.strip().lower() == column.lower():
                return idx
        return None

    def list_tables(self, title: str, include_all_tables: bool = False) -> Dict[str, Any]:
        """
        List the tables in a Wikipedia article without their full contents.

        Returns lightweight metadata for each table (index, caption, the article
        section it appears under, headers, row count, and column count) so callers
        can decide which table to fetch in detail via :meth:`get_table`. The
        ``section`` is an empty string for tables in the lead/introduction.

        Args:
            title: The title of the Wikipedia article.
            include_all_tables: If True, include infoboxes/navboxes as well.

        Returns:
            A dictionary with the article title, existence flag, table count,
            and a list of per-table summaries.
        """
        data = self.get_tables(title, include_all_tables=include_all_tables)
        if not data.get("exists"):
            return {
                "title": data.get("title", title),
                "exists": False,
                "count": 0,
                "tables": [],
                "error": data.get("error"),
            }

        summaries = []
        for table in data.get("tables", []):
            headers = table.get("headers", [])
            rows = table.get("rows", [])
            summaries.append(
                {
                    "index": table.get("index"),
                    "caption": table.get("caption", ""),
                    "section": table.get("section", ""),
                    "headers": headers,
                    "row_count": len(rows),
                    "column_count": self._table_column_count(headers, rows),
                }
            )

        response: Dict[str, Any] = {
            "title": data.get("title", title),
            "exists": True,
            "count": len(summaries),
            "tables": summaries,
        }
        if not summaries:
            response["message"] = data.get("message", "No tables found in this article.")
        return response

    def get_table(
        self,
        title: str,
        table_index: int = 0,
        row: int = -1,
        column: str = "",
        include_all_tables: bool = False,
    ) -> Dict[str, Any]:
        """
        Fetch a single table, or a specific row/column/cell within it.

        Args:
            title: The title of the Wikipedia article.
            table_index: Which table to fetch (0-based; see :meth:`list_tables`).
            row: A 0-based data-row index. If >= 0, only that row is returned.
            column: A column reference — either a 0-based index (as a string,
                e.g. "2") or a header name (case-insensitive). If provided, only
                that column is returned.
            include_all_tables: If True, index into all tables including
                infoboxes/navboxes rather than just data tables.

        Returns:
            A dictionary containing the whole table, a single row, a single
            column, or a single cell depending on which of ``row``/``column``
            are supplied. On failure an ``error`` field is included.
        """
        data = self.get_tables(title, include_all_tables=include_all_tables)
        if not data.get("exists"):
            return {
                "title": data.get("title", title),
                "exists": False,
                "error": data.get("error", "Page does not exist"),
            }

        tables = data.get("tables", [])
        if not tables:
            return {
                "title": data.get("title", title),
                "exists": True,
                "error": data.get("message", "No tables found in this article."),
            }

        if table_index < 0 or table_index >= len(tables):
            return {
                "title": data.get("title", title),
                "exists": True,
                "error": f"Table index {table_index} out of range; article has {len(tables)} table(s).",
            }

        table = tables[table_index]
        headers = table.get("headers", [])
        rows = table.get("rows", [])
        column_count = self._table_column_count(headers, rows)
        resolved_title = data.get("title", title)

        # Resolve an optional column reference up front.
        column_index: Optional[int] = None
        if column and column.strip():
            column_index = self._resolve_column_index(column, headers, column_count)
            if column_index is None:
                return {
                    "title": resolved_title,
                    "exists": True,
                    "table_index": table_index,
                    "error": f"Column '{column}' not found in table {table_index}.",
                }

        row_index: Optional[int] = row if row >= 0 else None
        if row_index is not None and row_index >= len(rows):
            return {
                "title": resolved_title,
                "exists": True,
                "table_index": table_index,
                "error": f"Row index {row_index} out of range; table {table_index} has {len(rows)} row(s).",
            }

        header_name = headers[column_index] if column_index is not None and column_index < len(headers) else None

        def cell(r: List[str], idx: int) -> str:
            return r[idx] if 0 <= idx < len(r) else ""

        # Single cell: both row and column specified.
        if row_index is not None and column_index is not None:
            return {
                "title": resolved_title,
                "exists": True,
                "table_index": table_index,
                "row_index": row_index,
                "column_index": column_index,
                "header": header_name,
                "value": cell(rows[row_index], column_index),
            }

        # Single row.
        if row_index is not None:
            return {
                "title": resolved_title,
                "exists": True,
                "table_index": table_index,
                "row_index": row_index,
                "headers": headers,
                "row": rows[row_index],
            }

        # Single column.
        if column_index is not None:
            return {
                "title": resolved_title,
                "exists": True,
                "table_index": table_index,
                "column_index": column_index,
                "header": header_name,
                "values": [cell(r, column_index) for r in rows],
            }

        # Whole table.
        return {
            "title": resolved_title,
            "exists": True,
            "table_index": table_index,
            "caption": table.get("caption", ""),
            "section": table.get("section", ""),
            "headers": headers,
            "rows": rows,
            "row_count": len(rows),
            "column_count": column_count,
        }
