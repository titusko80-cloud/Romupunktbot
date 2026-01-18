"""
Vehicle information handlers - Plate validation, owner name, curb weight, completeness
"""

import re
import logging
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ContextTypes
from states import VEHICLE_PLATE, OWNER_NAME, OWNER_CONFIRM, CURB_WEIGHT, COMPLETENESS, MISSING_PARTS, LOGISTICS, PHOTOS
from handlers.photos import _done_keyboard

logger = logging.getLogger(__name__)

def validate_estonian_plate(plate: str) -> bool:
    """Validate Estonian license plate format (123 ABC)"""
    pattern = r'^[0-9]{3}\s*[A-Z]{3}$'
    return bool(re.match(pattern, plate.upper().replace(' ', ' ')))

async def plate_validation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Validate and store license plate number"""
    plate = (update.message.text or "").strip()

    if not plate:
        if context.user_data.get('language') == 'ee':
            msg = "Palun sisestage autonumber:"
        elif context.user_data.get('language') == 'ru':
            msg = "Пожалуйста, введите номер автомобиля:"
        else:
            msg = "Please enter the license plate number:"

        await update.message.reply_text(msg)
        return VEHICLE_PLATE
    
    # Store validated plate
    context.user_data['plate_number'] = plate.upper()
    
    # Ask for owner name
    if context.user_data.get('language') == 'ee':
        msg = f"Autonumber {plate} on salvestatud.\n\nMis on teie nimi?"
    elif context.user_data.get('language') == 'ru':
        msg = f"Номер {plate} сохранён.\n\nКак вас зовут?"
    else:
        msg = f"License plate {plate} saved.\n\nWhat is your name?"
    
    await update.message.reply_text(msg)
    return OWNER_NAME

async def owner_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Store owner name and ask for curb weight"""
    owner_name = update.message.text.strip()
    context.user_data['owner_name'] = owner_name

    lang = context.user_data.get('language')
    if lang == 'ee':
        yes_btn = "✅ Jah"
        no_btn = "❌ Ei"
        msg = f"Tänan, {owner_name}!\n\nKas te olete selle sõiduki omanik?"
    elif lang == 'ru':
        yes_btn = "✅ Да"
        no_btn = "❌ Нет"
        msg = f"Спасибо, {owner_name}!\n\nВы владелец этого автомобиля?"
    else:
        yes_btn = "✅ Yes"
        no_btn = "❌ No"
        msg = f"Thank you, {owner_name}!\n\nAre you the owner of this vehicle?"

    reply_markup = ReplyKeyboardMarkup([[KeyboardButton(yes_btn), KeyboardButton(no_btn)]], resize_keyboard=True, is_persistent=False)
    await update.message.reply_text(msg, reply_markup=reply_markup)
    return OWNER_CONFIRM


async def owner_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = context.user_data.get('language')
    choice = (update.message.text or '').strip()

    if lang == 'ee':
        yes_btn = "✅ Jah"
        no_btn = "❌ Ei"
        invalid_msg = "Palun valige üks nuppudest."
        weight_msg = "Mis on teie sõiduki tühimass (kg)? See on vajalik täpse hinna arvutamiseks."
    elif lang == 'ru':
        yes_btn = "✅ Да"
        no_btn = "❌ Нет"
        invalid_msg = "Пожалуйста, выберите одну из кнопок."
        weight_msg = "Какова снаряжённая масса автомобиля (кг)? Это нужно для точной оценки."
    else:
        yes_btn = "✅ Yes"
        no_btn = "❌ No"
        invalid_msg = "Please choose one of the buttons."
        weight_msg = "What is your vehicle's curb weight (kg)? This is needed for accurate pricing."

    if choice not in (yes_btn, no_btn):
        reply_markup = ReplyKeyboardMarkup([[KeyboardButton(yes_btn), KeyboardButton(no_btn)]], resize_keyboard=True, is_persistent=False)
        await update.message.reply_text(invalid_msg, reply_markup=reply_markup)
        return OWNER_CONFIRM

    context.user_data['is_owner'] = choice == yes_btn
    await update.message.reply_text(weight_msg)
    return CURB_WEIGHT

async def curb_weight(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Store curb weight and go directly to photos"""
    logger.info(f"curb_weight called: user_id={update.effective_user.id}, current_state={context.user_data.get('current_state', 'unknown')}")
    
    try:
        # Extract numbers from text (handles "1500", "1500 kg", "1500kg", etc.)
        import re
        text = update.message.text.strip()
        numbers = re.findall(r'\d+', text)
        if not numbers:
            raise ValueError("No numbers found")
        
        weight = int(numbers[0])
        if weight < 500 or weight > 5000:
            raise ValueError("Weight out of reasonable range")
    except ValueError:
        if context.user_data.get('language') == 'ee':
            msg = "Palun sisestage korrektne tühimass kilogrammides (500-5000 kg):"
        elif context.user_data.get('language') == 'ru':
            msg = "Введите корректную массу в кг (500-5000):"
        else:
            msg = "Please enter a valid curb weight in kilograms (500-5000 kg):"
        
        await update.message.reply_text(msg)
        return CURB_WEIGHT
    
    context.user_data['curb_weight'] = weight
    logger.info(f"curb_weight: weight={weight}, going to photos")
    
    # Go directly to photos (reorganized flow)
    if context.user_data.get('language') == 'ee':
        msg = "Täname! Nüüd palun saatke 3-4 selget fotot sõidukist eri nurkadest:\n• Eest\n• Tagant\n• Külg\n• Salong (kui võimalik)"
    elif context.user_data.get('language') == 'ru':
        msg = "Спасибо! Теперь отправьте 3-4 чётких фото автомобиля с разных ракурсов:\n• Спереди\n• Сзади\n• Сбоку\n• Салон (если возможно)"
    else:
        msg = "Thank you! Now please send 3-4 clear photos of the vehicle from different angles:\n• Front\n• Back\n• Side\n• Interior (if possible)"
    
    await update.message.reply_text(msg, reply_markup=_done_keyboard(context.user_data.get('language', 'en')))
    return PHOTOS

async def vehicle_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """This handler is no longer used - completeness was removed from flow"""
    # This should never be called since COMPLETENESS state was removed
    return LOGISTICS


async def missing_parts(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """This handler is no longer used - completeness was removed from flow"""
    # This should never be called since MISSING_PARTS state was removed
    return LOGISTICS
