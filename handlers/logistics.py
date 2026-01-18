"""
Logistics handlers - Transport selection and tow details
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove, KeyboardButton
from telegram.ext import ContextTypes, CallbackQueryHandler
from states import LOGISTICS, LOCATION, PHOTOS
import logging
from handlers.photos import _done_keyboard

logger = logging.getLogger(__name__)

async def logistics_selection_final(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    # TASK 1 - HARD UI RESET
    context.user_data.clear()
    from uuid import uuid4
    context.user_data["session_id"] = uuid4().hex
    context.user_data["photo_count"] = 0

    # Remove inline keyboard and show ONLY [✅ Valmis] button
    await query.edit_message_reply_markup(None)
    await context.bot.send_message(
        chat_id=query.message.chat_id,
        text="📸 Laadi nüüd auto pildid üles.\nKui valmis, vajuta [✅ Valmis].",
        reply_markup=ReplyKeyboardMarkup([['✅ Valmis']], resize_keyboard=True)
    )

    # TASK 7 - KILL LOCATION PATH IF NOT TOW
    if query.data == "LOGISTICS_TOW":
        context.user_data["needs_tow"] = True
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="📍 Palun kirjuta aadress, kust auto tuleb ära tuua."
        )
        return LOCATION

    # 🚗 TOON ISE → STRAIGHT TO PHOTOS
    context.user_data["needs_tow"] = False
    return PHOTOS


async def show_logistics_inline(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show logistics options as inline keyboard"""
    lang = context.user_data.get('language')
    
    # TASK 1 - FIX THE STICKY BUTTONS (UI)
    # Remove any existing ReplyKeyboard before showing inline keyboard
    await update.message.reply_text(" ", reply_markup=ReplyKeyboardRemove())
    
    if lang == 'ee':
        keyboard = [
            [InlineKeyboardButton("🚗 Toon ise", callback_data="LOGISTICS_SELF")],
            [InlineKeyboardButton("🚛 Vajan buksiiri", callback_data="LOGISTICS_TOW")]
        ]
        msg = "Kuidas soovite sõiduki transportida?"
    elif lang == 'ru':
        keyboard = [
            [InlineKeyboardButton("🚗 Привезу сам", callback_data="LOGISTICS_SELF")],
            [InlineKeyboardButton("🚛 Нужен эвакуатор", callback_data="LOGISTICS_TOW")]
        ]
        msg = "Как вы хотите доставить автомобиль?"
    else:
        keyboard = [
            [InlineKeyboardButton("🚗 Bring myself", callback_data="LOGISTICS_SELF")],
            [InlineKeyboardButton("🚛 Need tow", callback_data="LOGISTICS_TOW")]
        ]
        msg = "How would you like to transport the vehicle?"
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(msg, reply_markup=reply_markup)
    return LOGISTICS


async def location_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Store tow address (text) then move to photo collection."""
    logger.info("location_received: user_id=%s", update.effective_user.id)
    if update.message.location is not None:
        context.user_data['location'] = {
            'latitude': update.message.location.latitude,
            'longitude': update.message.location.longitude,
        }
        context.user_data['tow_address'] = f"{update.message.location.latitude}, {update.message.location.longitude}"
    else:
        context.user_data['tow_address'] = (update.message.text or '').strip()

    # Create session for photos
    from uuid import uuid4
    context.user_data["session_id"] = uuid4().hex
    context.user_data["photo_count"] = 0

    await update.message.reply_text(
        "📸 Palun laadi üles auto pildid (võid saada mitu korraga)."
    )

    return PHOTOS
