# Cron Job Setup Instructions

## Quick Setup

1. **Edit your crontab:**
   ```bash
   crontab -e
   ```

2. **Add this line to run every hour:**
   ```
   0 * * * * /home/isaac/ai-hacking/security-feed-ntfy/run.sh
   ```

   Or to run every 30 minutes:
   ```
   */30 * * * * /home/isaac/ai-hacking/security-feed-ntfy/run.sh
   ```

3. **Save and exit** (in vim: press `Esc`, type `:wq`, press Enter)

## Cron Schedule Format

The format is: `minute hour day month weekday`

Examples:
- `0 * * * *` - Every hour at minute 0 (1:00, 2:00, 3:00, etc.)
- `*/30 * * * *` - Every 30 minutes
- `0 */2 * * *` - Every 2 hours
- `0 9,17 * * *` - At 9 AM and 5 PM daily
- `0 9 * * 1-5` - At 9 AM on weekdays only

## Verify Cron Job

1. **Check if cron is running:**
   ```bash
   systemctl status cron
   ```

2. **View your cron jobs:**
   ```bash
   crontab -l
   ```

3. **Check the logs:**
   ```bash
   tail -f logs/sec-alerts.log
   ```

## Troubleshooting

- **Cron doesn't run:** Make sure the script path is absolute (not relative)
- **Permission errors:** Ensure `run.sh` is executable: `chmod +x run.sh`
- **Python not found:** The script should use `python3` (already set in run.sh)
- **No logs:** Check that the `logs/` directory exists and is writable

