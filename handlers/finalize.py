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
from database.models import save_lead, get_lead_photos, get_lead_by_id, move_session_photos_to_lead
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
    """Accept direct phone number input without country code picker"""
    
    # B2 RULE: Phone number normalization (server-side, once)
    phone_raw = update.message.text.strip()
    logger.info("phone_number received: %s", phone_raw)

    lang = context.user_data.get("language", "en")

    if phone_raw.startswith("✅"):
        if lang == "ee":
            await update.message.reply_text("📞 Palun sisesta oma telefoninumber (näiteks 51234567).")
        elif lang == "ru":
            await update.message.reply_text("📞 Пожалуйста, отправьте номер телефона (например 51234567).")
        else:
            await update.message.reply_text("📞 Please send your phone number (example 51234567).")
        return PHONE
    
    # Remove all non-digit characters
    digits_only = re.sub(r'[^\d]', '', phone_raw)
    
    # Validate phone number (5-15 digits)
    if len(digits_only) < 5 or len(digits_only) > 15:
        if lang == "ee":
            await update.message.reply_text("Palun sisestage kehtiv telefoninumber (5-15 numbrit).")
        elif lang == "ru":
            await update.message.reply_text("Пожалуйста, введите действительный номер телефона (5-15 цифр).")
        else:
            await update.message.reply_text("Please enter a valid phone number (5-15 digits).")
        return PHONE
    
    # Store the raw phone number as provided by user
    context.user_data["phone_number"] = phone_raw
    logger.info("phone_number set to: %s", phone_raw)
    
    # Check if we have session photos
    session_id = context.user_data.get('session_id')
    if session_id:
        from database.models import get_session_photos, move_session_photos_to_lead
        user_id = update.effective_user.id
        photos = get_session_photos(user_id, session_id)
        
        # Create lead with all data
        logger.info("Creating lead with %d session photos", len(photos))
        user = update.effective_user
        lead_id = save_lead(context.user_data, user.id, getattr(user, "username", None))
        
        # Move photos from session to permanent storage BEFORE notification
        move_session_photos_to_lead(user_id, session_id, lead_id)
        
        # 🔴 STEP 4 - HARD FAIL IF PHOTOS ARE ZERO
        photos = get_lead_photos(lead_id)
        if not photos:
            raise RuntimeError("FATAL: Lead finalized without photos")
        
        logger.info("ATTACHED %d PHOTOS to lead %d", len(photos), lead_id)
        
        # CRITICAL: Send live Lead Card to admin IMMEDIATELY after database commit
        logger.info("Triggering live admin notification for lead %d", lead_id)
        await send_lead_card(context, lead_id, phone_raw)
        
        if context.user_data.get("language") == "ee":
            msg = "Aitäh! Võtame teiega ühendust pakkumisega."
        elif context.user_data.get("language") == "ru":
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
    
    # CRITICAL: Send live Lead Card to admin IMMEDIATELY after database commit
    logger.info("Triggering live admin notification for lead %d (no photos)", lead_id)
    
    await send_lead_card(context, lead_id, phone_raw)

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
    """Send professional Lead Card with media group and rich HTML caption"""
    # 🔥 DEBUG: Find the real file
    import inspect
    logger.error("🔥 ADMIN NOTIFIER FILE: %s", inspect.getfile(inspect.currentframe()))
    
    # 🔥🔥🔥 send_lead_card ACTIVE — THIS MUST APPEAR 🔥🔥🔥
    logger.error("🔥🔥🔥 send_lead_card ACTIVE — THIS MUST APPEAR 🔥🔥🔥")
    print("🔥🔥🔥 send_lead_card ACTIVE — THIS MUST APPEAR 🔥🔥🔥")
    
    if not ADMIN_TELEGRAM_USER_ID or ADMIN_TELEGRAM_USER_ID <= 0:
        logger.warning("ADMIN_TELEGRAM_USER_ID not set or invalid")
        return
    
    lead = get_lead_by_id(lead_id)
    if not lead:
        logger.error("Lead %d not found for admin notification", lead_id)
        return
    
    # 🔴 PATCH 1: Define lang (BLOCKER #1 FIXED)
    lang = lead.get("language") or "en"
    
    # 🔴 REQUIRED: Load photos for this lead
    photos = get_lead_photos(lead_id)
    logger.info(f"📸 DEBUG: Retrieved {len(photos)} photos for lead {lead_id}")
    
    # Debug: Log photo file_ids
    if photos:
        for i, photo in enumerate(photos):
            logger.info(f"📸 DEBUG: Photo {i+1}: {photo['file_id']}")
    else:
        logger.warning(f"📸 DEBUG: No photos found for lead {lead_id}")
    
    # Build inquiry form with HTML formatting
    if lang == "ee":
        title = f"<b>🏎️ Päring #{lead_id}</b>"
        labels = {"plate": "Number", "name": "Nimi", "phone": "Telefon", "weight": "Mass", "owner": "Omanik"}
    elif lang == "ru":
        title = f"<b>🏎️ Заявка #{lead_id}</b>"
        labels = {"plate": "Номер", "name": "Имя", "phone": "Телефон", "weight": "Масса", "owner": "Владелец"}
    else:
        title = f"<b>🏎️ Inquiry #{lead_id}</b>"
        labels = {"plate": "Plate", "name": "Name", "phone": "Phone", "weight": "Weight", "owner": "Owner"}
    
    # 🔴 PATCH 2: Fix phone rendering (BLOCKER #2 FIXED)
    readable_phone = phone_number
    
    # Build inquiry form caption with plain text phone (B3 rule)
    caption_lines = [
        title,
        "",
        f"<b>📋 {labels['plate']}:</b> <code>{lead.get('plate_number')}</code>",
        f"<b>👤 {labels['name']}:</b> {lead.get('owner_name')}",
        f"<b>📞 {labels['phone']}:</b> {readable_phone}",
        f"<b>⚖️ {labels['weight']}:</b> {lead.get('curb_weight')}kg",
    ]
    
    # Add owner status
    is_owner = lead.get('is_owner')
    if is_owner is not None:
        owner_status = "Jah" if int(is_owner) == 1 else "Ei"
        if lang == "ru":
            owner_status = "Да" if int(is_owner) == 1 else "Нет"
        elif lang == "en":
            owner_status = "Yes" if int(is_owner) == 1 else "No"
        caption_lines.append(f"<b>🔑 {labels['owner']}:</b> {owner_status}")
    
    # Add completeness if available
    completeness = lead.get('completeness')
    if completeness:
        if completeness == "complete":
            comp_text = "✅ Täielik" if lang == "ee" else "✅ Полный" if lang == "ru" else "✅ Complete"
        else:
            comp_text = "❌ Puudub" if lang == "ee" else "❌ Не полный" if lang == "ru" else "❌ Missing parts"
        caption_lines.append(f"<b>🔧 Komplektsus:</b> {comp_text}")
    
    # Add transport info
    transport = lead.get('transport_method')
    if transport:
        caption_lines.append(f"<b>🚚 Transport:</b> {transport}")
    
    # Add photo count
    caption_lines.append(f"<b>📷 Photos:</b> {len(photos)}")
    
    caption = "\n".join(caption_lines)
    
    # 🔴 REQUIRED: Build media group exactly as specified
    if photos:
        media = []
        for i, photo_dict in enumerate(photos):
            # 🔴 PATCH 3: Safe photo access (BLOCKER #3 FIXED)
            file_id = photo_dict["file_id"] if isinstance(photo_dict, dict) else photo_dict[0]
            logger.info(f"📸 CRITICAL: Processing photo {i+1}/{len(photos)}: {file_id}")
            
            if i == 0:
                # First photo gets caption
                logger.info(f"📸 CRITICAL: Adding photo {i+1} with caption")
                media.append(
                    InputMediaPhoto(
                        media=file_id,
                        caption=caption,
                        parse_mode="HTML"
                    )
                )
            else:
                # Remaining photos without caption
                logger.info(f"📸 CRITICAL: Adding photo {i+1} without caption")
                media.append(InputMediaPhoto(media=file_id))
        
        logger.info(f"📸 CRITICAL: Media group built with {len(media)} items")
        
        # 🔴 REQUIRED: Send the album to admin
        try:
            logger.info(f"📸 CRITICAL: Sending media group to admin {ADMIN_TELEGRAM_USER_ID}")
            await context.bot.send_media_group(
                chat_id=ADMIN_TELEGRAM_USER_ID,
                media=media
            )
            logger.info(f"✅ SUCCESS: Media group sent with {len(photos)} photos for lead {lead_id}")
        except Exception as e:
            logger.error(f"❌ FAILED: Media group failed for lead {lead_id}: {e}")
            logger.info(f"📸 FALLBACK: Sending text message instead")
            await context.bot.send_message(
                chat_id=ADMIN_TELEGRAM_USER_ID,
                text=caption,
                parse_mode="HTML"
            )
    else:
        # No photos, send text-only inquiry form
        logger.info(f"📸 NO PHOTOS: Sending text-only inquiry form for lead {lead_id}")
        await context.bot.send_message(
            chat_id=ADMIN_TELEGRAM_USER_ID,
            text=caption,
            parse_mode="HTML"
        )
    
    # B4 RULE: Admin actions with plain text phone and correct buttons
    logger.info(f"📸 CRITICAL: Sending action buttons as separate message for lead {lead_id}")
    reply_markup = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("💬 Vasta pakkumisega", callback_data=f"reply:{lead_id}"),
            InlineKeyboardButton("🗑 Arhiveeri", callback_data=f"archive:{lead_id}"),
        ]
    ])
    
    await context.bot.send_message(
        chat_id=ADMIN_TELEGRAM_USER_ID,
        text=f"📞 Telefon: {readable_phone}",
        reply_markup=reply_markup
    )
    logger.info(f"✅ SUCCESS: Action buttons sent for lead {lead_id}")

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
