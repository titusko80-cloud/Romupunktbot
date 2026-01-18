# Bot Logo Setup Instructions

## 🎯 WHERE TO PLACE YOUR LOGO

### ✅ Step 1: Place Logo File
Put your logo image file in the **same directory** as `bot.py`:

```
C:\Users\titus\Desktop\Romupunktbot\
├── bot.py
├── logo.png  ← PLACE YOUR LOGO HERE
├── handlers/
├── database/
└── ...
```

### ✅ Step 2: Supported Formats
- **PNG** (recommended)
- **JPG** 
- **JPEG**
- **GIF** (if animated)
- **WEBP**

### ✅ Step 3: File Name
The code looks for `logo.png` by default. If your file has a different name:
- Rename it to `logo.png`, OR
- Update the filename in `handlers/start.py` line 62

### ✅ Step 4: Logo Size Recommendations
- **Optimal**: 512x512 pixels
- **Maximum**: 10MB file size
- **Aspect**: Square or slightly rectangular

## 🚀 How It Works

When user clicks `/start`:
1. **Bot sends your logo image** first
2. **Then shows language selection** buttons
3. **Clean, professional UX** with your branding

## 🔄 If Logo Not Found

The bot has fallback:
- **Logs warning**: "Logo file not found"
- **Sends text fallback**: "🏎️ ROMUPUNKT"
- **Continues normally** with language selection

## ✅ Test It

1. **Place your logo** as `logo.png` in bot directory
2. **Restart the bot**
3. **Test**: Send `/start` → Should see your logo first!

Your logo will now be the first thing users see! 🏎️✨
