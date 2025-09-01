#!/bin/bash

# Start the async bot with PostgreSQL support

echo "🎣 Starting Fishing Bot with PostgreSQL..."

# Check if TELEGRAM_BOT_TOKEN is set
if [ -z "$TELEGRAM_BOT_TOKEN" ]; then
    echo "❌ Error: TELEGRAM_BOT_TOKEN environment variable is not set"
    echo "Please run: export TELEGRAM_BOT_TOKEN='your_token_here'"
    exit 1
fi

# Optional: Set DATABASE_URL if you want to use a different database
# export DATABASE_URL="postgresql://user:password@localhost/fishing_bot"

# Run the async version of the bot
python3 main.py