import re
import logging

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes

from config import ADMIN_TELEGRAM_USER_ID
from database.models import (
    get_latest_leads, get_lead_by_id, create_offer, get_offer_by_id, 
    update_offer_status, update_lead_status, delete_lead_by_id, get_lead_photos
)

logger = logging.getLogger(__name__)


def _format_lead(lead: dict, compact: bool = False) -> str:
    lead_id = lead.get("id")
    created_at = lead.get("created_at")
    plate = lead.get("plate_number")
    name = lead.get("owner_name")
    is_owner = lead.get("is_owner")
    phone = lead.get("phone_number")
    lang = lead.get("language")
    weight = lead.get("curb_weight")
    completeness = lead.get("completeness")
    missing_parts = lead.get("missing_parts")
    transport = lead.get("transport_method")
    needs_tow = lead.get("needs_tow")
    tow_address = lead.get("tow_address")
    lat = lead.get("location_latitude")
    lon = lead.get("location_longitude")
    
    # Get photos from the photos table, not the leads table
    try:
        photos = get_lead_photos(lead_id)
        photos_count = len(photos)
    except Exception:
        photos_count = 0
    
    status = lead.get("status", "pending")

    # Status badge
    status_emoji = {"pending": "🔵", "replied": "💬", "accepted": "✅", "rejected": "❌", "archived": "🗑️"}
    badge = status_emoji.get(status, "🔵")

    if compact:
        # One-line summary for quick scanning
        return f"{badge} #{lead_id} {plate} · {name} · {phone} ({photos_count}📷)"

    if completeness in ("complete", "missing"):
        if lang == "ee":
            completeness = "✅ Täielik" if completeness == "complete" else "❌ Puudub"
        elif lang == "ru":
            completeness = "✅ Полный" if completeness == "complete" else "❌ Не полный"
        else:
            completeness = "✅ Complete" if completeness == "complete" else "❌ Missing parts"

    if lang == "ee":
        title = f"{badge} Päring #{lead_id} ({created_at})"
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
            "location": "Asukoht",
            "photos": "Fotod",
        }
        yes_txt = "Jah"
        no_txt = "Ei"
    elif lang == "ru":
        title = f"{badge} Заявка #{lead_id} ({created_at})"
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
            "location": "Локация",
            "photos": "Фото",
        }
        yes_txt = "Да"
        no_txt = "Нет"
    else:
        title = f"{badge} Lead #{lead_id} ({created_at})"
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
            "location": "Location",
            "photos": "Photos",
        }
        yes_txt = "Yes"
        no_txt = "No"

    lines = []
    lines.append(title)
    lines.append(f"{labels['plate']}: {plate}")
    lines.append(f"{labels['name']}: {name}")
    if is_owner is not None:
        lines.append(f"{labels['is_owner']}: {yes_txt if int(is_owner) == 1 else no_txt}")
    lines.append(f"{labels['phone']}: {phone}")
    lines.append(f"{labels['weight']}: {weight}kg")
    if completeness is not None:
        lines.append(f"{labels['completeness']}: {completeness}")
    if missing_parts:
        lines.append(f"{labels['missing_parts']}: {missing_parts}")
    if transport is not None:
        lines.append(f"{labels['transport']}: {transport}")
    if needs_tow is not None:
        lines.append(f"{labels['needs_tow']}: {yes_txt if bool(needs_tow) else no_txt}")
    if tow_address:
        lines.append(f"{labels['location']}: {tow_address}")
    elif lat is not None and lon is not None:
        lines.append(f"{labels['location']}: {lat}, {lon}")
    lines.append(f"{labels['photos']}: {photos_count}")

    return "\n".join(lines)


async def leads_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if ADMIN_TELEGRAM_USER_ID <= 0:
        await update.message.reply_text("ADMIN_TELEGRAM_USER_ID is not set on the server.")
        return

    if user is None or user.id != ADMIN_TELEGRAM_USER_ID:
        await update.message.reply_text("Not authorized.")
        return

    chat = update.effective_chat
    chat_type = getattr(chat, "type", None)

    limit = 10
    if context.args:
        try:
            limit = int(context.args[0])
        except ValueError:
            limit = 10

    if limit < 1:
        limit = 1
    if limit > 30:
        limit = 30

    leads = get_latest_leads(limit)
    if not leads:
        await update.message.reply_text("No leads yet.")
        return

    # Reverse order: newest at bottom
    leads = list(reversed(leads))

    for lead in leads:
        lead_id = lead.get("id")
        status = lead.get("status", "pending")
        status_emoji = {"pending": "🔵", "replied": "💬", "accepted": "✅", "rejected": "❌", "archived": "🗑️"}
        badge = status_emoji.get(status, "🔵")
        text = f"{badge} #{lead_id} {lead.get('plate_number')} · {lead.get('owner_name')} · {lead.get('phone_number')}"
        reply_markup = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("💬 Vasta", callback_data=f"admin_reply:{lead_id}"),
                InlineKeyboardButton("🗑️ Arhiveeri", callback_data=f"admin_archive:{lead_id}"),
                InlineKeyboardButton("🗑️ Kustuta", callback_data=f"admin_delete:{lead_id}"),
            ]
        ])
        await update.message.reply_text(text, reply_markup=reply_markup)

    if chat_type is not None and chat_type != "private":
        await update.message.reply_text("Saadan privaatsõnumisse.")
    return


def _parse_price(text: str) -> float | None:
    """Extract the first number from a string (e.g. '200 eurot' -> 200)."""
    if not text:
        return None

    compact = re.sub(r"\s+", "", text)
    m = re.search(r"(\d+(?:[\.,]\d{1,2})?)", compact)
    if not m:
        return None

    token = m.group(1).replace(",", ".")
    try:
        return float(token)
    except ValueError:
        return None


def _offer_text(lang: str, amount: float) -> str:
    """Clean, official offer message"""
    amount_txt = f"{int(amount)}" if float(amount).is_integer() else f"{amount:.2f}".rstrip("0").rstrip(".")
    if lang == "ee":
        return f"🏁 ROMUPUNKT\n\nAmetlik pakkumine: {amount_txt}€\n\nSisaldab lammutusteenust ja lammutustõendit."
    if lang == "ru":
        return f"🏁 ROMUPUNKT\n\nОфициальное предложение: {amount_txt}€\n\nВключает утилизацию и справку о ликвидации."
    return f"🏁 ROMUPUNKT\n\nOfficial offer: {amount_txt}€\n\nIncludes dismantling service and destruction certificate."


def _offer_keyboard(lang: str, offer_id: int) -> InlineKeyboardMarkup:
    if lang == "ee":
        yes = "✅ JAH"
        no = "❌ EI"
        counter = "💬 Teen oma pakkumise"
    elif lang == "ru":
        yes = "✅ ДА"
        no = "❌ НЕТ"
        counter = "💬 Моя цена"
    else:
        yes = "✅ YES"
        no = "❌ NO"
        counter = "💬 Counter offer"

    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(yes, callback_data=f"offer_accept:{offer_id}"),
                InlineKeyboardButton(no, callback_data=f"offer_reject:{offer_id}"),
            ],
            [
                InlineKeyboardButton(counter, callback_data=f"offer_counter:{offer_id}"),
            ],
        ]
    )


async def offer_counter_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    if q is None:
        return

    data = q.data or ""
    if not data.startswith("offer_counter:"):
        await q.answer()
        return

    try:
        offer_id = int(data.split(":", 1)[1])
    except Exception:
        await q.answer("Error", show_alert=True)
        return

    offer = get_offer_by_id(offer_id)
    if not offer:
        await q.answer("Offer not found", show_alert=True)
        return

    lead = get_lead_by_id(int(offer.get("lead_id")))
    if not lead:
        await q.answer("Lead not found", show_alert=True)
        return

    user = update.effective_user
    if user is None or int(user.id) != int(lead.get("user_id")):
        await q.answer("Not allowed", show_alert=True)
        return

    logger.info(
        "offer_counter_callback: user_id=%s offer_id=%s lead_id=%s",
        user.id,
        offer_id,
        lead.get("id"),
    )
    awaiting_offer_id = int(offer_id)
    awaiting_lead_id = int(lead.get("id"))
    context.user_data["awaiting_counter_offer_offer_id"] = awaiting_offer_id
    context.user_data["awaiting_counter_offer_lead_id"] = awaiting_lead_id
    context.chat_data["awaiting_counter_offer_offer_id"] = awaiting_offer_id
    context.chat_data["awaiting_counter_offer_lead_id"] = awaiting_lead_id
    await q.answer()

    lang = lead.get("language")
    if lang == "ee":
        prompt = "Palun kirjuta oma hind (näiteks 250 või 250€)."
    elif lang == "ru":
        prompt = "Напишите вашу цену (например 250 или 250€)."
    else:
        prompt = "Type your price (e.g. 250 or 250€)."

    from telegram import ForceReply
    await context.bot.send_message(
        chat_id=int(lead.get("user_id")),
        text=prompt,
        reply_markup=ForceReply(selective=True),
    )


async def counter_offer_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # If admin is currently replying with a price offer, do not let counter-offer logic
    # intercept the admin's numeric message (common when admin is also the testing user).
    if context.chat_data.get("awaiting_price_lead_id"):
        return

    offer_id = context.user_data.get("awaiting_counter_offer_offer_id")
    lead_id = context.user_data.get("awaiting_counter_offer_lead_id")
    if not offer_id or not lead_id:
        offer_id = context.chat_data.get("awaiting_counter_offer_offer_id")
        lead_id = context.chat_data.get("awaiting_counter_offer_lead_id")
    if not offer_id or not lead_id:
        return

    user = update.effective_user
    logger.info(
        "counter_offer_message called: user_id=%s offer_id=%s lead_id=%s",
        user.id if user else None,
        offer_id,
        lead_id,
    )

    if user is None:
        return

    lead = get_lead_by_id(int(lead_id))
    if not lead:
        context.user_data.pop("awaiting_counter_offer_offer_id", None)
        context.user_data.pop("awaiting_counter_offer_lead_id", None)
        context.chat_data.pop("awaiting_counter_offer_offer_id", None)
        context.chat_data.pop("awaiting_counter_offer_lead_id", None)
        return

    if int(user.id) != int(lead.get("user_id")):
        return

    raw_text = update.message.text if update.message else ""
    amount = _parse_price(raw_text)
    logger.info(
        "counter_offer_message: raw_text=%r parsed_amount=%s",
        raw_text,
        amount,
    )

    lang = lead.get("language")
    if amount is None or amount <= 0:
        if lang == "ee":
            msg = "Palun sisesta number (näiteks 250)."
        elif lang == "ru":
            msg = "Пожалуйста, введите число (например 250)."
        else:
            msg = "Please send a number (e.g. 250)."
        await update.message.reply_text(msg)
        return

    context.user_data.pop("awaiting_counter_offer_offer_id", None)
    context.user_data.pop("awaiting_counter_offer_lead_id", None)
    context.chat_data.pop("awaiting_counter_offer_offer_id", None)
    context.chat_data.pop("awaiting_counter_offer_lead_id", None)

    if ADMIN_TELEGRAM_USER_ID and ADMIN_TELEGRAM_USER_ID > 0:
        plate = lead.get("plate_number")
        phone = lead.get("phone_number")
        admin_text = (
            f"💬 Counter-offer received\n"
            f"Lead #{lead.get('id')}\n"
            f"Plate: {plate}\n"
            f"Phone: {phone}\n"
            f"User offered: {int(amount) if float(amount).is_integer() else amount}€"
        )
        reply_markup = InlineKeyboardMarkup(
            [[InlineKeyboardButton("💬 Vasta", callback_data=f"admin_reply:{lead.get('id')}")]]
        )
        logger.info(
            "counter_offer_message: notifying admin chat_id=%s for lead_id=%s",
            ADMIN_TELEGRAM_USER_ID,
            lead.get("id"),
        )
        await context.bot.send_message(chat_id=ADMIN_TELEGRAM_USER_ID, text=admin_text, reply_markup=reply_markup)

    if lang == "ee":
        ack = "Aitäh! Saatsime teie pakkumise üle."
    elif lang == "ru":
        ack = "Спасибо! Мы передали вашу цену."
    else:
        ack = "Thanks! We forwarded your price."
    await update.message.reply_text(ack)
    return


async def admin_archive_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    if q is None:
        return

    user = update.effective_user
    if user is None or ADMIN_TELEGRAM_USER_ID <= 0 or user.id != ADMIN_TELEGRAM_USER_ID:
        await q.answer("Not authorized.", show_alert=True)
        return

    data = q.data or ""
    if not data.startswith("admin_archive:"):
        await q.answer()
        return

    try:
        lead_id = int(data.split(":", 1)[1])
    except Exception:
        await q.answer("Error", show_alert=True)
        return

    update_lead_status(lead_id, "archived")
    await q.answer("Arhiveeritud", show_alert=False)
    try:
        await q.edit_message_reply_markup(reply_markup=None)
    except Exception:
        pass

async def admin_delete_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    if q is None:
        return

    user = update.effective_user
    if user is None or ADMIN_TELEGRAM_USER_ID <= 0 or user.id != ADMIN_TELEGRAM_USER_ID:
        await q.answer("Not authorized.", show_alert=True)
        return

    data = q.data or ""
    if not data.startswith("admin_delete:"):
        await q.answer()
        return

    try:
        lead_id = int(data.split(":", 1)[1])
    except Exception:
        await q.answer("Error", show_alert=True)
        return

    delete_lead_by_id(lead_id)
    await q.answer("Kustutatud", show_alert=False)
    try:
        await q.edit_message_text(text="🗑️ Kustutatud", reply_markup=None)
    except Exception:
        pass

async def admin_lead_action_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    if q is None:
        return

    user = update.effective_user
    if user is None or ADMIN_TELEGRAM_USER_ID <= 0 or user.id != ADMIN_TELEGRAM_USER_ID:
        await q.answer("Not authorized.", show_alert=True)
        return

    data = q.data or ""
    if not data.startswith("admin_reply:"):
        await q.answer()
        return

    try:
        lead_id = int(data.split(":", 1)[1])
    except Exception:
        await q.answer("Error", show_alert=True)
        return

    # Ensure stale counter-offer state doesn't hijack the admin's next numeric reply.
    context.user_data.pop("awaiting_counter_offer_offer_id", None)
    context.user_data.pop("awaiting_counter_offer_lead_id", None)
    context.chat_data.pop("awaiting_counter_offer_offer_id", None)
    context.chat_data.pop("awaiting_counter_offer_lead_id", None)

    context.chat_data["awaiting_price_lead_id"] = str(lead_id)
    await q.answer()

    from telegram import ForceReply
    reply_markup = ForceReply(selective=True)
    await context.bot.send_message(
        chat_id=ADMIN_TELEGRAM_USER_ID,
        text=f"Send your price offer for lead #{lead_id}:",
        reply_markup=reply_markup
    )


async def admin_price_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle admin price input with robust parsing"""
    user = update.effective_user
    logger.info(f"admin_price_message called: user_id={user.id if user else 'None'}, ADMIN_TELEGRAM_USER_ID={ADMIN_TELEGRAM_USER_ID}")
    
    if user is None or ADMIN_TELEGRAM_USER_ID <= 0 or user.id != ADMIN_TELEGRAM_USER_ID:
        logger.warning("admin_price_message: Not authorized")
        return

    lead_id = context.chat_data.get("awaiting_price_lead_id")
    logger.info(f"admin_price_message: awaiting_price_lead_id={lead_id}")
    logger.info(f"admin_price_message: chat_data keys={list(context.chat_data.keys())}")
    
    if not lead_id:
        logger.info("admin_price_message: Not awaiting a price - ignoring message")
        return

    raw_text = update.message.text if update.message else ""
    logger.info(f"admin_price_message: raw_text='{raw_text}'")
    
    if not raw_text:
        logger.warning("admin_price_message: No text found")
        return

    # Robust price parsing - strip non-digits
    amount = _parse_price(raw_text)
    logger.info(f"admin_price_message: parsed amount={amount}")
    
    if amount is None or amount <= 0:
        logger.warning(f"admin_price_message: Invalid amount {amount}")
        await update.message.reply_text("Palun sisesta kehtiv hind (näiteks 800€ või 200).")
        return

    lead = get_lead_by_id(int(lead_id))
    if not lead:
        context.chat_data.pop("awaiting_price_lead_id", None)
        await update.message.reply_text("Päringut ei leitud.")
        return

    offer_id = create_offer(int(lead_id), float(amount), status="sent")
    update_lead_status(int(lead_id), "replied")
    chat_id = lead.get("user_id")
    lang = lead.get("language")
    
    try:
        logger.info("Sending offer %s to user %s (lead %s)", amount, chat_id, lead_id)
        await context.bot.send_message(
            chat_id=chat_id,
            text=_offer_text(lang, float(amount)),
            reply_markup=_offer_keyboard(lang, offer_id),
        )
        logger.info("Offer sent successfully to user %s", chat_id)
    except Exception as e:
        logger.exception("Failed to send offer to user %s (lead %s): %s", chat_id, lead_id, e)
        await update.message.reply_text("Ei saanud kasutajale pakkumist saata (võib-olla kasutaja on bot'i blokeerinud).")
        context.chat_data.pop("awaiting_price_lead_id", None)
        return

    context.chat_data.pop("awaiting_price_lead_id", None)
    await update.message.reply_text(f"Pakkumine saadetud (#{lead_id}).")
    return


async def offer_response_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    if q is None:
        return

    data = q.data or ""
    if not (data.startswith("offer_accept:") or data.startswith("offer_reject:")):
        await q.answer()
        return

    accepted = data.startswith("offer_accept:")
    try:
        offer_id = int(data.split(":", 1)[1])
    except Exception:
        await q.answer("Error", show_alert=True)
        return

    offer = get_offer_by_id(offer_id)
    if not offer:
        await q.answer("Offer not found", show_alert=True)
        return

    lead = get_lead_by_id(int(offer.get("lead_id")))
    if not lead:
        await q.answer("Lead not found", show_alert=True)
        return

    user = update.effective_user
    if user is None or int(user.id) != int(lead.get("user_id")):
        await q.answer("Not allowed", show_alert=True)
        return

    update_offer_status(offer_id, "accepted" if accepted else "rejected")
    update_lead_status(int(lead.get("id")), "accepted" if accepted else "rejected")
    await q.answer("OK")

    try:
        await q.edit_message_reply_markup(reply_markup=None)
    except Exception:
        pass

    lang = lead.get("language")
    if accepted:
        if lang == "ee":
            user_msg = "Aitäh! Võtame teiega kohe ühendust."
        elif lang == "ru":
            user_msg = "Спасибо! Мы сейчас свяжемся с вами."
        else:
            user_msg = "Thank you! We will contact you shortly."
    else:
        if lang == "ee":
            user_msg = "Selge! Aitäh vastuse eest."
        elif lang == "ru":
            user_msg = "Понятно! Спасибо за ответ."
        else:
            user_msg = "Got it. Thank you for your response."

    if q.message is not None:
        try:
            await q.message.reply_text(user_msg)
        except Exception:
            pass

    if not accepted:
        awaiting_offer_id = int(offer_id)
        awaiting_lead_id = int(lead.get("id"))
        context.user_data["awaiting_counter_offer_offer_id"] = awaiting_offer_id
        context.user_data["awaiting_counter_offer_lead_id"] = awaiting_lead_id
        context.chat_data["awaiting_counter_offer_offer_id"] = awaiting_offer_id
        context.chat_data["awaiting_counter_offer_lead_id"] = awaiting_lead_id

        if lang == "ee":
            prompt = "Kui soovite, kirjutage oma hind (näiteks 250 või 250€)."
        elif lang == "ru":
            prompt = "Если хотите, напишите вашу цену (например 250 или 250€)."
        else:
            prompt = "If you want, type your price (e.g. 250 or 250€)."

        from telegram import ForceReply
        try:
            await context.bot.send_message(
                chat_id=int(lead.get("user_id")),
                text=prompt,
                reply_markup=ForceReply(selective=True),
            )
        except Exception:
            pass

    if ADMIN_TELEGRAM_USER_ID and ADMIN_TELEGRAM_USER_ID > 0:
        plate = lead.get("plate_number")
        phone = lead.get("phone_number")
        amount = offer.get("offer_amount")
        lang = lead.get("language")
        if accepted:
            if lang == "ee":
                status_txt = "NÕUS"
                pre = "Vastus pakkumisele"
            elif lang == "ru":
                status_txt = "СОГЛАСЕН"
                pre = "Ответ на предложение"
            else:
                status_txt = "ACCEPTED"
                pre = "Response to offer"
        else:
            if lang == "ee":
                status_txt = "EI SOBI"
                pre = "Vastus pakkumisele"
            elif lang == "ru":
                status_txt = "НЕ ПОДОШЛО"
                pre = "Ответ на предложение"
            else:
                status_txt = "REJECTED"
                pre = "Response to offer"
        try:
            await context.bot.send_message(
                chat_id=ADMIN_TELEGRAM_USER_ID,
                text=f"{pre} #{offer_id} (päring #{lead.get('id')}): {status_txt}\nNumber: {plate}\nTelefon: {phone}\nPakkumine: {amount}€",
            )
        except Exception:
            pass
