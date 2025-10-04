"""
Wikipedia API client implementation.
"""

import logging
import wikipediaapi
import requests
from typing import Dict, List, Optional, Any
import functools
from wikipedia_mcp import __version__


logger = logging.getLogger(__name__)


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
        # Add more language variants as needed
        # Serbian variants
        "sr-latn": "sr",  # Serbian Latin
        "sr-cyrl": "sr",  # Serbian Cyrillic
        # Norwegian variants
        "no": "nb",  # Norwegian Bokmål (default)
        # Kurdish variants
        "ku-latn": "ku",  # Kurdish Latin
        "ku-arab": "ku",  # Kurdish Arabic
    }

    # Country/locale to language code mappings
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
        # Additional countries
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
        """Initialize the Wikipedia client.

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
            self.search = functools.lru_cache(maxsize=128)(self.search)
            self.get_article = functools.lru_cache(maxsize=128)(self.get_article)
            self.get_summary = functools.lru_cache(maxsize=128)(self.get_summary)
            self.get_sections = functools.lru_cache(maxsize=128)(self.get_sections)
            self.get_links = functools.lru_cache(maxsize=128)(self.get_links)
            self.get_related_topics = functools.lru_cache(maxsize=128)(self.get_related_topics)
            self.summarize_for_query = functools.lru_cache(maxsize=128)(self.summarize_for_query)
            self.summarize_section = functools.lru_cache(maxsize=128)(self.summarize_section)
            self.extract_facts = functools.lru_cache(maxsize=128)(self.extract_facts)
            self.get_coordinates = functools.lru_cache(maxsize=128)(self.get_coordinates)

    def _resolve_country_to_language(self, country: str) -> str:
        """Resolve country/locale code to language code.

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
        """Parse language code and extract base language and variant.

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
        """Get request headers for API calls, including authentication if available.

        Returns:
            Dictionary of headers to use for requests.
        """
        headers = {"User-Agent": self.user_agent}

        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"

        return headers

    def _add_variant_to_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Add language variant parameter to API request parameters if needed.

        Args:
            params: The API request parameters.

        Returns:
            Updated parameters with variant if applicable.
        """
        if self.language_variant:
            params = params.copy()
            params["variant"] = self.language_variant
        return params

    def test_connectivity(self) -> Dict[str, Any]:
        """Test connectivity to the Wikipedia API and return diagnostics."""
        test_url = f"https://{self.base_language}.wikipedia.org/w/api.php"
        test_params = {
            "action": "query",
            "format": "json",
            "meta": "siteinfo",
            "siprop": "general",
        }

        try:
            logger.info(f"Testing connectivity to {test_url}")
            response = requests.get(
                test_url,
                headers=self._get_request_headers(),
                params=test_params,
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()

            site_info = data.get("query", {}).get("general", {})

            return {
                "status": "success",
                "url": test_url,
                "language": self.base_language,
                "site_name": site_info.get("sitename", "Unknown"),
                "server": site_info.get("server", "Unknown"),
                "response_time_ms": response.elapsed.total_seconds() * 1000,
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

    def search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search Wikipedia for articles matching a query with validation and diagnostics."""
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
            response = requests.get(
                self.api_url,
                headers=self._get_request_headers(),
                params=params,
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()

            if "error" in data:
                error_info = data["error"]
                logger.error(
                    "Wikipedia API error: %s - %s",
                    error_info.get("code", "unknown"),
                    error_info.get("info", "No details"),
                )
                return []

            if "warnings" in data:
                for warning_type, warning_body in data["warnings"].items():
                    logger.warning("Wikipedia API warning (%s): %s", warning_type, warning_body)

            query_data = data.get("query", {})
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

    def get_article(self, title: str) -> Dict[str, Any]:
        """Get the full content of a Wikipedia article.

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

    def get_summary(self, title: str) -> str:
        """Get a summary of a Wikipedia article.

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
        """Get the sections of a Wikipedia article.

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
        """Get the links in a Wikipedia article.

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

    def get_related_topics(self, title: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get topics related to a Wikipedia article based on links and categories.

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

            # Combine and limit
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

    def _extract_sections(self, sections, level=0) -> List[Dict[str, Any]]:
        """Extract sections recursively.

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

    def extract_facts(self, title: str, topic_within_article: Optional[str] = None, count: int = 5) -> List[str]:
        """
        Extract key facts from a Wikipedia article.
        This is a simplified implementation returning the first few sentences of the summary
        or a relevant section if topic_within_article is provided.

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

            # Basic sentence splitting (can be improved with NLP libraries like nltk or spacy)
            sentences = [s.strip() for s in text_to_process.split(".") if s.strip()]

            facts = []
            for sentence in sentences[:count]:
                if sentence:  # Ensure not an empty string after strip
                    facts.append(sentence + ".")  # Add back the period

            return facts if facts else ["Could not extract facts from the provided text."]

        except Exception as e:
            logger.error(f"Error extracting key facts for '{title}': {e}")
            return [f"Error extracting key facts for '{title}': {str(e)}"]

    def get_coordinates(self, title: str) -> Dict[str, Any]:
        """Get the coordinates of a Wikipedia article.

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
            response = requests.get(self.api_url, headers=self._get_request_headers(), params=params)
            response.raise_for_status()
            data = response.json()

            pages = data.get("query", {}).get("pages", {})

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

            # Process coordinates - typically there's one primary coordinate
            processed_coordinates = []
            for coord in coordinates:
                processed_coordinates.append(
                    {
                        "latitude": coord.get("lat"),
                        "longitude": coord.get("lon"),
                        "primary": coord.get("primary", False),
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
