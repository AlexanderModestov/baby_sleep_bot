# Baby Sleep Tracker Telegram Bot

This is a Telegram bot that integrates with the Baby Sleep Prediction web application.

## Features

- `/start` - Register and authorize users, collect custom names
- `/settings` - Configure notification preferences and change user names
- WebApp integration - Opens the main sleep tracking application
- User management with persistent storage

## Setup

1. Create a new bot with @BotFather on Telegram
2. Copy `.env.example` to `.env` and add your bot token:
   ```
   BOT_TOKEN=your_bot_token_here
   WEBAPP_URL=http://localhost:3000
   API_BASE_URL=http://localhost:3000/api
   ```

3. Install dependencies:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

4. Run the bot:
   ```bash
   python main.py
   ```

## Architecture

- `main.py` - Entry point and bot initialization
- `config/settings.py` - Configuration management
- `database/user_manager.py` - User data storage and management
- `handlers/` - Command and callback handlers
  - `start_handler.py` - Registration and main menu
  - `settings_handler.py` - User settings management

## User Data

User data is stored in `database/users.json` with the following structure:
```json
{
  "user_id": {
    "telegram_id": 123456789,
    "username": "username",
    "first_name": "John",
    "last_name": "Doe",
    "custom_name": "Johnny",
    "settings": {
      "notifications_enabled": true,
      "sleep_reminders": true,
      "wake_reminders": true
    },
    "registered": true
  }
}
```

## WebApp Integration

The bot opens the web application with the user's Telegram ID as a URL parameter:
`http://localhost:3000?telegram_user_id=123456789`

The web app can then use this ID to fetch user preferences and display the custom name.# baby_sleep_bot
