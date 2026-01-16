"""
Logistics handlers - Transport selection and tow details
"""

from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ContextTypes
from states import LOGISTICS, LOCATION, PHOTOS

async def logistics_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle transport selection"""
    choice = update.message.text.strip()
    context.user_data['transport_method'] = choice
    
    if "treilerit" in choice.lower() or "tow" in choice.lower():
        context.user_data['needs_tow'] = True
        if context.user_data.get('language') == 'ee':
            msg = "Vajan treilerit valitud.\n\nPalun saatke oma asukoht (Live Location) nii, et me saame transportikulu arvutada."
            location_button = KeyboardButton("📍 Saada asukoht", request_location=True)
        else:
            msg = "Need tow selected.\n\nPlease send your location (Live Location) so we can calculate transport costs."
            location_button = KeyboardButton("📍 Send Location", request_location=True)
        
        keyboard = [[location_button]]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        await update.message.reply_text(msg, reply_markup=reply_markup)
        return LOCATION
    else:
        context.user_data['needs_tow'] = False
        if context.user_data.get('language') == 'ee':
            msg = "Toon ise valitud.\n\nNüüd palun saatke 3-4 selget fotot sõidukist eri nurkadest:\n• Eest\n• Tagant\n• Külg\n• Salong (kui võimalik)"
        else:
            msg = "Bring myself selected.\n\nNow please send 3-4 clear photos of the vehicle from different angles:\n• Front\n• Back\n• Side\n• Interior (if possible)"
        
        await update.message.reply_text(msg)
        return PHOTOS


async def location_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Store tow location then move to photo collection."""
    context.user_data['location'] = {
        'latitude': update.message.location.latitude,
        'longitude': update.message.location.longitude,
    }

    if context.user_data.get('language') == 'ee':
        msg = "Asukoht saadetud! Aitäh.\n\nNüüd palun saatke 3-4 selget fotot sõidukist eri nurkadest:\n• Eest\n• Tagant\n• Külg\n• Salong (kui võimalik)"
    else:
        msg = "Location received! Thank you.\n\nNow please send 3-4 clear photos of the vehicle from different angles:\n• Front\n• Back\n• Side\n• Interior (if possible)"

    await update.message.reply_text(msg)
    return PHOTOS
