# Romupunkt Bot (Telegram)

Telegram bot for Estonian car dismantling leads (Romupunkt).

## Requirements

- Python installed (on Windows use `py`)

## Setup (Windows PowerShell)

1) Install dependencies:

```powershell
py -m pip install -r requirements.txt
```

2) Set your Telegram bot token (do NOT commit it):

```powershell
$env:TELEGRAM_BOT_TOKEN = "PASTE_YOUR_TOKEN_HERE"
```

3) Run the bot:

```powershell
py bot.py
```

## Flow

- Language selection (EE/EN)
- Plate number + owner name
- Curb weight (tühimass)
- Completeness
- Transport (tow vs self-bring)
- If tow: request location
- Photo collection (min 3)
- Phone number

## Data storage

Leads are stored in `romupunkt.db` (SQLite) in the project folder.
