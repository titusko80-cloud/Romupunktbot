"""
Vehicle information handlers - Plate validation, owner name, curb weight, completeness
"""

import re
import logging
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, KeyboardButton
from telegram.ext import ContextTypes
from states import VEHICLE_PLATE, OWNER_NAME, OWNER_CONFIRM, CURB_WEIGHT, LOGISTICS, PHOTOS
from handlers.photos import _done_keyboard

logger = logging.getLogger(__name__)

async def plate_validation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Store license plate number - accept user input as-is"""
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
    
    # Store plate exactly as user entered it (no validation, no correction)
    context.user_data['plate_number'] = plate
    
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
    logger.info(f"curb_weight called: user_id={update.effective_user.id}")
    
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
    
    # CODE REPLACEMENT 1 - Remove ReplyKeyboard before showing logistics
    await update.message.reply_text(" ", reply_markup=ReplyKeyboardRemove())
    
    # Show logistics inline keyboard
    from handlers.logistics import show_logistics_inline
    return await show_logistics_inline(update, context)
