"""RSS feed fetcher."""

import feedparser
import logging
from datetime import datetime
from typing import List
from dateutil import parser as date_parser

from ..models import AlertItem

logger = logging.getLogger(__name__)


def parse_date(date_str: str) -> datetime:
    """Parse a date string to datetime, handling various formats."""
    try:
        # Try parsing with dateutil first (handles most formats)
        parsed = date_parser.parse(date_str)
        return parsed
    except (ValueError, TypeError) as e:
        logger.warning(f"Failed to parse date '{date_str}': {e}, using current time")
        return datetime.utcnow()


def fetch_rss(url: str, source_name: str, category: str = "news") -> List[AlertItem]:
    """
    Fetch items from an RSS feed.

    Args:
        url: RSS feed URL
        source_name: Name of the feed source
        category: Category for items (default: "news")

    Returns:
        List of AlertItem objects
    """
    logger.debug(f"Fetching RSS feed: {source_name} from {url}")
    
    try:
        # Parse the RSS feed
        feed = feedparser.parse(url)
        
        if feed.bozo and feed.bozo_exception:
            logger.warning(f"RSS feed parsing warning for {source_name}: {feed.bozo_exception}")
        
        items = []
        
        # Check if feed has entries
        if not hasattr(feed, 'entries') or not feed.entries:
            logger.warning(f"No entries found in RSS feed: {source_name}")
            return items
        
        for entry in feed.entries:
            try:
                # Extract title
                title = entry.get('title', 'Untitled')
                
                # Extract summary/description
                summary = entry.get('summary', '')
                if not summary:
                    summary = entry.get('description', '')
                if not summary:
                    # Try to get content if available
                    if hasattr(entry, 'content') and entry.content:
                        summary = entry.content[0].get('value', '')
                
                # Extract URL
                item_url = entry.get('link', '')
                if not item_url:
                    # Try alternate link fields
                    item_url = entry.get('id', '')
                
                # Extract published date
                published_str = entry.get('published', '')
                if not published_str:
                    published_str = entry.get('updated', '')
                if not published_str:
                    published_str = entry.get('pubDate', '')
                
                published_at = parse_date(published_str) if published_str else datetime.utcnow()
                
                # Generate a stable ID (will be regenerated in main.py, but useful here)
                import hashlib
                id_key = f"{source_name}:{item_url}:{title}:{published_at.isoformat()}"
                item_id = hashlib.sha256(id_key.encode()).hexdigest()
                
                # Create AlertItem
                item = AlertItem(
                    id=item_id,
                    source=source_name,
                    category=category,
                    title=title.strip(),
                    summary=summary.strip() if summary else "",
                    url=item_url,
                    published_at=published_at,
                    severity=None,  # RSS feeds don't have CVSS scores
                    tags=[],
                )
                
                items.append(item)
                
            except Exception as e:
                logger.error(f"Error processing RSS entry from {source_name}: {e}")
                continue
        
        logger.info(f"Successfully parsed {len(items)} items from {source_name}")
        return items
        
    except Exception as e:
        logger.error(f"Error fetching RSS feed {source_name} from {url}: {e}")
        raise

