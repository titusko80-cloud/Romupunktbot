"""
Logistics handlers - Transport selection and tow details
"""

from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ContextTypes
from states import LOGISTICS, LOCATION, PHOTOS
import logging

logger = logging.getLogger(__name__)

async def logistics_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle transport selection"""
    choice = update.message.text.strip()
    context.user_data['transport_method'] = choice
    logger.info("logistics_selection: choice=%s, user_id=%s", choice, update.effective_user.id)

    choice_l = choice.lower()
    lang = context.user_data.get('language')
    if lang == 'ee':
        tow_button = "🚛 Vajan buksiiri"
        self_button = "🚗 Toon ise"
    elif lang == 'ru':
        tow_button = "🚛 Нужен эвакуатор"
        self_button = "🚗 Привезу сам"
    else:
        tow_button = "🚛 Need tow"
        self_button = "🚗 Bring myself"

    if choice not in (tow_button, self_button):
        keyboard = [[KeyboardButton(tow_button), KeyboardButton(self_button)]]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, is_persistent=True)
        if lang == 'ee':
            msg = "Palun valige üks nuppudest."
        elif lang == 'ru':
            msg = "Пожалуйста, выберите одну из кнопок."
        else:
            msg = "Please choose one of the buttons."
        await update.message.reply_text(msg, reply_markup=reply_markup)
        return LOGISTICS

    needs_tow = choice == tow_button
    logger.info("logistics_selection: needs_tow=%s", needs_tow)

    if needs_tow:
        context.user_data['needs_tow'] = True
        if context.user_data.get('language') == 'ee':
            msg = "Vajan buksiiri valitud.\n\nPalun kirjutage oma aadress (linn, tänav, maja nr), et saaksime transportikulu arvutada."
        elif context.user_data.get('language') == 'ru':
            msg = "Выбран эвакуатор.\n\nПожалуйста, напишите адрес (город, улица, дом), чтобы мы могли посчитать стоимость перевозки."
        else:
            msg = "Need tow selected.\n\nPlease type your address (city, street, house number) so we can calculate transport costs."

        await update.message.reply_text(msg)
        logger.info("logistics_selection: moving to LOCATION state")
        return LOCATION
    else:
        context.user_data['needs_tow'] = False
        if context.user_data.get('language') == 'ee':
            msg = "Toon ise valitud.\n\nNüüd palun saatke 3-4 selget fotot sõidukist eri nurkadest:\n• Eest\n• Tagant\n• Külg\n• Salong (kui võimalik)"
        elif context.user_data.get('language') == 'ru':
            msg = "Вы выбрали: привезу сам.\n\nТеперь отправьте 3-4 чётких фото автомобиля с разных ракурсов:\n• Спереди\n• Сзади\n• Сбоку\n• Салон (если возможно)"
        else:
            msg = "Bring myself selected.\n\nNow please send 3-4 clear photos of the vehicle from different angles:\n• Front\n• Back\n• Side\n• Interior (if possible)"
        
        await update.message.reply_text(msg)
        logger.info("logistics_selection: moving to PHOTOS state")
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

    if context.user_data.get('language') == 'ee':
        msg = "Aitäh!\n\nNüüd palun saatke 3-4 selget fotot sõidukist eri nurkadest:\n• Eest\n• Tagant\n• Külg\n• Salong (kui võimalik)"
    elif context.user_data.get('language') == 'ru':
        msg = "Спасибо!\n\nТеперь отправьте 3-4 чётких фото автомобиля с разных ракурсов:\n• Спереди\n• Сзади\n• Сбоку\n• Салон (если возможно)"
    else:
        msg = "Thank you!\n\nNow please send 3-4 clear photos of the vehicle from different angles:\n• Front\n• Back\n• Side\n• Interior (if possible)"

    await update.message.reply_text(msg)
    logger.info("location_received: moving to PHOTOS state")
    return PHOTOS
