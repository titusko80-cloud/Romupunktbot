"""
Logistics handlers - Transport selection and tow details
"""

from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, KeyboardButton
from telegram.ext import ContextTypes
from states import LOGISTICS, LOCATION, PHOTOS
import logging

logger = logging.getLogger(__name__)

def _valmis_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup([[KeyboardButton("✅ Valmis")]], resize_keyboard=True, is_persistent=False)


async def show_logistics(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = context.user_data.get('language')

    if lang == 'ee':
        self_btn = "🚗 Toon ise"
        tow_btn = "🚛 Vajan buksiiri"
        msg = "Kuidas soovite sõiduki transportida?"
    elif lang == 'ru':
        self_btn = "🚗 Привезу сам"
        tow_btn = "🚛 Нужен эвакуатор"
        msg = "Как вы хотите доставить автомобиль?"
    else:
        self_btn = "🚗 Bring myself"
        tow_btn = "🚛 Need tow"
        msg = "How would you like to transport the vehicle?"

    reply_markup = ReplyKeyboardMarkup(
        [[KeyboardButton(self_btn)], [KeyboardButton(tow_btn)]],
        resize_keyboard=True,
        is_persistent=False,
    )
    await update.message.reply_text(msg, reply_markup=reply_markup)
    return LOGISTICS


async def logistics_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    choice = (update.message.text or '').strip()
    lang = context.user_data.get('language')

    if lang == 'ee':
        self_btn = "🚗 Toon ise"
        tow_btn = "🚛 Vajan buksiiri"
    elif lang == 'ru':
        self_btn = "🚗 Привезу сам"
        tow_btn = "🚛 Нужен эвакуатор"
    else:
        self_btn = "🚗 Bring myself"
        tow_btn = "🚛 Need tow"

    if choice not in (self_btn, tow_btn):
        return await show_logistics(update, context)

    if not context.user_data.get("session_id"):
        from uuid import uuid4
        context.user_data["session_id"] = uuid4().hex
        context.user_data["photo_count"] = 0

    context.user_data["transport_method"] = choice

    if choice == tow_btn:
        context.user_data["needs_tow"] = True
        await update.message.reply_text(
            "📍 Palun kirjuta aadress, kust auto tuleb ära tuua.",
            reply_markup=ReplyKeyboardRemove(),
        )
        return LOCATION

    context.user_data["needs_tow"] = False
    await update.message.reply_text(
        "📸 Laadi nüüd auto pildid üles.\nKui valmis, vajuta ✅ Valmis.",
        reply_markup=_valmis_keyboard(),
    )
    return PHOTOS


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

    if not context.user_data.get("session_id"):
        from uuid import uuid4
        context.user_data["session_id"] = uuid4().hex
        context.user_data["photo_count"] = 0

    await update.message.reply_text(
        "📸 Palun laadi üles auto pildid (võid saada mitu korraga).\nKui valmis, vajuta ✅ Valmis.",
        reply_markup=_valmis_keyboard(),
    )

    return PHOTOS
