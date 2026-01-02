# security-feed-ntfy

Capture the latest cybersecurity news with RSS feeds. Get free notifications on your phone with ntfy!

A lightweight alert service that pulls security feeds (RSS + CVE sources), filters them by keywords and severity, deduplicates, and pushes notifications to your phone/desktop via [ntfy](https://ntfy.sh). Runs on a schedule using cron.

## Features

- ✅ **RSS Feed Aggregation** - Pulls from multiple security news sources
- ✅ **Smart Filtering** - Keyword-based filtering with deny lists
- ✅ **Deduplication** - SQLite-based state tracking prevents duplicate notifications
- ✅ **Instant Notifications** - Push alerts directly to your phone via ntfy
- ✅ **Digest Mode** - Option to accumulate alerts and send summaries
- ✅ **Configurable** - YAML-based configuration, no code changes needed
- ✅ **Cron-Ready** - Includes wrapper script for automated scheduling

## Architecture

```
Cron → Python Script → RSS Feeds → Filter/Score → Deduplicate → ntfy → Your Phone
```

- **Feeds**: RSS feeds (Hacker News, BleepingComputer, KrebsOnSecurity, SANS ISC Diary)
- **Filtering**: Keywords + severity thresholds + deny keywords
- **Deduplication**: Local SQLite database tracks seen items
- **Output**: ntfy push notifications + optional Markdown digest file

## Requirements

- Linux host (or WSL) with cron
- Python 3.11+ (3.9+ should work)
- Access to an ntfy server:
  - Use the public [ntfy.sh](https://ntfy.sh) server (fastest to start), OR
  - Self-host ntfy for privacy and control

## Installation

### 1. Clone or Download the Repository

```bash
git clone <repository-url>
cd security-feed-ntfy
```

### 2. Create Virtual Environment (Recommended)

```bash
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -U pip
pip install -r requirements.txt
```

### 4. Configure

Copy the example config and customize it:

```bash
cp config.example.yaml config.yaml
```

Edit `config.yaml` and set:
- Your ntfy topic name (use a hard-to-guess random string)
- Your keywords and filters
- RSS feeds you want to monitor

### 5. Set Up ntfy

#### Option A: Use Public ntfy Server (Fastest)

1. Pick a topic name that is hard to guess (treat it like a password):
   - Example: `sec-alerts-7x9k2m4p8q1w3r5t6y`

2. Subscribe on your phone/desktop:
   - **Android/iOS**: Install the "ntfy" app, add subscription
     - Server: `https://ntfy.sh`
     - Topic: `your-topic-name`
   - **Web**: Open `https://ntfy.sh/your-topic-name` in a browser

3. Test it:
   ```bash
   curl -d "Test notification" "https://ntfy.sh/your-topic-name"
   ```

#### Option B: Self-Host ntfy (Recommended for Privacy)

Use Docker:

```bash
docker run -p 80:80 -v /var/cache/ntfy:/var/cache/ntfy -v /etc/ntfy:/etc/ntfy binwiederhier/ntfy serve
```

Then update `config.yaml` with your server URL.

## Usage

### Run Once (Manual)

```bash
python3 -m sec_alerts.main --config config.yaml --once
```

### Test Without Sending Notifications

```bash
python3 -m sec_alerts.main --config config.yaml --dry-run --verbose
```

### Command Line Options

- `--config PATH` - Path to config YAML file (default: `config.yaml`)
- `--once` - Run one cycle and exit
- `--dry-run` - Print what would be sent without actually sending
- `--verbose` - Enable verbose logging
- `--mode instant|digest` - Override mode from config
- `--log-file PATH` - Path to log file (default: `logs/sec-alerts.log`)

### Automated Scheduling (Cron)

1. The `run.sh` script is already set up for cron usage.

2. Add to your crontab:
   ```bash
   crontab -e
   ```

3. Add one of these lines:
   ```bash
   # Run every hour
   0 * * * * /home/isaac/ai-hacking/security-feed-ntfy/run.sh
   
   # Or run every 30 minutes
   */30 * * * * /home/isaac/ai-hacking/security-feed-ntfy/run.sh
   ```

4. Verify it's set up:
   ```bash
   crontab -l
   ```

5. Check logs:
   ```bash
   tail -f logs/sec-alerts.log
   ```

See `CRON_SETUP.md` for detailed cron setup instructions.

## Configuration

The configuration file (`config.yaml`) controls all aspects of the system:

### App Settings

```yaml
app:
  timezone: "America/New_York"
  mode: "instant"  # instant | digest
  digest_output: "data/digest.md"
  db_path: "data/alerts.sqlite"
```

### ntfy Settings

```yaml
ntfy:
  base_url: "https://ntfy.sh"
  topic: "sec-alerts-your-random-topic-name"
  priority: "high"  # min | low | default | high | urgent
  # Optional: headers for auth if self-hosted
  # headers:
  #   Authorization: "Bearer YOUR_TOKEN"
```

### Filters

```yaml
filters:
  keywords:
    - rce
    - auth bypass
    - exchange
    - citrix
    - kubernetes
    - vmware
  deny_keywords:
    - "crypto price"
    - "giveaway"
  min_cvss: 8.8  # Minimum CVSS score for CVEs
  kev_always_alert: true  # Always alert on CISA KEV items
```

### Feeds

```yaml
feeds:
  rss:
    - name: "Hacker News"
      url: "https://news.ycombinator.com/rss"
      category: "news"
    - name: "BleepingComputer"
      url: "https://www.bleepingcomputer.com/feed/"
      category: "news"
    # Add more RSS feeds as needed
```

## Project Structure

```
security-feed-ntfy/
├── README.md
├── LICENSE
├── requirements.txt
├── config.example.yaml      # Example configuration
├── config.yaml              # Your config (not in git)
├── run.sh                    # Cron wrapper script
├── test.py                   # Test suite
├── test_dedup.py            # Deduplication test
├── CRON_SETUP.md            # Cron setup guide
├── sec_alerts/
│   ├── __init__.py
│   ├── main.py              # Main entry point
│   ├── models.py            # Data models (AlertItem)
│   ├── storage.py           # SQLite deduplication
│   ├── notify.py            # ntfy notification sender
│   ├── scoring.py           # Filtering/scoring logic
│   └── fetchers/
│       ├── __init__.py
│       └── rss.py           # RSS feed fetcher
├── data/
│   └── alerts.sqlite        # Deduplication database
└── logs/
    └── sec-alerts.log       # Application logs
```

## Testing

### Run Test Suite

```bash
python3 test.py
```

This will test:
- RSS fetcher functionality
- Storage and deduplication
- Scoring/filtering logic
- Config file loading

### Test Deduplication

```bash
python3 test_dedup.py
```

Or run the main script twice to verify duplicates are skipped:

```bash
python3 -m sec_alerts.main --config config.yaml --once
python3 -m sec_alerts.main --config config.yaml --once
```

The second run should show `Sent: 0` and `Duplicates: X` in the summary.

## How It Works

1. **Fetch**: Pulls items from configured RSS feeds
2. **Filter**: Applies keyword matching and severity thresholds
3. **Deduplicate**: Checks SQLite database to skip already-seen items
4. **Notify**: Sends matching items via ntfy to your phone
5. **Track**: Marks items as seen in the database

### Filtering Logic

Items trigger alerts if they:
- Match keywords AND contain urgent terms (RCE, auth bypass, exploited, etc.)
- Have CVSS score >= `min_cvss` (for CVEs)
- Are from CISA KEV feed (if `kev_always_alert: true`)

Items are excluded if they:
- Match any `deny_keywords`

### Modes

- **Instant Mode**: Sends individual notifications immediately when items match
- **Digest Mode**: Accumulates items and sends a summary notification with a markdown digest file

## Observability

The script logs detailed information:

- Run start/end timestamps
- Counts fetched per source
- Counts filtered and sent
- Counts skipped (duplicates)
- Duration of each run

Logs are written to:
- Console (when run manually)
- `logs/sec-alerts.log` (when run via cron)

## Security Notes

⚠️ **Important Security Considerations:**

- If using public ntfy.sh, use a **long random topic name** (treat it like a password)
- Anyone who knows your topic name can see your notifications
- Prefer self-hosted ntfy if pushing sensitive internal data
- Never include secrets in notifications (tokens, internal hostnames, etc.)
- Keep NVD API keys in `config.yaml` and don't commit it to git
- The `config.yaml` file is gitignored by default

## Troubleshooting

### "No notifications received"

1. Verify you're subscribed to the correct ntfy topic
2. Test with curl: `curl -d "test" "https://ntfy.sh/your-topic"`
3. Run with `--dry-run --verbose` to see what would be sent
4. Check that items match your keywords (run with `--verbose`)

### "Too many alerts"

- Raise `min_cvss` threshold
- Add more `deny_keywords`
- Switch to `digest` mode
- Refine your `keywords` list

### "Cron isn't running"

- Ensure paths in cron are absolute (not relative)
- Check logs: `tail -n 200 logs/sec-alerts.log`
- Verify `run.sh` is executable: `chmod +x run.sh`
- Test `run.sh` manually: `./run.sh`

### "RSS fetcher not available"

- Install dependencies: `pip install -r requirements.txt`
- Verify feedparser is installed: `python3 -c "import feedparser"`

## Roadmap

Planned features:

- [ ] CISA KEV feed fetcher
- [ ] NVD CVE feed fetcher
- [ ] Slack/Discord outputs
- [ ] Per-client "tech stack profiles"
- [ ] CPE matching against known assets
- [ ] PoC detection signals (exploit-db, metasploit, nuclei templates)
- [ ] Enrichment: vendor advisory links, EPSS score, KEV correlation
- [ ] Quiet hours and batching

## Contributing

Contributions welcome! Areas that need work:

- KEV and NVD feed fetchers
- Additional output formats
- Enhanced filtering/scoring rules
- Performance optimizations

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Acknowledgments

- [ntfy](https://ntfy.sh) for the excellent notification service
- RSS feed providers (Hacker News, BleepingComputer, KrebsOnSecurity, SANS ISC)
- Built with Python, feedparser, and SQLite

---

**Status**: ✅ RSS feeds working, deduplication working, notifications working. KEV and NVD fetchers coming soon.
