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
        plate = context.user_data.get("plate_number")
        name = context.user_data.get("owner_name")
        weight = context.user_data.get("curb_weight")
        lang = context.user_data.get("language")
        completeness = _display_completeness(lang, context.user_data.get("completeness"))
        is_owner = context.user_data.get("is_owner")
        missing_parts = context.user_data.get("missing_parts")
        transport = context.user_data.get("transport_method")
        needs_tow = context.user_data.get("needs_tow")
        tow_address = context.user_data.get("tow_address")
        loc = context.user_data.get("location") or {}
        lat = loc.get("latitude")
        lon = loc.get("longitude")
        photos = context.user_data.get("photos") or []

        username = getattr(user, "username", None)
        user_line = f"@{username}" if username else str(user.id)

        if lang == "ee":
            title = f"Uus päring #{lead_id}"
            labels = {
                "plate": "Number",
                "name": "Nimi",
                "is_owner": "Omanik",
                "phone": "Telefon",
                "weight": "Tühimass",
                "completeness": "Komplektsus",
                "missing_parts": "Puudub",
                "transport": "Transport",
                "needs_tow": "Buksiir",
                "photos": "Fotod",
                "from": "Kasutaja",
                "location": "Asukoht",
            }
        elif lang == "ru":
            title = f"Новая заявка #{lead_id}"
            labels = {
                "plate": "Номер",
                "name": "Имя",
                "is_owner": "Владелец",
                "phone": "Телефон",
                "weight": "Масса",
                "completeness": "Комплектность",
                "missing_parts": "Отсутствует",
                "transport": "Доставка",
                "needs_tow": "Эвакуатор",
                "photos": "Фото",
                "from": "Пользователь",
                "location": "Локация",
            }
        else:
            title = f"New inquiry #{lead_id}"
            labels = {
                "plate": "Plate",
                "name": "Name",
                "is_owner": "Owner",
                "phone": "Phone",
                "weight": "Weight",
                "completeness": "Completeness",
                "missing_parts": "Missing",
                "transport": "Transport",
                "needs_tow": "Needs tow",
                "photos": "Photos",
                "from": "From",
                "location": "Location",
            }

        msg_lines = [
            title,
            f"{labels['plate']}: {plate}",
            f"{labels['name']}: {name}",
            f"{labels['phone']}: {phone}",
            f"{labels['weight']}: {weight}",
            f"{labels['completeness']}: {completeness}",
        ]

        if is_owner is not None:
            msg_lines.insert(3, f"{labels['is_owner']}: {_yes_no(lang, bool(is_owner))}")

        if missing_parts:
            msg_lines.append(f"{labels['missing_parts']}: {missing_parts}")

        msg_lines += [
            f"{labels['transport']}: {transport}",
            f"{labels['needs_tow']}: {_yes_no(lang, bool(needs_tow) if needs_tow is not None else None)}",
            f"{labels['photos']}: {len(photos)}",
            f"{labels['from']}: {user_line}",
        ]
        if tow_address:
            msg_lines.append(f"{labels['location']}: {tow_address}")
        elif lat is not None and lon is not None:
            msg_lines.append(f"{labels['location']}: {lat}, {lon}")

        # Prepare Call button only if phone looks like a full international number
        call_button = None
        if phone and re.fullmatch(r"\+?[0-9]{10,15}", phone):
            call_button = InlineKeyboardButton("📞 Helista kohe", url=f"tel:{phone}")

        if call_button:
            reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("💬 Vasta pakkumisega", callback_data=f"admin_reply:{lead_id}"), call_button], [InlineKeyboardButton("🗑️ Arhiveeri", callback_data=f"admin_archive:{lead_id}")]])
        else:
            reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("💬 Vasta pakkumisega", callback_data=f"admin_reply:{lead_id}")], [InlineKeyboardButton("🗑️ Arhiveeri", callback_data=f"admin_archive:{lead_id}")]])

        try:
            await context.bot.send_message(
                chat_id=ADMIN_TELEGRAM_USER_ID,
                text="\n".join(msg_lines),
                reply_markup=reply_markup,
            )
            logger.info("Admin notification sent for lead %s", lead_id)
        except Exception:
            logger.exception("FAILED to send admin lead message (lead_id=%s, admin_id=%s)", lead_id, ADMIN_TELEGRAM_USER_ID)
    else:
        logger.warning("ADMIN_TELEGRAM_USER_ID is not set or <=0 (value=%s); skipping admin notification for lead %s", ADMIN_TELEGRAM_USER_ID, lead_id)

        media = []
        photo_bytes = []
        for path in photos[:4]:
            try:
                p = Path(path)
                if not p.is_absolute():
                    p = _BASE_DIR / p
                if not p.exists():
                    continue
                b = p.read_bytes()
                photo_bytes.append(b)
                media.append(InputMediaPhoto(media=b))
            except Exception:
                logger.exception("Failed to read photo for admin send (lead_id=%s)", lead_id)

        if media:
            try:
                await context.bot.send_media_group(chat_id=ADMIN_TELEGRAM_USER_ID, media=media)
            except Exception:
                logger.exception("Failed to send admin media group (lead_id=%s). Falling back to individual photos.", lead_id)
                for b in photo_bytes:
                    try:
                        await context.bot.send_photo(chat_id=ADMIN_TELEGRAM_USER_ID, photo=b)
                    except Exception:
                        logger.exception("Failed to send admin photo fallback (lead_id=%s)", lead_id)

    if context.user_data.get("language") == "ee":
        msg = _thank_you_message("ee")
    elif context.user_data.get("language") == "ru":
        msg = _thank_you_message("ru")
    else:
        msg = _thank_you_message("en")

    await update.message.reply_text(msg, reply_markup=_share_keyboard(context.user_data.get("language", "en")))

    context.user_data.clear()

    return ConversationHandler.END
