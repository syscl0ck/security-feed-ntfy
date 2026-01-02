#!/usr/bin/env python3
"""Main entry point for security feed aggregator."""

import argparse
import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Optional
import yaml

from .models import AlertItem
from .storage import Storage
from .notify import send_ntfy
from .scoring import should_alert, should_digest

# Import fetchers (will be created later)
try:
    from .fetchers import rss
except ImportError:
    rss = None

try:
    from .fetchers import kev
except ImportError:
    kev = None

try:
    from .fetchers import nvd
except ImportError:
    nvd = None


def setup_logging(verbose: bool = False, log_file: Optional[str] = None):
    """Configure logging."""
    level = logging.DEBUG if verbose else logging.INFO
    handlers = [logging.StreamHandler(sys.stdout)]
    
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(log_file))
    
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=handlers,
    )


def load_config(config_path: str) -> dict:
    """Load configuration from YAML file."""
    config_file = Path(config_path)
    if not config_file.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    
    with open(config_file, "r") as f:
        config = yaml.safe_load(f)
    
    return config


def fetch_rss_feeds(feed_configs: List[dict]) -> List[AlertItem]:
    """Fetch items from RSS feeds."""
    items = []
    
    if rss is None:
        logging.warning("RSS fetcher not available")
        return items
    
    for feed_config in feed_configs:
        name = feed_config.get("name", "Unknown")
        url = feed_config.get("url")
        category = feed_config.get("category", "news")
        
        if not url:
            logging.warning(f"Skipping RSS feed {name}: no URL")
            continue
        
        try:
            feed_items = rss.fetch_rss(url, name, category)
            items.extend(feed_items)
            logging.info(f"Fetched {len(feed_items)} items from {name}")
        except Exception as e:
            logging.error(f"Error fetching RSS feed {name}: {e}")
    
    return items


def fetch_kev_feeds(enabled: bool) -> List[AlertItem]:
    """Fetch items from CISA KEV feed."""
    if not enabled:
        return []
    
    if kev is None:
        logging.warning("KEV fetcher not available")
        return []
    
    try:
        items = kev.fetch_kev()
        logging.info(f"Fetched {len(items)} items from KEV")
        return items
    except Exception as e:
        logging.error(f"Error fetching KEV feed: {e}")
        return []


def fetch_nvd_feeds(nvd_config: dict) -> List[AlertItem]:
    """Fetch items from NVD feed."""
    if not nvd_config.get("enabled", False):
        return []
    
    if nvd is None:
        logging.warning("NVD fetcher not available")
        return []
    
    try:
        mode = nvd_config.get("mode", "api_recent")
        results_per_run = nvd_config.get("results_per_run", 200)
        api_key = nvd_config.get("api_key", "")
        
        items = nvd.fetch_nvd(mode=mode, results_per_run=results_per_run, api_key=api_key)
        logging.info(f"Fetched {len(items)} items from NVD")
        return items
    except Exception as e:
        logging.error(f"Error fetching NVD feed: {e}")
        return []


def generate_item_id(item: AlertItem) -> str:
    """Generate a stable ID for an alert item."""
    import hashlib
    key = f"{item.source}:{item.url}:{item.title}:{item.published_at.isoformat()}"
    return hashlib.sha256(key.encode()).hexdigest()


def run_once(config: dict, dry_run: bool = False, mode_override: Optional[str] = None):
    """Run one cycle of fetching, filtering, and notification."""
    logger = logging.getLogger(__name__)
    start_time = datetime.utcnow()
    
    logger.info("=" * 60)
    logger.info("Starting security feed aggregation cycle")
    logger.info("=" * 60)
    
    # Get mode
    mode = mode_override or config.get("app", {}).get("mode", "instant")
    logger.info(f"Mode: {mode}")
    
    # Initialize storage
    db_path = config.get("app", {}).get("db_path", "data/alerts.sqlite")
    storage = Storage(db_path)
    logger.info(f"Storage initialized. Total seen items: {storage.get_seen_count()}")
    
    # Fetch from all sources
    all_items = []
    
    # RSS feeds
    rss_configs = config.get("feeds", {}).get("rss", [])
    rss_items = fetch_rss_feeds(rss_configs)
    all_items.extend(rss_items)
    logger.info(f"RSS: {len(rss_items)} items")
    
    # KEV feed
    kev_config = config.get("feeds", {}).get("kev", {})
    kev_items = fetch_kev_feeds(kev_config.get("enabled", False))
    all_items.extend(kev_items)
    logger.info(f"KEV: {len(kev_items)} items")
    
    # NVD feed
    nvd_config = config.get("feeds", {}).get("nvd", {})
    nvd_items = fetch_nvd_feeds(nvd_config)
    all_items.extend(nvd_items)
    logger.info(f"NVD: {len(nvd_items)} items")
    
    logger.info(f"Total fetched: {len(all_items)} items")
    
    # Filter and score items
    filter_config = config.get("filters", {})
    keywords = filter_config.get("keywords", [])
    deny_keywords = filter_config.get("deny_keywords", [])
    min_cvss = filter_config.get("min_cvss", 8.8)
    kev_always_alert = filter_config.get("kev_always_alert", True)
    
    alert_items = []
    digest_items = []
    
    for item in all_items:
        # Generate ID and check if seen
        item_id = generate_item_id(item)
        item.id = item_id
        
        if storage.is_seen(item_id):
            logger.debug(f"Skipping duplicate: {item.title[:50]}...")
            continue
        
        # Check if should alert
        should_alert_flag, reason = should_alert(
            item, keywords, deny_keywords, min_cvss, kev_always_alert
        )
        
        if should_alert_flag:
            alert_items.append((item, reason))
        elif mode == "digest":
            # Check if should be in digest
            if should_digest(item, keywords, deny_keywords, min_cvss):
                digest_items.append(item)
    
    logger.info(f"Items to alert: {len(alert_items)}")
    logger.info(f"Items for digest: {len(digest_items)}")
    
    # Handle notifications
    ntfy_config = config.get("ntfy", {})
    base_url = ntfy_config.get("base_url", "https://ntfy.sh")
    topic = ntfy_config.get("topic")
    priority = ntfy_config.get("priority", "high")
    headers = ntfy_config.get("headers")
    
    if not topic:
        logger.warning("No ntfy topic configured, skipping notifications")
        dry_run = True
    
    sent_count = 0
    skipped_count = 0
    
    if mode == "instant":
        # Send individual notifications
        for item, reason in alert_items:
            if dry_run:
                logger.info(f"[DRY RUN] Would send: {item.title[:60]}... ({reason})")
                sent_count += 1
            else:
                success = send_ntfy(
                    title=f"[{item.source}] {item.title}",
                    message=f"{item.summary[:200]}...\n\nReason: {reason}",
                    base_url=base_url,
                    topic=topic,
                    url=item.url,
                    tags=[item.category],
                    priority=priority,
                    headers=headers,
                )
                if success:
                    storage.mark_seen(item.id, item.source, item.title, item.url)
                    sent_count += 1
                else:
                    skipped_count += 1
    
    elif mode == "digest":
        # Accumulate and send digest
        all_digest_items = [item for item, _ in alert_items] + digest_items
        
        if all_digest_items:
            digest_output = config.get("app", {}).get("digest_output", "data/digest.md")
            digest_path = Path(digest_output)
            digest_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write digest markdown
            with open(digest_path, "w") as f:
                f.write(f"# Security Alert Digest\n\n")
                f.write(f"Generated: {datetime.utcnow().isoformat()}\n\n")
                f.write(f"## Alerts ({len(alert_items)})\n\n")
                
                for item, reason in alert_items:
                    f.write(f"### [{item.source}] {item.title}\n\n")
                    f.write(f"**Reason:** {reason}\n\n")
                    f.write(f"{item.summary}\n\n")
                    f.write(f"[Read more]({item.url})\n\n")
                    f.write("---\n\n")
                
                if digest_items:
                    f.write(f"## Digest Items ({len(digest_items)})\n\n")
                    for item in digest_items:
                        f.write(f"- [{item.title}]({item.url}) - {item.source}\n")
            
            # Send summary notification
            if dry_run:
                logger.info(f"[DRY RUN] Would send digest with {len(all_digest_items)} items")
                sent_count = len(all_digest_items)
            else:
                success = send_ntfy(
                    title=f"Security Digest: {len(all_digest_items)} items",
                    message=f"{len(alert_items)} alerts, {len(digest_items)} digest items\n\nSee: {digest_output}",
                    base_url=base_url,
                    topic=topic,
                    url=f"file://{digest_path.absolute()}",
                    priority=priority,
                    headers=headers,
                )
                if success:
                    # Mark all items as seen
                    for item in all_digest_items:
                        storage.mark_seen(item.id, item.source, item.title, item.url)
                    sent_count = len(all_digest_items)
                else:
                    skipped_count = len(all_digest_items)
    
    # Summary
    end_time = datetime.utcnow()
    duration = (end_time - start_time).total_seconds()
    
    logger.info("=" * 60)
    logger.info("Cycle complete")
    logger.info(f"Duration: {duration:.2f}s")
    logger.info(f"Fetched: {len(all_items)}")
    logger.info(f"Sent: {sent_count}")
    logger.info(f"Skipped: {skipped_count}")
    logger.info(f"Duplicates: {len(all_items) - len(alert_items) - len(digest_items) - skipped_count}")
    logger.info("=" * 60)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Security feed aggregator with ntfy notifications"
    )
    parser.add_argument(
        "--config",
        default="config.yaml",
        help="Path to config YAML file (default: config.yaml)",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run one cycle and exit",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be sent without actually sending",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )
    parser.add_argument(
        "--mode",
        choices=["instant", "digest"],
        help="Override mode from config",
    )
    parser.add_argument(
        "--log-file",
        help="Path to log file (default: logs/sec-alerts.log)",
    )
    
    args = parser.parse_args()
    
    # Setup logging
    log_file = args.log_file or "logs/sec-alerts.log"
    setup_logging(verbose=args.verbose, log_file=log_file)
    
    # Load config
    try:
        config = load_config(args.config)
    except FileNotFoundError as e:
        logging.error(f"Configuration error: {e}")
        sys.exit(1)
    except Exception as e:
        logging.error(f"Error loading config: {e}")
        sys.exit(1)
    
    # Run
    try:
        run_once(config, dry_run=args.dry_run, mode_override=args.mode)
    except KeyboardInterrupt:
        logging.info("Interrupted by user")
        sys.exit(0)
    except Exception as e:
        logging.exception(f"Error during execution: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

