"""Data models for security alerts."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List


@dataclass
class AlertItem:
    """Represents a security alert item from any source."""

    id: str
    source: str
    category: str  # "cve" | "news"
    title: str
    summary: str
    url: str
    published_at: datetime
    severity: Optional[float] = None  # CVSS score for CVEs
    tags: Optional[List[str]] = None

    def __post_init__(self):
        """Ensure tags is a list."""
        if self.tags is None:
            self.tags = []

