"""
Wikipedia API client implementation.
"""

import logging
import wikipediaapi
import requests
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

class WikipediaClient:
    """Client for interacting with the Wikipedia API."""

    def __init__(self, language: str = "en"):
        """Initialize the Wikipedia client.
        
        Args:
            language: The language code for Wikipedia (default: "en" for English).
        """
        self.language = language
        self.user_agent = "WikipediaMCPServer/0.1.0 (https://github.com/rudra-ravi/wikipedia-mcp.git)"
        self.wiki = wikipediaapi.Wikipedia(
            user_agent=self.user_agent,
            language=language,
            extract_format=wikipediaapi.ExtractFormat.WIKI
        )
        self.api_url = f"https://{language}.wikipedia.org/w/api.php"

    def search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search Wikipedia for articles matching a query.
        
        Args:
            query: The search query.
            limit: Maximum number of results to return.
            
        Returns:
            A list of search results.
        """
        params = {
            'action': 'query',
            'format': 'json',
            'list': 'search',
            'utf8': 1,
            'srsearch': query,
            'srlimit': limit
        }
        
        try:
            response = requests.get(self.api_url, params=params)
            response.raise_for_status()
            data = response.json()
            
            results = []
            for item in data.get('query', {}).get('search', []):
                results.append({
                    'title': item.get('title', ''),
                    'snippet': item.get('snippet', ''),
                    'pageid': item.get('pageid', 0),
                    'wordcount': item.get('wordcount', 0),
                    'timestamp': item.get('timestamp', '')
                })
            
            return results
        except Exception as e:
            logger.error(f"Error searching Wikipedia: {e}")
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
                return {
                    'title': title,
                    'exists': False,
                    'error': 'Page does not exist'
                }
            
            # Get sections
            sections = self._extract_sections(page.sections)
            
            # Get categories
            categories = [cat for cat in page.categories.keys()]
            
            # Get links
            links = [link for link in page.links.keys()]
            
            return {
                'title': page.title,
                'pageid': page.pageid,
                'summary': page.summary,
                'text': page.text,
                'url': page.fullurl,
                'sections': sections,
                'categories': categories,
                'links': links[:100],  # Limit to 100 links to avoid too much data
                'exists': True
            }
        except Exception as e:
            logger.error(f"Error getting Wikipedia article: {e}")
            return {
                'title': title,
                'exists': False,
                'error': str(e)
            }

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
                    related.append({
                        'title': link,
                        'summary': link_page.summary[:200] + '...' if len(link_page.summary) > 200 else link_page.summary,
                        'url': link_page.fullurl,
                        'type': 'link'
                    })
                
                if len(related) >= limit:
                    break
            
            # Add categories if we still have room
            remaining = limit - len(related)
            if remaining > 0:
                for category in categories[:remaining]:
                    # Remove "Category:" prefix if present
                    clean_category = category.replace("Category:", "")
                    related.append({
                        'title': clean_category,
                        'type': 'category'
                    })
            
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
                'title': section.title,
                'level': level,
                'text': section.text,
                'sections': self._extract_sections(section.sections, level + 1)
            }
            result.append(section_data)
        
        return result 
