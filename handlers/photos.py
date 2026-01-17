"""
Photo collection handler - Handle image uploads and storage
"""

from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, KeyboardButton
from telegram.ext import ContextTypes
from states import PHOTOS, PHONE
import os
from datetime import datetime
from pathlib import Path


_BASE_DIR = Path(__file__).resolve().parent.parent


def _is_done_text(text: str, lang: str) -> bool:
    t = (text or "").strip().lower()
    if not t:
        return False
    if lang == 'ee':
        return ("valmis" in t) or (t == "done") or ("done" in t)
    if lang == 'ru':
        return ("готово" in t) or (t == "done") or ("done" in t)
    return (t == "done") or ("done" in t)


def _done_keyboard(lang: str) -> ReplyKeyboardMarkup:
    if lang == 'ee':
        text = "✅ Valmis"
    elif lang == 'ru':
        text = "✅ Готово"
    else:
        text = "✅ Done"
    keyboard = [[KeyboardButton(text)]]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, is_persistent=True)


async def _ask_phone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = context.user_data.get('language')
    if lang == 'ee':
        msg = "Täname! Viimane samm:\n\nPalun sisestage oma telefoninumber, et me saaksime teile kiiresti pakkumise teha:"
    elif lang == 'ru':
        msg = "Спасибо! Последний шаг:\n\nВведите ваш номер телефона, чтобы мы быстро сделали предложение:"
    else:
        msg = "Thank you! Final step:\n\nPlease enter your phone number so we can quickly send you an offer:"

    await update.message.reply_text(msg, reply_markup=ReplyKeyboardRemove())
    return PHONE


async def photo_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = context.user_data.get('language')
    if _is_done_text(update.message.text, lang):
        if context.user_data.get('photo_count', 0) >= 3:
            return await _ask_phone(update, context)

        if lang == 'ee':
            msg = "Palun saatke vähemalt 3 fotot enne kui lõpetate."
        elif lang == 'ru':
            msg = "Пожалуйста, отправьте минимум 3 фото перед завершением."
        else:
            msg = "Please send at least 3 photos before finishing."

        await update.message.reply_text(msg, reply_markup=_done_keyboard(lang))
        return PHOTOS

    if lang == 'ee':
        msg = "Palun saatke foto(d). Kui olete valmis (vähemalt 3 fotot), vajutage 'Valmis'."
    elif lang == 'ru':
        msg = "Пожалуйста, отправьте фото. Когда будете готовы (минимум 3 фото), нажмите 'Готово'."
    else:
        msg = "Please send photo(s). When finished (at least 3 photos), tap 'Done'."

    await update.message.reply_text(msg, reply_markup=_done_keyboard(lang))
    return PHOTOS

async def photo_collection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle photo uploads"""
    # Initialize photo count if not exists
    if 'photo_count' not in context.user_data:
        context.user_data['photo_count'] = 0
        context.user_data['photos'] = []

    lang = context.user_data.get('language')

    file = None
    ext = "jpg"
    if update.message.photo:
        file = await update.message.photo[-1].get_file()
        ext = "jpg"
    elif update.message.document and (update.message.document.mime_type or "").startswith("image/"):
        file = await update.message.document.get_file()
        mt = update.message.document.mime_type or ""
        if mt == "image/png":
            ext = "png"
        elif mt == "image/webp":
            ext = "webp"
        else:
            ext = "jpg"
    else:
        if lang == 'ee':
            msg = "Palun saatke foto (pilt) või vajutage 'Valmis'."
        elif lang == 'ru':
            msg = "Пожалуйста, отправьте фото (картинку) или нажмите 'Готово'."
        else:
            msg = "Please send a photo (image) or tap 'Done'."
        await update.message.reply_text(msg, reply_markup=_done_keyboard(lang))
        return PHOTOS
    
    photo_dir = _BASE_DIR / 'photos'
    photo_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate unique filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    user_id = update.effective_user.id
    rel_path = Path('photos') / f"{user_id}_{timestamp}_{context.user_data['photo_count'] + 1}.{ext}"
    abs_path = _BASE_DIR / rel_path
    
    # Download and save photo
    await file.download_to_drive(str(abs_path))
    
    # Store photo info
    context.user_data['photos'].append(rel_path.as_posix())
    context.user_data['photo_count'] += 1

    count = context.user_data['photo_count']
    if lang == 'ee':
        msg = f"Foto {count} saadetud."
        if count < 3:
            msg += f" Palun saatke veel {3 - count} fotot."
        else:
            msg += " Kui olete valmis, vajutage 'Valmis'."
    elif lang == 'ru':
        msg = f"Фото {count} получено."
        if count < 3:
            msg += f" Пожалуйста, отправьте ещё {3 - count} фото."
        else:
            msg += " Когда будете готовы, нажмите 'Готово'."
    else:
        msg = f"Photo {count} received."
        if count < 3:
            msg += f" Please send {3 - count} more photos."
        else:
            msg += " When finished, tap 'Done'."

    await update.message.reply_text(msg, reply_markup=_done_keyboard(lang))
    return PHOTOS
