"""
Start handler - Language selection and welcome message
"""

from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ContextTypes
from states import LANGUAGE, VEHICLE_PLATE
import json

def load_translations():
    """Load translation files"""
    translations = {}
    try:
        with open('locale/ee.json', 'r', encoding='utf-8') as f:
            translations['ee'] = json.load(f)
        with open('locale/en.json', 'r', encoding='utf-8') as f:
            translations['en'] = json.load(f)
    except FileNotFoundError:
        # Fallback translations if files don't exist
        translations = {
            'ee': {
                'welcome': "Tere tulemast Romupunkti!\n\nMe aitame teie sõiduki kiirelt ja legaalselt lammutada. Valige keel:",
                'language_selected': "Keel valitud: {lang}\n\nAlustame sõiduki andmete kogumisega.",
                'start_button': "🇪🇪 Eesti",
                'english_button': "🇬🇧 English"
            },
            'en': {
                'welcome': "Welcome to Romupunkt!\n\nWe help you dismantle your vehicle quickly and legally. Choose your language:",
                'language_selected': "Language selected: {lang}\n\nLet's start collecting your vehicle information.",
                'start_button': "🇪🇪 Eesti",
                'english_button': "🇬🇧 English"
            }
        }
    return translations

translations = load_translations()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Send welcome message and language selection"""
    keyboard = [
        [KeyboardButton("🇪🇪 Eesti"), KeyboardButton("🇬🇧 English")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    
    await update.message.reply_text(
        "Welcome to Romupunkt!\n\nWe help you dismantle your vehicle quickly and legally. Choose your language:",
        reply_markup=reply_markup
    )
    return LANGUAGE

async def language_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle language selection"""
    user_choice = update.message.text
    
    if "Eesti" in user_choice or "eesti" in user_choice.lower():
        context.user_data['language'] = 'ee'
        lang_name = "Eesti"
        welcome_msg = "Tere tulemast Romupunkti!\n\nMe aitame teie sõiduki kiirelt ja legaalselt lammutada. Meie protsess on lihtne ja me kõik vajalikud dokumendid (ka lammutustõend)."
        plate_msg = "Sisestage oma sõiduki numberkood (näiteks: 123 ABC):"
    else:
        context.user_data['language'] = 'en'
        lang_name = "English"
        welcome_msg = "Welcome to Romupunkt!\n\nWe help you dismantle your vehicle quickly and legally. Our process is simple and we handle all necessary paperwork (including certificate of destruction)."
        plate_msg = "Please enter your vehicle's license plate number (example: 123 ABC):"
    
    await update.message.reply_text(f"Language selected: {lang_name}\n\n{welcome_msg}")
    await update.message.reply_text(plate_msg)
    
    return VEHICLE_PLATE
