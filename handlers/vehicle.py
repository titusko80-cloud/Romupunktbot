"""
Vehicle information handlers - Plate validation, owner name, curb weight, completeness
"""

import re
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ContextTypes
from states import VEHICLE_PLATE, OWNER_NAME, OWNER_CONFIRM, CURB_WEIGHT, COMPLETENESS, MISSING_PARTS, LOGISTICS

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
        msg = f"Autonumber {plate} on õige.\n\nMis on teie nimi?"
    elif context.user_data.get('language') == 'ru':
        msg = f"Номер {plate} принят.\n\nКак вас зовут?"
    else:
        msg = f"License plate {plate} is valid.\n\nWhat is your name?"
    
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

    reply_markup = ReplyKeyboardMarkup([[KeyboardButton(yes_btn), KeyboardButton(no_btn)]], resize_keyboard=True, is_persistent=True)
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
        reply_markup = ReplyKeyboardMarkup([[KeyboardButton(yes_btn), KeyboardButton(no_btn)]], resize_keyboard=True, is_persistent=True)
        await update.message.reply_text(invalid_msg, reply_markup=reply_markup)
        return OWNER_CONFIRM

    context.user_data['is_owner'] = choice == yes_btn
    await update.message.reply_text(weight_msg)
    return CURB_WEIGHT

async def curb_weight(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Store curb weight and ask about completeness"""
    try:
        weight = int(update.message.text.strip())
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
    
    # Ask about completeness
    if context.user_data.get('language') == 'ee':
        keyboard = [[KeyboardButton("Jah"), KeyboardButton("Ei")]]
        msg = "Kas sõiduk on täiskomplektis?"
    elif context.user_data.get('language') == 'ru':
        keyboard = [[KeyboardButton("✅ Полный"), KeyboardButton("❌ Не полный")]]
        msg = "Автомобиль в полной комплектации?"
    else:
        keyboard = [[KeyboardButton("✅ Complete"), KeyboardButton("❌ Missing parts")]]
        msg = "Is the vehicle complete?"

    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, is_persistent=True)

    await update.message.reply_text(msg, reply_markup=reply_markup)
    return COMPLETENESS

async def vehicle_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Store completeness info and ask about logistics"""
    completeness = update.message.text.strip()

    lang = context.user_data.get('language')
    if lang == 'ee':
        valid_complete = "Jah"
        valid_missing = "Ei"
    elif lang == 'ru':
        valid_complete = "✅ Полный"
        valid_missing = "❌ Не полный"
    else:
        valid_complete = "✅ Complete"
        valid_missing = "❌ Missing parts"

    if completeness not in (valid_complete, valid_missing):
        keyboard = [[KeyboardButton(valid_complete), KeyboardButton(valid_missing)]]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, is_persistent=True)
        if lang == 'ee':
            msg = "Palun valige üks nuppudest."
        elif lang == 'ru':
            msg = "Пожалуйста, выберите одну из кнопок."
        else:
            msg = "Please choose one of the buttons."
        await update.message.reply_text(msg, reply_markup=reply_markup)
        return COMPLETENESS

    is_missing = completeness == valid_missing
    context.user_data['completeness'] = 'missing' if is_missing else 'complete'

    if is_missing:
        if lang == 'ee':
            msg = "Mis on puudu? (näiteks aku, rattad, katalüsaator jne)"
        elif lang == 'ru':
            msg = "Что отсутствует? (например аккумулятор, колёса, катализатор и т.д.)"
        else:
            msg = "What is missing? (e.g. battery, wheels, catalytic converter, etc.)"
        await update.message.reply_text(msg)
        return MISSING_PARTS

    if lang == 'ee':
        keyboard = [[KeyboardButton("🚛 Vajan buksiiri"), KeyboardButton("🚗 Toon ise")]]
        msg = "Kuidas soovite sõiduki transportida?"
    elif lang == 'ru':
        keyboard = [[KeyboardButton("🚛 Нужен эвакуатор"), KeyboardButton("🚗 Привезу сам")]]
        msg = "Как вы хотите доставить автомобиль?"
    else:
        keyboard = [[KeyboardButton("🚛 Need tow"), KeyboardButton("🚗 Bring myself")]]
        msg = "How would you like to transport the vehicle?"
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, is_persistent=True)

    await update.message.reply_text(msg, reply_markup=reply_markup)
    return LOGISTICS


async def missing_parts(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = (update.message.text or '').strip()
    context.user_data['missing_parts'] = text

    lang = context.user_data.get('language')
    if lang == 'ee':
        keyboard = [[KeyboardButton("🚛 Vajan buksiiri"), KeyboardButton("🚗 Toon ise")]]
        msg = "Kuidas soovite sõiduki transportida?"
    elif lang == 'ru':
        keyboard = [[KeyboardButton("🚛 Нужен эвакуатор"), KeyboardButton("🚗 Привезу сам")]]
        msg = "Как вы хотите доставить автомобиль?"
    else:
        keyboard = [[KeyboardButton("🚛 Need tow"), KeyboardButton("🚗 Bring myself")]]
        msg = "How would you like to transport the vehicle?"
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, is_persistent=True)

    await update.message.reply_text(msg, reply_markup=reply_markup)
    return LOGISTICS
