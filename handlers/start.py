"""
Start handler - Language selection and welcome message
"""

from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, KeyboardButton, BotCommand
from telegram.constants import BotCommandScopeType
from telegram import BotCommandScopeChat
from telegram.ext import ContextTypes
from states import LANGUAGE, VEHICLE_PLATE, WELCOME
import json
from config import ADMIN_TELEGRAM_USER_ID

def load_translations():
    """Load translation files"""
    translations = {}
    try:
        with open('locale/ee.json', 'r', encoding='utf-8') as f:
            translations['ee'] = json.load(f)
        with open('locale/en.json', 'r', encoding='utf-8') as f:
            translations['en'] = json.load(f)
        with open('locale/ru.json', 'r', encoding='utf-8') as f:
            translations['ru'] = json.load(f)
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
            },
            'ru': {
                'welcome': "Добро пожаловать в Romupunkt!\n\nМы поможем быстро и легально утилизировать ваш автомобиль.",
                'language_selected': "Язык выбран: {lang}",
                'start_button': "🇪🇪 Eesti",
                'english_button': "🇬🇧 English"
            }
        }
    return translations

translations = load_translations()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Send welcome message and language selection"""
    context.user_data.clear()
    keyboard = [
        [KeyboardButton("🇪🇪 Eesti"), KeyboardButton("🇬🇧 English"), KeyboardButton("🇷🇺 Русский")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, is_persistent=True)
    
    await update.message.reply_text(
        "Vali keel:",
        reply_markup=reply_markup
    )
    return LANGUAGE

async def language_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle language selection"""
    user_choice = update.message.text
    user_choice_l = (user_choice or "").strip().lower()
    
    if user_choice and ("Eesti" in user_choice or "eesti" in user_choice_l):
        lang = 'ee'
        lang_name = "Eesti"
        start_text = "▶️ Alusta"
    elif user_choice and ("Рус" in user_choice or "russian" in user_choice_l or "ru" == user_choice_l):
        lang = 'ru'
        lang_name = "Русский"
        start_text = "▶️ Начать"
    elif user_choice and ("English" in user_choice or "english" in user_choice_l or "en" == user_choice_l):
        lang = 'en'
        lang_name = "English"
        start_text = "▶️ Start"

    else:
        keyboard = [
            [KeyboardButton("🇪🇪 Eesti"), KeyboardButton("🇬🇧 English"), KeyboardButton("🇷🇺 Русский")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, is_persistent=True)
        await update.message.reply_text(
            "Vali keel:",
            reply_markup=reply_markup,
        )
        return LANGUAGE

    context.user_data['language'] = lang

    try:
        chat = update.effective_chat
        chat_id = chat.id if chat else None
        if chat_id is not None:
            if lang == 'ee':
                commands = [
                    BotCommand('start', 'Alusta'),
                    BotCommand('new', 'Uus päring'),
                ]
                admin_desc = 'Admin: päringud'
            elif lang == 'ru':
                commands = [
                    BotCommand('start', 'Старт'),
                    BotCommand('new', 'Новая заявка'),
                ]
                admin_desc = 'Админ: заявки'
            else:
                commands = [
                    BotCommand('start', 'Start'),
                    BotCommand('new', 'New inquiry'),
                ]
                admin_desc = 'Admin: leads'

            user = update.effective_user
            if (
                getattr(chat, "type", None) == "private"
                and user is not None
                and ADMIN_TELEGRAM_USER_ID > 0
                and user.id == ADMIN_TELEGRAM_USER_ID
            ):
                commands.append(BotCommand('leads', admin_desc))

            await context.bot.set_my_commands(commands, scope=BotCommandScopeChat(chat_id))
    except Exception:
        pass

    t = translations.get(lang, translations.get('en', {}))
    welcome_msg = t.get('welcome', '')
    legal_note = t.get('legal_note', '')
    selected_msg_tpl = t.get('language_selected', "Language selected: {lang}")
    selected_msg = selected_msg_tpl.format(lang=lang_name)

    await update.message.reply_text(f"{selected_msg}\n\n{welcome_msg}\n\n{legal_note}")
 
    keyboard = [[KeyboardButton(start_text)]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, is_persistent=True)
    if lang == 'ee':
        msg = "Kui olete valmis, vajutage 'Alusta'."
    elif lang == 'ru':
        msg = "Когда будете готовы, нажмите 'Начать'."
    else:
        msg = "When you're ready, tap 'Start'."

    await update.message.reply_text(msg, reply_markup=reply_markup)
    return WELCOME


async def welcome_continue(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = context.user_data.get('language', 'en')
    text = (update.message.text or '').strip().lower()

    if lang == 'ee':
        start_text = "▶️ Alusta"
    elif lang == 'ru':
        start_text = "▶️ Начать"
    else:
        start_text = "▶️ Start"

    keyboard = [[KeyboardButton(start_text)]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, is_persistent=True)

    is_start = False
    if lang == 'ee' and 'alusta' in text:
        is_start = True
    elif lang == 'ru' and ('нач' in text or 'start' == text):
        is_start = True
    elif lang == 'en' and 'start' in text:
        is_start = True

    if not is_start:
        if lang == 'ee':
            msg = "Vajutage 'Alusta', et jätkata."
        elif lang == 'ru':
            msg = "Нажмите 'Начать', чтобы продолжить."
        else:
            msg = "Tap 'Start' to continue."
        await update.message.reply_text(msg, reply_markup=reply_markup)
        return WELCOME

    t = translations.get(lang, translations.get('en', {}))
    plate_msg = t.get('plate_prompt', "Please enter your vehicle's license plate number (example: 123 ABC):")
    await update.message.reply_text(plate_msg, reply_markup=ReplyKeyboardRemove())
    return VEHICLE_PLATE
