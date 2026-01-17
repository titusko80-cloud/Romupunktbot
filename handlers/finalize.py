"""Finalization handler - phone number collection and lead persistence."""

import logging
import re
from typing import Optional
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

from pathlib import Path
from telegram import InputMediaPhoto
from telegram import ReplyKeyboardMarkup, KeyboardButton
from telegram import InlineKeyboardMarkup, InlineKeyboardButton

from config import ADMIN_TELEGRAM_USER_ID
from database.models import save_lead
from states import PHONE


_BASE_DIR = Path(__file__).resolve().parent.parent
logger = logging.getLogger(__name__)


def _thank_you_message(lang: str) -> str:
    if lang == "ee":
        return (
            "Aitäh! Saime andmed kätte ja helistame teile kiirelt tagasi pakkumisega.\n\n"
            "Me vormistame ka lammutustõendi ja aitame sõiduki registrist eemaldamisega."
        )
    if lang == "ru":
        return (
            "Спасибо! Мы получили данные и быстро перезвоним вам с предложением.\n\n"
            "Мы также оформляем справку об утилизации и помогаем снять автомобиль с учёта."
        )
    return (
        "Thank you! We received your details and will call you back quickly with an offer.\n\n"
        "We also handle the certificate of destruction and deregistration paperwork."
    )

def _share_keyboard(lang: str) -> ReplyKeyboardMarkup:
    if lang == "ee":
        share_text = "🔗 Jaga sõbraga, kellel on romu hoovis"
    elif lang == "ru":
        share_text = "🔗 Поделись с другом, у которого машина на разборку"
    else:
        share_text = "🔗 Share with a friend who's scrapping a car"
    return ReplyKeyboardMarkup([[KeyboardButton(share_text)]], resize_keyboard=True, is_persistent=True)


def _display_completeness(lang: str, completeness: Optional[str]) -> Optional[str]:
    if completeness is None:
        return None

    if completeness in ("complete", "missing"):
        if lang == "ee":
            return "✅ Täielik" if completeness == "complete" else "❌ Puudub"
        if lang == "ru":
            return "✅ Полный" if completeness == "complete" else "❌ Не полный"
        return "✅ Complete" if completeness == "complete" else "❌ Missing parts"

    return completeness


def _yes_no(lang: str, val: Optional[bool]) -> Optional[str]:
    if val is None:
        return None
    if lang == "ee":
        return "Jah" if val else "Ei"
    if lang == "ru":
        return "Да" if val else "Нет"
    return "Yes" if val else "No"


def _new_inquiry_keyboard(lang: str) -> ReplyKeyboardMarkup:
    if lang == "ee":
        text = "🔄 Uus päring"
    elif lang == "ru":
        text = "🔄 Новая заявка"
    else:
        text = "🔄 New inquiry"
    return ReplyKeyboardMarkup([[KeyboardButton(text)]], resize_keyboard=True, is_persistent=True)


def _normalize_phone(phone_raw: str) -> Optional[str]:
    phone = phone_raw.strip().replace(" ", "")
    if phone.startswith("00"):
        phone = "+" + phone[2:]
    # Accept any international format (+country code) or plain number, 7-15 digits
    if re.fullmatch(r"\+?[0-9]{7,15}", phone):
        return phone
    return None


async def handle_share_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    lang = context.user_data.get('language', 'en')
    bot_username = (context.bot.username or "")
    if not bot_username:
        await update.message.reply_text("Bot username not available.")
        return
    share_url = f"https://t.me/share?url=https://t.me/{bot_username}"
    if lang == "ee":
        msg = "Teada sõpru, kellel on vana auto romu hoovis! Saada neile kiirelt link."
        btn_text = "🔗 Saada link"
    elif lang == "ru":
        msg = "Расскажи друзьям, у которых старая машина на разборку! Быстро отправь им ссылку."
        btn_text = "🔗 Отправить ссылку"
    else:
        msg = "Tell friends who have an old car to scrap! Send them the link quick."
        btn_text = "🔗 Send link"
    await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(btn_text, url=share_url)]]))

async def phone_number(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    phone_raw = update.message.text
    phone = _normalize_phone(phone_raw)

    if phone is None:
        if context.user_data.get("language") == "ee":
            msg = "Palun sisestage korrektne telefoninumber (näiteks +3725xxxxxxx või 5xxxxxxx):"
        elif context.user_data.get("language") == "ru":
            msg = "Введите корректный номер телефона (например +3725xxxxxxx или 5xxxxxxx):"
        else:
            msg = "Please enter a valid phone number (example +3725xxxxxxx or 5xxxxxxx):"

        await update.message.reply_text(msg, reply_markup=_new_inquiry_keyboard(context.user_data.get("language")))
        return PHONE

    context.user_data["phone_number"] = phone

    if context.user_data.get("lead_id") is not None:
        lang = context.user_data.get("language")
        await update.message.reply_text(_thank_you_message(lang), reply_markup=_new_inquiry_keyboard(lang))
        context.user_data.clear()
        return ConversationHandler.END

    user = update.effective_user
    lead_id = save_lead(context.user_data, user.id, getattr(user, "username", None))
    context.user_data["lead_id"] = lead_id
    logger.info("Saved lead with ID %s for user %s", lead_id, user.id)

    if ADMIN_TELEGRAM_USER_ID and ADMIN_TELEGRAM_USER_ID > 0:
        logger.info("Attempting to send admin notification for lead %s. ADMIN_TELEGRAM_USER_ID=%s", lead_id, ADMIN_TELEGRAM_USER_ID)
        
        # 🔥 FIX: Use send_media_group instead of sendMessage
        try:
            from database.models import get_lead_photos
            photos = get_lead_photos(lead_id)
        except Exception as e:
            logger.exception("FAILED loading lead photos")
            photos = []
        
        # Build caption
        plate = context.user_data.get("plate_number")
        name = context.user_data.get("owner_name")
        weight = context.user_data.get("curb_weight")
        phone = context.user_data.get("phone_number")
        lang = context.user_data.get("language")
        
        if lang == "ee":
            title = f"🏎️ Päring #{lead_id}"
        elif lang == "ru":
            title = f"🏎️ Заявка #{lead_id}"
        else:
            title = f"🏎️ Inquiry #{lead_id}"
        
        caption_lines = [
            title,
            "",
            f"📋 Number: {plate}",
            f"👤 Name: {name}",
            f"📞 Phone: {phone}",
            f"⚖️ Weight: {weight}kg",
            f"📷 Photos: {len(photos)}",
        ]
        
        caption = "\n".join(caption_lines)
        
        # Build media group
        if photos:
            from telegram import InputMediaPhoto
            media = []
            for i, photo_dict in enumerate(photos):
                file_id = photo_dict["file_id"] if isinstance(photo_dict, dict) else photo_dict[0]
                if i == 0:
                    media.append(InputMediaPhoto(media=file_id, caption=caption, parse_mode="HTML"))
                else:
                    media.append(InputMediaPhoto(media=file_id))
            
            # Send media group
            await context.bot.send_media_group(
                chat_id=ADMIN_TELEGRAM_USER_ID,
                media=media
            )
            logger.info(f"✅ SUCCESS: Media group sent with {len(photos)} photos for lead {lead_id}")
        else:
            # No photos, send text message
            await context.bot.send_message(
                chat_id=ADMIN_TELEGRAM_USER_ID,
                text=caption,
                parse_mode="HTML"
            )
        
        # Send buttons as second message
        from telegram import InlineKeyboardMarkup, InlineKeyboardButton
        reply_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("💬 Vasta pakkumisega", callback_data=f"admin_reply:{lead_id}")],
            [InlineKeyboardButton("🗑️ Arhiveeri", callback_data=f"admin_archive:{lead_id}")]
        ])
        
        await context.bot.send_message(
            chat_id=ADMIN_TELEGRAM_USER_ID,
            text=f"🎯 Actions for lead #{lead_id}:",
            reply_markup=reply_markup
        )
        
        logger.info("Admin notification sent for lead %s", lead_id)
    else:
        logger.warning("ADMIN_TELEGRAM_USER_ID is not set or <=0 (value=%s); skipping admin notification for lead %s", ADMIN_TELEGRAM_USER_ID, lead_id)

    if context.user_data.get("language") == "ee":
        msg = _thank_you_message("ee")
    elif context.user_data.get("language") == "ru":
        msg = _thank_you_message("ru")
    else:
        msg = _thank_you_message("en")

    await update.message.reply_text(msg, reply_markup=_share_keyboard(context.user_data.get("language", "en")))

    context.user_data.clear()

    return ConversationHandler.END
