"""Finalization handler - phone number collection and lead persistence."""

import re
from typing import Optional
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

from database.models import save_lead
from states import PHONE


def _normalize_phone(phone_raw: str) -> Optional[str]:
    phone = phone_raw.strip().replace(" ", "")
    if phone.startswith("00"):
        phone = "+" + phone[2:]
    if re.fullmatch(r"\+?[0-9]{7,15}", phone):
        return phone
    return None


async def phone_number(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    phone_raw = update.message.text
    phone = _normalize_phone(phone_raw)

    if phone is None:
        if context.user_data.get("language") == "ee":
            msg = "Palun sisestage korrektne telefoninumber (näiteks +3725xxxxxxx):"
        else:
            msg = "Please enter a valid phone number (example +3725xxxxxxx):"

        await update.message.reply_text(msg)
        return PHONE

    context.user_data["phone_number"] = phone

    user = update.effective_user
    lead_id = save_lead(context.user_data, user.id, getattr(user, "username", None))
    context.user_data["lead_id"] = lead_id

    if context.user_data.get("language") == "ee":
        msg = (
            "Aitäh! Saime andmed kätte ja helistame teile kiirelt tagasi pakkumisega.\n\n"
            "Me vormistame ka lammutustõendi ja aitame sõiduki registrist eemaldamisega."
        )
    else:
        msg = (
            "Thank you! We received your details and will call you back quickly with an offer.\n\n"
            "We also handle the certificate of destruction and deregistration paperwork."
        )

    await update.message.reply_text(msg)

    return ConversationHandler.END
