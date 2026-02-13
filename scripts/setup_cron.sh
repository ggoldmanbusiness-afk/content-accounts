#!/bin/bash
# Sets up launchd jobs for daily scraping and weekly recommendations

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PYTHON="$(which python3)"

echo "Setting up analytics cron jobs..."
echo "Project: $PROJECT_DIR"
echo "Python: $PYTHON"

# Daily scrape (8am)
SCRAPE_PLIST="$HOME/Library/LaunchAgents/com.content-accounts.daily-scrape.plist"
cat > "$SCRAPE_PLIST" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.content-accounts.daily-scrape</string>
    <key>ProgramArguments</key>
    <array>
        <string>$PYTHON</string>
        <string>$PROJECT_DIR/scripts/daily_scrape.py</string>
    </array>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>8</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>
    <key>WorkingDirectory</key>
    <string>$PROJECT_DIR</string>
    <key>StandardOutPath</key>
    <string>$PROJECT_DIR/logs/daily_scrape.log</string>
    <key>StandardErrorPath</key>
    <string>$PROJECT_DIR/logs/daily_scrape_error.log</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin</string>
    </dict>
</dict>
</plist>
EOF

# Weekly recommend (Monday 9am)
RECOMMEND_PLIST="$HOME/Library/LaunchAgents/com.content-accounts.weekly-recommend.plist"
cat > "$RECOMMEND_PLIST" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.content-accounts.weekly-recommend</string>
    <key>ProgramArguments</key>
    <array>
        <string>$PYTHON</string>
        <string>$PROJECT_DIR/scripts/weekly_recommend.py</string>
    </array>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Weekday</key>
        <integer>1</integer>
        <key>Hour</key>
        <integer>9</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>
    <key>WorkingDirectory</key>
    <string>$PROJECT_DIR</string>
    <key>StandardOutPath</key>
    <string>$PROJECT_DIR/logs/weekly_recommend.log</string>
    <key>StandardErrorPath</key>
    <string>$PROJECT_DIR/logs/weekly_recommend_error.log</string>
</dict>
</plist>
EOF

mkdir -p "$PROJECT_DIR/logs"

launchctl load "$SCRAPE_PLIST"
launchctl load "$RECOMMEND_PLIST"

echo "Done! Cron jobs installed:"
echo "  - Daily scrape: 8:00 AM"
echo "  - Weekly recommend: Monday 9:00 AM"
echo ""
echo "To check status: launchctl list | grep content-accounts"
echo "To unload: launchctl unload $SCRAPE_PLIST"
