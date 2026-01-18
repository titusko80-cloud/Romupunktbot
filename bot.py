#!/usr/bin/env python3
"""
Romupunkt Bot - Estonian Car Dismantling Market Bot
A specialized Telegram bot for collecting vehicle data and handling
legal requirements for car dismantling in Estonia.
"""

import asyncio
import logging
from telegram import BotCommand, BotCommandScopeAllPrivateChats, BotCommandScopeChat, Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ConversationHandler, ContextTypes, CallbackQueryHandler
from telegram.ext import PicklePersistence
from config import BOT_TOKEN, ADMIN_TELEGRAM_USER_ID
from handlers.start import start, language_selection, welcome_continue
from handlers.admin import leads_command, admin_lead_action_callback, offer_response_callback, admin_price_message, admin_archive_callback, admin_delete_callback
from handlers.vehicle import plate_validation, owner_name, owner_confirm, curb_weight
from handlers.photos import photo_collection, photo_text, _done_keyboard
from handlers.logistics import logistics_selection_final, location_received
from handlers.finalize import phone_number, handle_share_button
from database.models import init_db
from states import (
    LANGUAGE,
    WELCOME,
    VEHICLE_PLATE,
    OWNER_NAME,
    OWNER_CONFIRM,
    CURB_WEIGHT,
    PHOTOS,
    LOGISTICS,
    LOCATION,
    PHONE,
)

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def main():
    """Start the bot."""
    # Initialize database
    init_db()
    
    # Set up persistence for concurrency safety
    persistence = PicklePersistence(filepath='bot_data.pkl', on_flush=False)
    
    async def _post_init(app: Application) -> None:
        """Set up bot descriptions and commands"""
        try:
            # Set honest multilingual descriptions for empty chat window
            descriptions = {
                'et': '💰 ROMUPUNKT: Ostame teie vana auto rahaks. Saada andmed ja pildid – teeme pakkumise.',
                'en': '💰 ROMUPUNKT: Buy your old car for cash. Send details and photos – we make an offer.',
                'ru': '💰 ROMUPUNKT: Купите вашу старую машину за наличные. Отправьте данные и фото – мы сделаем предложение.'
            }
            
            # Set descriptions for all languages
            for lang_code, desc in descriptions.items():
                try:
                    await application.bot.set_my_description(description=desc, language_code=lang_code)
                    logger.info(f"✅ Bot description set for language: {lang_code}")
                except Exception as e:
                    logger.warning(f"❌ Failed to set description for {lang_code}: {e}")
            
            # Set honest multilingual profile bio
            about_texts = {
                'et': (
                    '�️ ROMUPUNKT\n\n'
                    'Autode ost ja lammutamine Eestis.\n'
                    'Ostme vanu, vigastatud ja soovimatuid autosid.\n'
                    '✅ Pakkumised andmete põhjal\n'
                    '✅ Ametlik lammutustõend\n'
                    '✅ Sõiduki eemaldamine registrist\n\n'
                    'Saada andmed ja pildid pakkumise saamiseks!'
                ),
                'ru': (
                    '�️ ROMUPUNKT\n\n'
                    'Скупка и утилизация автомобилей в Эстонии.\n'
                    'Покупаем старые, поврежденные и ненужные автомобили.\n'
                    '✅ Предложения на основе данных\n'
                    '✅ Официальная справка об утилизации\n'
                    '✅ Снятие с учета\n\n'
                    'Пришлите данные и фото для получения предложения!'
                ),
                'en': (
                    '�️ ROMUPUNKT\n\n'
                    'Car buying and dismantling in Estonia.\n'
                    'We buy old, damaged, and unwanted cars.\n'
                    '✅ Offers based on data\n'
                    '✅ Official destruction certificate\n'
                    '✅ Vehicle deregistration\n\n'
                    'Send details and photos to get an offer!'
                )
            }
            
            for lang_code, about_text in about_texts.items():
                try:
                    if hasattr(application.bot, "set_my_short_description"):
                        await application.bot.set_my_short_description(short_description=about_text, language_code=lang_code)
                        logger.info(f"✅ Bot short description set for language: {lang_code}")
                    elif hasattr(application.bot, "set_my_about_text"):
                        await application.bot.set_my_about_text(about_text=about_text, language_code=lang_code)
                        logger.info(f"✅ Bot about text set for language: {lang_code}")
                except Exception as e:
                    logger.warning(f"❌ Failed to set about text for {lang_code}: {e}")
                    
        except Exception as e:
            logger.warning("Failed to set bot descriptions: %s", e)
        
        # Set commands for all users
        try:
            commands = [
                BotCommand('start', 'Start / Start'),
                BotCommand('new', 'New inquiry / Uus päring / Новая заявка'),
            ]
            await application.bot.set_my_commands(commands, scope=BotCommandScopeAllPrivateChats())
            logger.info("Bot commands set for all users")
        except Exception as e:
            logger.warning("Failed to set bot commands: %s", e)
        
        # Set commands for admin
        if ADMIN_TELEGRAM_USER_ID and ADMIN_TELEGRAM_USER_ID > 0:
            try:
                commands = [
                    BotCommand("start", "Alusta"),
                    BotCommand("new", "Uus päring"),
                    BotCommand("leads", "Admin: päringud"),
                ]
                await application.bot.set_my_commands(commands, scope=BotCommandScopeChat(ADMIN_TELEGRAM_USER_ID))
            except Exception:
                pass

    application = Application.builder().token(BOT_TOKEN).post_init(_post_init).persistence(persistence).build()

    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler('start', start),
            CommandHandler('new', start),
            MessageHandler(filters.Regex(r'^🔄'), start),
        ],
        states={
            LANGUAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, language_selection)],
            WELCOME: [MessageHandler(filters.TEXT & ~filters.COMMAND, welcome_continue)],
            VEHICLE_PLATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, plate_validation)],
            OWNER_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, owner_name)],
            OWNER_CONFIRM: [MessageHandler(filters.TEXT & ~filters.COMMAND, owner_confirm)],
            CURB_WEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, curb_weight)],
            LOGISTICS: [
                CallbackQueryHandler(logistics_selection_final, pattern="^LOGISTICS_"),
            ],
            PHOTOS: [
                MessageHandler(filters.PHOTO | filters.Document.IMAGE, photo_collection),
                MessageHandler(filters.Regex(r"^✅"), photo_text),
            ],
            LOCATION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, location_received),
                MessageHandler(filters.LOCATION, location_received),
            ],
            PHONE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, phone_number),
            ],
        },
        fallbacks=[
            CommandHandler('start', start),
            CommandHandler('new', start),
            MessageHandler(filters.Regex(r'^🔄'), start),
        ],
        per_chat=True,     # ✅ DEFAULT, EXPLICIT
        per_message=True,
    )
    
    application.add_handler(conv_handler)
    
    # Start the Bot
    application.run_polling()

if __name__ == '__main__':
    main()
