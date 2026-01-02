"""Scoring and filtering logic for alerts."""

import logging
from typing import List, Optional, Tuple
from .models import AlertItem

logger = logging.getLogger(__name__)


def should_alert(
    item: AlertItem,
    keywords: List[str],
    deny_keywords: List[str],
    min_cvss: float,
    kev_always_alert: bool = True,
) -> Tuple[bool, str]:
    """
    Determine if an item should trigger an alert.

    Returns:
        Tuple of (should_alert: bool, reason: str)
    """
    # Check deny keywords first
    text_to_check = f"{item.title} {item.summary}".lower()
    for deny_kw in deny_keywords:
        if deny_kw.lower() in text_to_check:
            return False, f"Matched deny keyword: {deny_kw}"

    # KEV items always alert if enabled
    if kev_always_alert and item.source.lower() == "kev":
        return True, "KEV item (always alert)"

    # Check CVSS threshold for CVEs
    if item.category == "cve" and item.severity is not None:
        if item.severity >= min_cvss:
            return True, f"CVSS {item.severity} >= {min_cvss}"

    # Check for urgent keywords
    urgent_keywords = ["rce", "auth bypass", "exploited", "wormable", "mass scanning"]
    text_lower = text_to_check
    for urgent_kw in urgent_keywords:
        if urgent_kw.lower() in text_lower:
            # Also check if it matches any user keywords
            for kw in keywords:
                if kw.lower() in text_lower:
                    return True, f"Urgent keyword match: {urgent_kw} + {kw}"

    # Check for regular keyword matches
    for kw in keywords:
        if kw.lower() in text_lower:
            return True, f"Keyword match: {kw}"

    return False, "No matching criteria"


def should_digest(
    item: AlertItem,
    keywords: List[str],
    deny_keywords: List[str],
    min_cvss: float,
) -> bool:
    """Determine if an item should be included in digest mode."""
    # Check deny keywords
    text_to_check = f"{item.title} {item.summary}".lower()
    for deny_kw in deny_keywords:
        if deny_kw.lower() in text_to_check:
            return False

    # Include if keyword matches but doesn't meet alert threshold
    if item.category == "cve" and item.severity is not None:
        if item.severity < min_cvss:
            # Check if it matches keywords
            for kw in keywords:
                if kw.lower() in text_to_check:
                    return True
            return False

    # Include news items that match keywords
    if item.category == "news":
        for kw in keywords:
            if kw.lower() in text_to_check:
                return True

    return False

