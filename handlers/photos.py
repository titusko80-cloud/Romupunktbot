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
from uuid import uuid4
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

    lang = context.user_data.get("language")
    done_texts = {"✅ Valmis", "✅ Готово", "✅ Done"}
    if lang == "ee":
        done_texts = {"✅ Valmis"}
    elif lang == "ru":
        done_texts = {"✅ Готово"}
    elif lang == "en":
        done_texts = {"✅ Done"}

    if text in done_texts:
        photo_count = context.user_data.get("photo_count") or 0
        if photo_count < 1:
            if lang == "ee":
                msg = "📸 Palun laadi vähemalt üks pilt üles enne kui jätkad."
            elif lang == "ru":
                msg = "📸 Пожалуйста, отправьте хотя бы одно фото перед тем как продолжить."
            else:
                msg = "📸 Please upload at least one photo before continuing."
            await update.message.reply_text(msg)
            return PHOTOS
        if lang == "ee":
            msg = "📞 Palun sisesta oma telefoninumber, et saaksime sinuga kohe ühendust võtta."
        elif lang == "ru":
            msg = "📞 Пожалуйста, отправьте номер телефона, чтобы мы могли быстро связаться с вами."
        else:
            msg = "📞 Please send your phone number so we can contact you quickly."
        await update.message.reply_text(msg, reply_markup=ReplyKeyboardRemove())
        return PHONE
    
    return PHOTOS


async def photo_collection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not context.user_data.get("session_id"):
        context.user_data["session_id"] = uuid4().hex
    if context.user_data.get("photo_count") is None:
        context.user_data["photo_count"] = 0
     
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
        lang = context.user_data.get("language")
        if lang == "ru":
            msg = "Когда закончите, нажмите:"
        elif lang == "en":
            msg = "When finished, tap:"
        else:
            msg = "Kui valmis, vajuta:"
        await update.message.reply_text(
            msg,
            reply_markup=_done_keyboard(context.user_data.get("language"))
        )
    
    return PHOTOS
