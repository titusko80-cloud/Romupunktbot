"""
Vehicle information handlers - Plate validation, owner name, curb weight, completeness
"""

import re
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ContextTypes
from states import VEHICLE_PLATE, OWNER_NAME, CURB_WEIGHT, COMPLETENESS, LOGISTICS

def validate_estonian_plate(plate: str) -> bool:
    """Validate Estonian license plate format (123 ABC)"""
    pattern = r'^[0-9]{3}\s*[A-Z]{3}$'
    return bool(re.match(pattern, plate.upper().replace(' ', ' ')))

async def plate_validation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Validate and store license plate number"""
    plate = update.message.text.strip()
    
    if not validate_estonian_plate(plate):
        if context.user_data.get('language') == 'ee':
            msg = "Vale numberkoodi formaat. Palun sisestage õige formaat (näiteks: 123 ABC):"
        else:
            msg = "Invalid license plate format. Please enter the correct format (example: 123 ABC):"
        
        await update.message.reply_text(msg)
        return VEHICLE_PLATE
    
    # Store validated plate
    context.user_data['plate_number'] = plate.upper()
    
    # Ask for owner name
    if context.user_data.get('language') == 'ee':
        msg = f"Numberkood {plate} on õige.\n\nMis on teie nimi?"
    else:
        msg = f"License plate {plate} is valid.\n\nWhat is your name?"
    
    await update.message.reply_text(msg)
    return OWNER_NAME

async def owner_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Store owner name and ask for curb weight"""
    owner_name = update.message.text.strip()
    context.user_data['owner_name'] = owner_name
    
    if context.user_data.get('language') == 'ee':
        msg = f"Tänan, {owner_name}!\n\nMis on teie sõiduki tühimass (kg)? See on vajalik täpse hinna arvutamiseks."
    else:
        msg = f"Thank you, {owner_name}!\n\nWhat is your vehicle's curb weight (kg)? This is needed for accurate pricing."
    
    await update.message.reply_text(msg)
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
        else:
            msg = "Please enter a valid curb weight in kilograms (500-5000 kg):"
        
        await update.message.reply_text(msg)
        return CURB_WEIGHT
    
    context.user_data['curb_weight'] = weight
    
    # Ask about completeness
    keyboard = [
        [KeyboardButton("✅ Täielik"), KeyboardButton("❌ Puudub")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    
    if context.user_data.get('language') == 'ee':
        msg = "Kas sõiduk on täielik? Valige puuduvad osad (kui on):"
        await update.message.reply_text(msg, reply_markup=reply_markup)
        msg = "• Aku (aku)\n• Katalüsaator (katalüsaator)\n• Mootor (mootor)\n• Muud osad (muud)"
    else:
        msg = "Is the vehicle complete? Select missing parts (if any):"
        await update.message.reply_text(msg, reply_markup=reply_markup)
        msg = "• Battery (aku)\n• Catalyst (katalüsaator)\n• Engine (mootor)\n• Other parts (muud)"
    
    await update.message.reply_text(msg)
    return COMPLETENESS

async def vehicle_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Store completeness info and ask about logistics"""
    completeness = update.message.text.strip()
    context.user_data['completeness'] = completeness
    
    # Ask about logistics
    keyboard = [
        [KeyboardButton("🚛 Vajan treilerit"), KeyboardButton("🚗 Toon ise")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    
    if context.user_data.get('language') == 'ee':
        msg = "Kuidas soovite sõiduki transportida?"
    else:
        msg = "How would you like to transport the vehicle?"
    
    await update.message.reply_text(msg, reply_markup=reply_markup)
    return LOGISTICS
