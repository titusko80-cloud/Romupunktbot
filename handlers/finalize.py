"""Finalization handler - phone number collection and lead persistence."""

import logging
import re
from typing import Optional
from pathlib import Path
from telegram import Update, InputMediaPhoto
from telegram.ext import ContextTypes, ConversationHandler
from telegram import ReplyKeyboardMarkup, KeyboardButton
from telegram import InlineKeyboardMarkup, InlineKeyboardButton

from config import ADMIN_TELEGRAM_USER_ID
from database.models import save_lead, get_lead_photos, get_lead_by_id
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
    # Remove @ if present
    bot_username = bot_username.lstrip('@')
    share_url = f"https://t.me/share?url=https://t.me/{bot_username}"
    if lang == "ee":
        msg = f"Teada sõpru, kellel on vana auto romu hoovis! Saada neile kiirelt link:\nhttps://t.me/{bot_username}"
        btn_text = "🔗 Jagada Telegramis"
    elif lang == "ru":
        msg = f"Расскажи друзьям, у которых старая машина на разборку! Быстро отправь им ссылку:\nhttps://t.me/{bot_username}"
        btn_text = "🔗 Поделиться в Telegram"
    else:
        msg = f"Tell friends who have an old car to scrap! Send them the link quick:\nhttps://t.me/{bot_username}"
        btn_text = "🔗 Share on Telegram"
    try:
        await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(btn_text, url=share_url)]]))
    except Exception:
        # Fallback: just send the link without the share button
        await update.message.reply_text(msg)

def _phone_keyboard(lang: str) -> ReplyKeyboardMarkup:
    if lang == "ee":
        keyboard = [
            [KeyboardButton("🇪🇪 +372"), KeyboardButton("🇫🇮 +358"), KeyboardButton("🇱🇻 +371")],
            [KeyboardButton("🇷🇺 +7"), KeyboardButton("🇱🇹 +370"), KeyboardButton("🇸🇪 +46")],
        ]
        prompt = "Vali riigi kood:"
    elif lang == "ru":
        keyboard = [
            [KeyboardButton("🇪🇪 +372"), KeyboardButton("🇫🇮 +358"), KeyboardButton("🇱🇻 +371")],
            [KeyboardButton("🇷🇺 +7"), KeyboardButton("🇱🇹 +370"), KeyboardButton("🇸🇪 +46")],
        ]
        prompt = "Выберите код страны:"
    else:
        keyboard = [
            [KeyboardButton("🇪🇪 +372"), KeyboardButton("🇫🇮 +358"), KeyboardButton("🇱🇻 +371")],
            [KeyboardButton("🇷🇺 +7"), KeyboardButton("🇱🇹 +370"), KeyboardButton("🇸🇪 +46")],
        ]
        prompt = "Choose country code:"
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, is_persistent=True), prompt

async def phone_number(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # First time: show country picker
    if "phone_country_code" not in context.user_data:
        keyboard, prompt = _phone_keyboard(context.user_data.get("language", "en"))
        await update.message.reply_text(prompt, reply_markup=keyboard)
        return PHONE

    # B2 RULE: Phone number normalization (server-side, once)
    phone_raw = update.message.text.strip()
    country_code = context.user_data.get("phone_country_code", "")
    
    # Strip spaces and symbols
    clean_phone = re.sub(r'[\s\-\(\)]', '', phone_raw)
    
    # Normalization logic
    if clean_phone.startswith("+"):
        full_phone = clean_phone  # Keep existing + format
    elif clean_phone.startswith("372"):
        full_phone = f"+{clean_phone}"  # Add + to 372
    elif len(clean_phone) >= 7 and len(clean_phone) <= 8 and clean_phone.isdigit():
        full_phone = f"+372{clean_phone}"  # Add +372 to short numbers
    else:
        # Reject invalid format
        logger.warning("Phone validation failed for %s", clean_phone)
        if context.user_data.get("language") == "ee":
            msg = "Palun sisestage korrektne number (näiteks 53504299 või +37253504299):"
        elif context.user_data.get("language") == "ru":
            msg = "Введите корректный номер (например 53504299 или +37253504299):"
        else:
            msg = "Please enter a valid number (example 53504299 or +37253504299):"
        await update.message.reply_text(msg, reply_markup=_new_inquiry_keyboard(context.user_data.get("language")))
        return PHONE
    
    logger.info("phone_number received: %s, full_phone: %s", phone_raw, full_phone)

    # Save phone number to context
    context.user_data["phone_number"] = full_phone
    logger.info("phone_number set to: %s", full_phone)

    # Check if we have session photos
    session_id = context.user_data.get('session_id')
    if session_id:
        from database.models import get_session_photos, move_session_photos_to_lead
        user_id = update.effective_user.id
        photos = get_session_photos(user_id, session_id)
        
        if photos:
            # Create lead with all data
            logger.info("Creating lead with %d session photos", len(photos))
            user = update.effective_user
            lead_id = save_lead(context.user_data, user.id, getattr(user, "username", None))
            
            # CRITICAL: Move photos from session to permanent storage BEFORE notification
            move_session_photos_to_lead(user_id, session_id, lead_id)
            
            # CRITICAL: Send live Lead Card to admin IMMEDIATELY after database commit
            logger.info("Triggering live admin notification for lead %d", lead_id)
            await send_lead_card(context, lead_id, full_phone)
            
            # Send thank you message
            lang = context.user_data.get("language")
            if lang == "ee":
                msg = "Aitäh! Võtame teiega ühendust pakkumisega."
            elif lang == "ru":
                msg = "Спасибо! Мы свяжемся с вами с предложением."
            else:
                msg = "Thank you! We'll contact you with an offer."
            
            await update.message.reply_text(msg, reply_markup=_new_inquiry_keyboard(lang))
            context.user_data.clear()
            return ConversationHandler.END

    # No photos, create lead now
    user = update.effective_user
    lead_id = save_lead(context.user_data, user.id, getattr(user, "username", None))
    context.user_data["lead_id"] = lead_id
    logger.info("Saved lead with ID %s for user %s", lead_id, user.id)

    # Send admin notification using the fixed send_lead_card function
    await send_lead_card(context, lead_id, full_phone)

    if context.user_data.get("language") == "ee":
        msg = "Aitäh! Võtame teiega ühendust pakkumisega."
    elif context.user_data.get("language") == "ru":
        msg = "Спасибо! Мы свяжемся с вами с предложением."
    else:
        msg = "Thank you! We'll contact you with an offer."

    await update.message.reply_text(msg, reply_markup=_new_inquiry_keyboard(context.user_data.get("language", "en")))
    context.user_data.clear()
    return ConversationHandler.END

async def send_lead_card(context: ContextTypes.DEFAULT_TYPE, lead_id: int, phone_number: str) -> None:
    """Send professional Lead Card with media group and compact layout"""
    if not ADMIN_TELEGRAM_USER_ID or ADMIN_TELEGRAM_USER_ID <= 0:
        logger.warning("ADMIN_TELEGRAM_USER_ID not set or invalid")
        return
    
    lead = get_lead_by_id(lead_id)
    if not lead:
        logger.error("Lead %d not found for admin notification", lead_id)
        return
    
    # Get user language from lead data
    lang = lead.get("language") or "en"
    
    # Load photos for this lead (max 5)
    photos = get_lead_photos(lead_id)
    photos = photos[:5]  # Enforce max 5 photos
    logger.info(f"MEDIA_GROUP_SENT lead_id={lead_id} photos={len(photos)}")
    
    # Language-specific labels
    LABELS = {
        "et": {
            "number": "Number",
            "name": "Nimi",
            "phone": "Telefon",
            "owner": "Omanik",
            "delivery": "Transport"
        },
        "ru": {
            "number": "Номер",
            "name": "Имя",
            "phone": "Телефон",
            "owner": "Владелец",
            "delivery": "Доставка"
        },
        "en": {
            "number": "Plate",
            "name": "Name",
            "phone": "Phone",
            "owner": "Owner",
            "delivery": "Delivery"
        }
    }
    
    labels = LABELS.get(lang, LABELS["en"])
    
    # Build compact caption (no emojis spam, one glance = decision)
    caption_lines = [
        f"🚗 Lead #{lead_id}",
        f"{labels['number']}: {lead.get('plate_number')}",
    ]
    
    # Owner status (always show)
    is_owner = lead.get('is_owner')
    if is_owner is not None:
        owner_status = "Yes" if int(is_owner) == 1 else "No"
        if lang == "et":
            owner_status = "Jah" if int(is_owner) == 1 else "Ei"
        elif lang == "ru":
            owner_status = "Да" if int(is_owner) == 1 else "Нет"
        caption_lines.append(f"{labels['owner']}: {owner_status}")
    
    caption_lines.extend([
        f"{labels['phone']}: {phone_number}",
    ])
    
    # Delivery method (always show)
    transport = lead.get('transport_method')
    needs_tow = lead.get('needs_tow')
    
    if transport:
        if lang == "et":
            delivery_text = "Toon ise" if "bring" in transport.lower() else "Vajab buksüüri"
        elif lang == "ru":
            delivery_text = "Привезу сам" if "bring" in transport.lower() else "Нужен эвакуатор"
        else:
            delivery_text = "Will bring" if "bring" in transport.lower() else "Tow needed"
        caption_lines.append(f"{labels['delivery']}: {delivery_text}")
    elif needs_tow is not None:
        if int(needs_tow) == 1:
            if lang == "et":
                delivery_text = "Vajab buksüüri"
            elif lang == "ru":
                delivery_text = "Нужен эвакуатор"
            else:
                delivery_text = "Tow needed"
        else:
            if lang == "et":
                delivery_text = "Toon ise"
            elif lang == "ru":
                delivery_text = "Привезу сам"
            else:
                delivery_text = "Will bring"
        caption_lines.append(f"{labels['delivery']}: {delivery_text}")
    
    caption = "\n".join(caption_lines)
    
    # Send media group with photos only (caption on first photo)
    if photos:
        media = []
        for i, photo_dict in enumerate(photos):
            file_id = photo_dict["file_id"] if isinstance(photo_dict, dict) else photo_dict[0]
            
            if i == 0:
                # First photo gets caption
                media.append(InputMediaPhoto(media=file_id, caption=caption))
            else:
                # Remaining photos without caption
                media.append(InputMediaPhoto(media=file_id))
        
        # Send media group
        await context.bot.send_media_group(
            chat_id=ADMIN_TELEGRAM_USER_ID,
            media=media
        )
        logger.info(f"MEDIA_GROUP_SENT lead_id={lead_id} photos={len(photos)}")
    else:
        # No photos, send text message
        await context.bot.send_message(
            chat_id=ADMIN_TELEGRAM_USER_ID,
            text=caption
        )
    
    # Send buttons as separate message (NEVER in media caption)
    from telegram import InlineKeyboardMarkup, InlineKeyboardButton
    reply_markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("💬 Reply", callback_data=f"admin_reply:{lead_id}")],
        [InlineKeyboardButton("🗑️ Archive", callback_data=f"admin_archive:{lead_id}")]
    ])
    
    await context.bot.send_message(
        chat_id=ADMIN_TELEGRAM_USER_ID,
        text=f"Actions for lead #{lead_id}:",
        reply_markup=reply_markup
    )

async def phone_country_code(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    choice = update.message.text.strip()
    logger.info("phone_country_code received: %s", choice)
    # Extract country code from button text
    match = re.search(r"\+([0-9]+)", choice)
    if not match:
        if context.user_data.get("language") == "ee":
            msg = "Palun vali riigi kood nuppudest."
        elif context.user_data.get("language") == "ru":
            msg = "Пожалуйста, выберите код страны из кнопок."
        else:
            msg = "Please choose a country code from the buttons."
        keyboard, _ = _phone_keyboard(context.user_data.get("language", "en"))
        await update.message.reply_text(msg, reply_markup=keyboard)
        return PHONE

    country_code = "+" + match.group(1)
    context.user_data["phone_country_code"] = country_code
    logger.info("phone_country_code set to: %s", country_code)

    if context.user_data.get("language") == "ee":
        msg = f"Riikikood {country_code} valitud. Nüüd sisestage kohalik number (näiteks 51234567):"
    elif context.user_data.get("language") == "ru":
        msg = f"Код страны {country_code} выбран. Теперь введите местный номер (например 51234567):"
    else:
        msg = f"Country code {country_code} selected. Now enter your local number (example 51234567):"

    await update.message.reply_text(msg)
    return PHONE
