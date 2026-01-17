import re

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, ApplicationHandlerStop

from config import ADMIN_TELEGRAM_USER_ID
from database.models import get_latest_leads, get_lead_by_id, create_offer, get_offer_by_id, update_offer_status


def _format_lead(lead: dict) -> str:
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
    photos = (lead.get("photos") or "").strip()
    photos_count = len([p for p in photos.split(",") if p]) if photos else 0

    if completeness in ("complete", "missing"):
        if lang == "ee":
            completeness = "✅ Täielik" if completeness == "complete" else "❌ Puudub"
        elif lang == "ru":
            completeness = "✅ Полный" if completeness == "complete" else "❌ Не полный"
        else:
            completeness = "✅ Complete" if completeness == "complete" else "❌ Missing parts"

    if lang == "ee":
        title = f"Päring #{lead_id} ({created_at})"
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
        title = f"Заявка #{lead_id} ({created_at})"
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
        title = f"Lead #{lead_id} ({created_at})"
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

    text = "\n\n".join(_format_lead(l) for l in leads)
    if len(text) > 3500:
        text = text[:3500] + "\n\n(truncated)"

    if chat_type is not None and chat_type != "private":
        try:
            await context.bot.send_message(chat_id=ADMIN_TELEGRAM_USER_ID, text=text)
            await update.message.reply_text("Saadan privaatsõnumisse.")
        except Exception:
            await update.message.reply_text("Cannot send private message. Open the bot in private chat first.")
        return

    await update.message.reply_text(text)


def _parse_price(text: str):
    m = re.search(r"([0-9]+(?:[\.,][0-9]+)?)", text or "")
    if not m:
        return None
    v = m.group(1).replace(",", ".")
    try:
        return float(v)
    except ValueError:
        return None


def _offer_text(lang: str, amount: float) -> str:
    amount_txt = f"{int(amount)}" if float(amount).is_integer() else f"{amount:.2f}".rstrip("0").rstrip(".")
    if lang == "ee":
        return f"Meie pakkumine on {amount_txt}€. Sobib?"
    if lang == "ru":
        return f"Наше предложение {amount_txt}€. Подходит?"
    return f"Our offer is {amount_txt}€. Does it work for you?"


def _offer_keyboard(lang: str, offer_id: int) -> InlineKeyboardMarkup:
    if lang == "ee":
        yes = "✅ JAH"
        no = "❌ EI"
    elif lang == "ru":
        yes = "✅ ДА"
        no = "❌ НЕТ"
    else:
        yes = "✅ YES"
        no = "❌ NO"

    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(yes, callback_data=f"offer_accept:{offer_id}"),
                InlineKeyboardButton(no, callback_data=f"offer_reject:{offer_id}"),
            ]
        ]
    )


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

    lead = get_lead_by_id(lead_id)
    if not lead:
        await q.answer("Lead not found", show_alert=True)
        return

    context.chat_data["awaiting_price_lead_id"] = lead_id
    await q.answer()
    await q.message.reply_text(f"Kirjuta pakkumine (näiteks 800€) päringule #{lead_id}:")


async def admin_price_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if user is None or ADMIN_TELEGRAM_USER_ID <= 0 or user.id != ADMIN_TELEGRAM_USER_ID:
        return

    lead_id = context.chat_data.get("awaiting_price_lead_id")
    if not lead_id:
        return

    raw_text = update.message.text if update.message else ""
    if not re.search(r"\d", raw_text or ""):
        return

    amount = _parse_price(raw_text)
    if amount is None:
        await update.message.reply_text("Palun sisesta hind (näiteks 800€).")
        raise ApplicationHandlerStop

    lead = get_lead_by_id(int(lead_id))
    if not lead:
        context.chat_data.pop("awaiting_price_lead_id", None)
        await update.message.reply_text("Päringut ei leitud.")
        return

    offer_id = create_offer(int(lead_id), float(amount), status="sent")
    chat_id = lead.get("user_id")
    lang = lead.get("language")
    try:
        await context.bot.send_message(
            chat_id=chat_id,
            text=_offer_text(lang, float(amount)),
            reply_markup=_offer_keyboard(lang, offer_id),
        )
    except Exception:
        await update.message.reply_text("Ei saanud kasutajale pakkumist saata (võib-olla kasutaja on bot'i blokeerinud).")
        context.chat_data.pop("awaiting_price_lead_id", None)
        raise ApplicationHandlerStop

    context.chat_data.pop("awaiting_price_lead_id", None)
    await update.message.reply_text(f"Pakkumine saadetud (#{lead_id}).")
    raise ApplicationHandlerStop


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

    if ADMIN_TELEGRAM_USER_ID and ADMIN_TELEGRAM_USER_ID > 0:
        plate = lead.get("plate_number")
        phone = lead.get("phone_number")
        amount = offer.get("offer_amount")
        status_txt = "NÕUS" if accepted else "EI SOBI"
        try:
            await context.bot.send_message(
                chat_id=ADMIN_TELEGRAM_USER_ID,
                text=f"Vastus pakkumisele #{offer_id} (päring #{lead.get('id')}): {status_txt}\nNumber: {plate}\nTelefon: {phone}\nPakkumine: {amount}€",
            )
        except Exception:
            pass
