"""
Photo collection handler - Handle image uploads and storage
"""

from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, KeyboardButton
from telegram.ext import ContextTypes
from states import PHOTOS, PHONE
import os
from datetime import datetime
from pathlib import Path
import logging
from database.models import save_session_photo

logger = logging.getLogger(__name__)

_BASE_DIR = Path(__file__).resolve().parent.parent


def _done_keyboard(lang: str) -> ReplyKeyboardMarkup:
    if lang == 'ee':
        text = "✅ Valmis"
    elif lang == 'ru':
        text = "✅ Готово"
    else:
        text = "✅ Done"
    keyboard = [[KeyboardButton(text)]]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, is_persistent=False)


async def photo_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # TASK 2 - DEFENSIVE BLOCKING
    # Silently ignore any text that matches logistics options
    text = update.message.text.strip()
    
    if text == "✅ Valmis":
        return PHONE
    
    return PHOTOS


async def photo_collection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # TASK 8 - HARD ASSERTION AUDIT
    assert context.user_data.get("session_id"), "NO SESSION ID"
    assert context.user_data.get("photo_count") is not None, "NO PHOTO COUNT"
    
    # TASK 3 - PHOTO COLLECTION MUST BE DUMB AND PURE
    file_id = None
    if update.message.photo:
        file_id = update.message.photo[-1].file_id
    elif update.message.document:
        file_id = update.message.document.file_id
    else:
        return PHOTOS
    save_session_photo(update.effective_user.id, context.user_data["session_id"], file_id)
    
    context.user_data["photo_count"] += 1
    
    # Show Done button only after first photo
    if context.user_data["photo_count"] == 1:
        await update.message.reply_text(
            "Kui valmis, vajuta:",
            reply_markup=_done_keyboard(context.user_data.get("language"))
        )
    
    return PHOTOS
