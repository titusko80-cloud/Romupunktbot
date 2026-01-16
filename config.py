"""
Configuration settings for Romupunkt Bot
"""

import os

# Your bot token from @BotFather
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN") or "YOUR_BOT_TOKEN_HERE"

# Database settings
DATABASE_URL = "sqlite:///romupunkt.db"

# Estonian Transport Administration API (if available)
TRANSPORDIAMET_API_KEY = None

# Photo settings
MAX_PHOTOS = 4
PHOTO_QUALITY = 80

# Supported languages
SUPPORTED_LANGUAGES = ['ee', 'en']

# Estonian license plate format regex
LICENSE_PLATE_REGEX = r'^[0-9]{3}\s[A-Z]{3}$'
