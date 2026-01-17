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

logger = logging.getLogger(__name__)

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
    """Ask for phone number and send admin notification if lead exists"""
    from handlers.finalize import send_lead_card
    
    lang = context.user_data.get('language')
    lead_id = context.user_data.get('lead_id')
    
    # If we have a lead (photos were sent), send admin notification now
    if lead_id:
        phone = context.user_data.get('phone_number')
        if phone:
            logger.info("Sending admin notification for existing lead %d after photos", lead_id)
            await send_lead_card(context, lead_id, phone)
    
    if lang == 'ee':
        msg = "Täname! Viimane samm:\n\nPalun sisestage oma telefoninumber, et me saaksime teile kiiresti pakkumise teha:"
    elif lang == 'ru':
        msg = "Спасибо! Последний шаг:\n\nВведите ваш номер телефона, чтобы мы быстро сделали предложение:"
    else:
        msg = "Thank you! Final step:\n\nPlease enter your phone number so we can quickly send you an offer:"

    await update.message.reply_text(msg, reply_markup=ReplyKeyboardRemove())
    return PHONE


async def photo_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle 'Done' button - enforce gate before proceeding"""
    from database.models import get_session_photos
    
    lang = context.user_data.get('language', 'en')
    text = update.message.text.strip()
    
    # Check for Done button in all languages
    done_texts = ['✅ Valmis', '✅ Готово', '✅ Done']
    
    if text in done_texts:
        session_id = context.user_data.get('session_id')
        if not session_id:
            # No session, proceed to phone step
            return await _ask_phone(update, context)
        
        # Check if user has uploaded any photos
        user_id = update.effective_user.id
        photos = get_session_photos(user_id, session_id)
        
        if not photos:
            # No photos uploaded, warn user
            if lang == 'ee':
                msg = "Palun saatke vähemalt üks foto enne 'Valmis' vajutamist."
            elif lang == 'ru':
                msg = "Пожалуйста, отправьте хотя бы одно фото перед нажатием 'Готово'."
            else:
                msg = "Please send at least one photo before tapping 'Done'."
            await update.message.reply_text(msg, reply_markup=_done_keyboard(lang))
            return PHOTOS
        
        # Have photos, proceed to phone step
        logger.info("User clicked Done with %d photos in session %s", len(photos), session_id)
        return await _ask_phone(update, context)
    
    # Any other text during photo phase
    if lang == 'ee':
        msg = "Palun saatke foto või vajutage 'Valmis'."
    elif lang == 'ru':
        msg = "Пожалуйста, отправьте фото или нажмите 'Готово'."
    else:
        msg = "Please send a photo or tap 'Done'."

    await update.message.reply_text(msg, reply_markup=_done_keyboard(lang))
    return PHOTOS

async def photo_collection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle photo uploads with session-based storage and concurrency safety"""
    import uuid
    from database.models import save_session_photo
    
    # Generate or get session ID with user isolation
    if 'session_id' not in context.user_data:
        context.user_data['session_id'] = str(uuid.uuid4())
        context.user_data['photo_count'] = 0
        logger.info("Created session %s for user %s", context.user_data['session_id'], update.effective_user.id)

    session_id = context.user_data['session_id']
    user_id = update.effective_user.id
    lang = context.user_data.get('language')

    file = None
    if update.message.photo:
        # Get highest resolution photo (last in array)
        file = await update.message.photo[-1].get_file()
        logger.info("Got photo file_id: %s", file.file_id)
    elif update.message.document and (update.message.document.mime_type or "").startswith("image/"):
        file = await update.message.document.get_file()
        logger.info("Got document file_id: %s", file.file_id)
    else:
        if lang == 'ee':
            msg = "Palun saatke foto (pilt) või vajutage 'Valmis'."
        elif lang == 'ru':
            msg = "Пожалуйста, отправьте фото (картинку) или нажмите 'Готово'."
        else:
            msg = "Please send a photo (image) or tap 'Done'."
        await update.message.reply_text(msg, reply_markup=_done_keyboard(lang))
        return PHOTOS
    
    # Save to session-based storage with concurrency safety
    try:
        save_session_photo(user_id, session_id, file.file_id)
        context.user_data['photo_count'] += 1
        logger.info("Saved photo to session %s, total photos: %d", session_id, context.user_data['photo_count'])
    except Exception as e:
        logger.error("Failed to save photo: %s", e)
        if lang == 'ee':
            msg = "Viga foto salvestamisel. Palun proovige uuesti."
        elif lang == 'ru':
            msg = "Ошибка сохранения фото. Пожалуйста, попробуйте еще раз."
        else:
            msg = "Error saving photo. Please try again."
        await update.message.reply_text(msg, reply_markup=_done_keyboard(lang))
        return PHOTOS

    count = context.user_data['photo_count']
    
    # Check if reached 5-photo limit
    if count >= 5:
        if lang == 'ee':
            msg = f"Maksimum 5 fotot saadetud. Vajutage 'Valmis', et jätkata."
        elif lang == 'ru':
            msg = f"Отправлено максимум 5 фото. Нажмите 'Готово' для продолжения."
        else:
            msg = f"Maximum 5 photos sent. Tap 'Done' to continue."
        await update.message.reply_text(msg, reply_markup=_done_keyboard(lang))
        return PHOTOS
    
    # Normal response
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
