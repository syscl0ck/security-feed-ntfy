"""Send notifications via ntfy."""

import requests
import logging
from typing import Optional, List

logger = logging.getLogger(__name__)


def send_ntfy(
    title: str,
    message: str,
    base_url: str,
    topic: str,
    url: Optional[str] = None,
    tags: Optional[List[str]] = None,
    priority: str = "default",
    headers: Optional[dict] = None,
) -> bool:
    """
    Send a notification via ntfy.

    Args:
        title: Notification title
        message: Notification message/body
        base_url: ntfy server base URL (e.g., "https://ntfy.sh")
        topic: ntfy topic name
        url: Optional URL to include in notification
        tags: Optional list of tags
        priority: Priority level (min, low, default, high, urgent)
        headers: Optional additional headers (e.g., for auth)

    Returns:
        True if successful, False otherwise
    """
    notify_url = f"{base_url.rstrip('/')}/{topic}"

    # Build headers
    notify_headers = {}
    if headers:
        notify_headers.update(headers)

    # Add priority
    if priority:
        notify_headers["X-Priority"] = priority

    # Add tags
    if tags:
        notify_headers["X-Tags"] = ",".join(tags)

    # Add click action if URL provided
    if url:
        notify_headers["X-Click"] = url

    # Build message body
    body = f"{title}\n\n{message}"
    if url:
        body += f"\n\n{url}"

    try:
        response = requests.post(notify_url, headers=notify_headers, data=body, timeout=10)
        response.raise_for_status()
        logger.info(f"Sent notification: {title[:50]}...")
        return True
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to send notification: {e}")
        return False

