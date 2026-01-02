#!/usr/bin/env python3
"""Test script to verify deduplication is working."""

import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from sec_alerts.storage import Storage
from sec_alerts.models import AlertItem


def test_deduplication():
    """Test that deduplication prevents duplicate notifications."""
    print("=" * 60)
    print("Testing Deduplication")
    print("=" * 60)
    
    # Use a test database
    test_db = "data/test_dedup.sqlite"
    storage = Storage(test_db)
    
    # Create a test item
    test_item = AlertItem(
        id="test_dedup_123",
        source="test_source",
        category="news",
        title="Test Alert: Critical RCE Vulnerability",
        summary="This is a test alert to verify deduplication",
        url="https://example.com/test",
        published_at=datetime.utcnow(),
    )
    
    print(f"\n1. Creating test item: {test_item.title}")
    
    # Check if seen (should be False)
    is_seen_before = storage.is_seen(test_item.id)
    print(f"   Is seen before marking? {is_seen_before}")
    
    if is_seen_before:
        print("   ⚠ Item already exists (might be from previous test)")
    else:
        print("   ✓ Item not seen yet (expected)")
    
    # Mark as seen
    storage.mark_seen(test_item.id, test_item.source, test_item.title, test_item.url)
    print(f"   ✓ Marked item as seen")
    
    # Check if seen again (should be True)
    is_seen_after = storage.is_seen(test_item.id)
    print(f"   Is seen after marking? {is_seen_after}")
    
    if is_seen_after:
        print("   ✓ Deduplication working! Item correctly identified as seen")
    else:
        print("   ✗ Deduplication failed! Item not recognized as seen")
        return False
    
    # Test with production database
    print(f"\n2. Checking production database")
    prod_storage = Storage("data/alerts.sqlite")
    count = prod_storage.get_seen_count()
    print(f"   Total items in production DB: {count}")
    
    if count > 0:
        print(f"   ✓ Production database has {count} seen items")
        print(f"   This means deduplication is tracking items from previous runs")
    else:
        print(f"   ℹ Production database is empty (first run)")
    
    print(f"\n3. Simulating duplicate detection")
    print(f"   If you run the main script twice, items from the first run")
    print(f"   should be skipped in the second run.")
    print(f"   You can verify this by:")
    print(f"     - Running: python3 -m sec_alerts.main --config config.yaml --once")
    print(f"     - Running it again immediately")
    print(f"     - The second run should show 'Duplicates: X' in the summary")
    
    return True


if __name__ == "__main__":
    success = test_deduplication()
    sys.exit(0 if success else 1)

