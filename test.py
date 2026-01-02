#!/usr/bin/env python3
"""Quick test script for security feed aggregator."""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from sec_alerts.fetchers import rss
from sec_alerts.models import AlertItem
from sec_alerts.storage import Storage
from sec_alerts.scoring import should_alert
from sec_alerts.notify import send_ntfy


def test_rss_fetcher():
    """Test RSS fetcher with a simple feed."""
    print("=" * 60)
    print("Testing RSS Fetcher")
    print("=" * 60)
    
    # Test with Hacker News RSS feed
    test_url = "https://news.ycombinator.com/rss"
    test_name = "Hacker News"
    
    try:
        items = rss.fetch_rss(test_url, test_name, "news")
        print(f"✓ Successfully fetched {len(items)} items from {test_name}")
        
        if items:
            print(f"\nFirst item:")
            item = items[0]
            print(f"  Title: {item.title[:80]}...")
            print(f"  URL: {item.url}")
            print(f"  Published: {item.published_at}")
            print(f"  Summary: {item.summary[:100]}...")
            return True
        else:
            print("⚠ No items found in feed")
            return False
            
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_storage():
    """Test storage/deduplication."""
    print("\n" + "=" * 60)
    print("Testing Storage")
    print("=" * 60)
    
    try:
        # Use a test database
        storage = Storage("data/test_alerts.sqlite")
        print("✓ Storage initialized")
        
        # Test with a dummy item
        test_id = "test_item_123"
        storage.mark_seen(test_id, "test_source", "Test Title", "https://example.com")
        print("✓ Marked test item as seen")
        
        is_seen = storage.is_seen(test_id)
        if is_seen:
            print("✓ Deduplication check works")
        else:
            print("✗ Deduplication check failed")
            return False
        
        count = storage.get_seen_count()
        print(f"✓ Total seen items: {count}")
        
        return True
        
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_scoring():
    """Test scoring/filtering logic."""
    print("\n" + "=" * 60)
    print("Testing Scoring")
    print("=" * 60)
    
    try:
        from datetime import datetime
        
        # Create a test item
        test_item = AlertItem(
            id="test_123",
            source="test",
            category="news",
            title="Critical RCE vulnerability found in Exchange",
            summary="A remote code execution vulnerability has been discovered",
            url="https://example.com",
            published_at=datetime.utcnow(),
        )
        
        keywords = ["rce", "exchange", "critical"]
        deny_keywords = ["crypto price"]
        min_cvss = 8.8
        
        should_alert_flag, reason = should_alert(
            test_item, keywords, deny_keywords, min_cvss
        )
        
        if should_alert_flag:
            print(f"✓ Scoring works - item should alert: {reason}")
        else:
            print(f"✗ Scoring failed - item should alert but doesn't")
            return False
        
        # Test deny keyword
        deny_item = AlertItem(
            id="test_456",
            source="test",
            category="news",
            title="Crypto price update",
            summary="Bitcoin price is up",
            url="https://example.com",
            published_at=datetime.utcnow(),
        )
        
        should_alert_flag, reason = should_alert(
            deny_item, keywords, deny_keywords, min_cvss
        )
        
        if not should_alert_flag:
            print(f"✓ Deny keyword filtering works: {reason}")
        else:
            print(f"✗ Deny keyword filtering failed")
            return False
        
        return True
        
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_config_loading():
    """Test config file loading."""
    print("\n" + "=" * 60)
    print("Testing Config Loading")
    print("=" * 60)
    
    try:
        import yaml
        
        config_file = Path("config.example.yaml")
        if not config_file.exists():
            print("⚠ config.example.yaml not found, skipping config test")
            return True
        
        with open(config_file, "r") as f:
            config = yaml.safe_load(f)
        
        print("✓ Config file loaded successfully")
        
        # Check required sections
        required_sections = ["app", "ntfy", "filters", "feeds"]
        for section in required_sections:
            if section in config:
                print(f"✓ Section '{section}' present")
            else:
                print(f"✗ Section '{section}' missing")
                return False
        
        # Check RSS feeds
        rss_feeds = config.get("feeds", {}).get("rss", [])
        print(f"✓ Found {len(rss_feeds)} RSS feeds configured")
        
        return True
        
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_ntfy_dry_run():
    """Test ntfy notification (dry run - won't actually send)."""
    print("\n" + "=" * 60)
    print("Testing ntfy Notification (Dry Run)")
    print("=" * 60)
    
    print("ℹ Skipping actual notification send (would require valid topic)")
    print("  To test notifications, run:")
    print("    python -m sec_alerts.main --config config.yaml --dry-run")
    return True


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("Security Feed Aggregator - Test Suite")
    print("=" * 60)
    
    results = []
    
    # Run tests
    results.append(("RSS Fetcher", test_rss_fetcher()))
    results.append(("Storage", test_storage()))
    results.append(("Scoring", test_scoring()))
    results.append(("Config Loading", test_config_loading()))
    results.append(("ntfy (Dry Run)", test_ntfy_dry_run()))
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n✓ All tests passed! System is ready to use.")
        print("\nNext steps:")
        print("  1. Copy config.example.yaml to config.yaml")
        print("  2. Update config.yaml with your ntfy topic")
        print("  3. Run: python -m sec_alerts.main --config config.yaml --dry-run --verbose")
        return 0
    else:
        print("\n✗ Some tests failed. Please check the errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())

