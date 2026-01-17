#!/usr/bin/env python3
"""
Romupunkt Bot - Estonian Car Dismantling Market Bot
A specialized Telegram bot for collecting vehicle data and handling
legal requirements for car dismantling in Estonia.
"""

import asyncio
import logging
from telegram import BotCommand
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ConversationHandler
from telegram.ext import PicklePersistence
from config import BOT_TOKEN, ADMIN_TELEGRAM_USER_ID
from handlers.start import start, language_selection, welcome_continue
from handlers.admin import leads_command, admin_lead_action_callback, offer_response_callback, admin_price_message, admin_archive_callback, admin_delete_callback
from handlers.vehicle import vehicle_info, plate_validation, owner_name, owner_confirm, curb_weight, missing_parts
from handlers.photos import photo_collection, photo_text
from handlers.logistics import logistics_selection, location_received
from handlers.finalize import phone_number, handle_share_button, phone_country_code
from database.models import init_db
from states import (
    LANGUAGE,
    WELCOME,
    VEHICLE_PLATE,
    OWNER_NAME,
    OWNER_CONFIRM,
    CURB_WEIGHT,
    COMPLETENESS,
    MISSING_PARTS,
    LOGISTICS,
    LOCATION,
    PHOTOS,
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
            # Set professional multilingual descriptions for empty chat window
            descriptions = {
                'et': '🏁 ROMUPUNKT: Müü oma auto kiirelt! 🏎️ Saa pakkumine 60 sekundiga ja ametlik lammutustõend. Vajuta START, et alustada.',
                'ru': '🏁 ROMUPUNKT: Продайте свою машину быстро! 🏎️ Получите предложение за 60 секунд и официальную справку об утилизации. Нажмите START, чтобы начать.',
                'en': '🏁 ROMUPUNKT: Sell your car fast! 🏎️ Get a price quote in 60 seconds and an official destruction certificate. Press START to begin.'
            }
            
            # Set descriptions for all languages
            for lang_code, desc in descriptions.items():
                try:
                    await application.bot.set_my_description(description=desc, language_code=lang_code)
                    logger.info(f"✅ Bot description set for language: {lang_code}")
                except Exception as e:
                    logger.warning(f"❌ Failed to set description for {lang_code}: {e}")
            
            # Set professional multilingual profile bio
            about_texts = {
                'et': (
                    '🏁 ROMUPUNKT\n\n'
                    'Ametlik sõidukite lammutus teenus Eestis.\n'
                    'Ostame vanu, vigastatud ja soovimatuid autosid.\n'
                    '✅ Kiired pakkumised\n'
                    '✅ Tasuta sõiduki äravedu\n'
                    '✅ Ametlik lammutustõend\n'
                    '✅ Kohene makse\n\n'
                    'Võta ühendust pakkumise saamiseks!'
                ),
                'ru': (
                    '🏁 ROMUPUNKT\n\n'
                    'Официальная услуга утилизации автомобилей в Эстонии.\n'
                    'Покупаем старые, поврежденные и ненужные автомобили.\n'
                    '✅ Быстрые предложения\n'
                    '✅ Бесплатная эвакуация автомобиля\n'
                    '✅ Официальная справка об утилизации\n'
                    '✅ Мгновенная оплата\n\n'
                    'Свяжитесь с нами для получения предложения!'
                ),
                'en': (
                    '🏁 ROMUPUNKT\n\n'
                    'Official vehicle dismantling service in Estonia.\n'
                    'We buy old, damaged, and unwanted cars.\n'
                    '✅ Fast price quotes\n'
                    '✅ Free vehicle pickup\n'
                    '✅ Official destruction certificate\n'
                    '✅ Instant payment\n\n'
                    'Contact us for a quote today!'
                )
            }
            
            for lang_code, about_text in about_texts.items():
                try:
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
            application.bot.set_my_commands(commands, scope=BotCommandScopeAllPrivateChats())
            logger.info("Bot commands set for all users")
        except Exception as e:
            logger.warning("Failed to set bot commands: %s", e)
        
        # Set commands for admin
        if ADMIN_TELEGRAM_USER_ID and ADMIN_TELEGRAM_USER_ID > 0:
            try:
                from telegram import BotCommandScopeChat

                commands = [
                    BotCommand("start", "Alusta"),
                    BotCommand("new", "Uus päring"),
                    BotCommand("leads", "Admin: päringud"),
                ]
                application.bot.set_my_commands(commands, scope=BotCommandScopeChat(ADMIN_TELEGRAM_USER_ID))
            except Exception:
                pass

    application = Application.builder().token(BOT_TOKEN).post_init(_post_init).persistence(persistence).build()

    application.add_handler(
        MessageHandler(
            filters.User(user_id=ADMIN_TELEGRAM_USER_ID)
            & filters.TEXT
            & ~filters.COMMAND
            & filters.Regex(r".*\d.*"),
            admin_price_message,
            block=False,
        )
    )
    
    # Add conversation handler
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
            COMPLETENESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, vehicle_info)],
            MISSING_PARTS: [MessageHandler(filters.TEXT & ~filters.COMMAND, missing_parts)],
            LOGISTICS: [MessageHandler(filters.TEXT & ~filters.COMMAND, logistics_selection)],
            LOCATION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, location_received),
                MessageHandler(filters.LOCATION, location_received),
            ],
            PHOTOS: [
                MessageHandler(filters.PHOTO, photo_collection),
                MessageHandler(filters.Document.IMAGE, photo_collection),
                MessageHandler(filters.TEXT & ~filters.COMMAND, photo_text),
            ],
            PHONE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, phone_country_code),
                MessageHandler(filters.TEXT & ~filters.COMMAND, phone_number),
            ],
        },
        fallbacks=[
            CommandHandler('start', start),
            CommandHandler('new', start),
            MessageHandler(filters.Regex(r'^🔄'), start),
        ],
        block=False,  # Allow concurrent processing
    )
    
    application.add_handler(conv_handler)

    application.add_handler(CommandHandler('leads', leads_command))

    application.add_handler(MessageHandler(filters.User(user_id=ADMIN_TELEGRAM_USER_ID) & filters.Regex(r'^🔄'), start))

    from telegram.ext import CallbackQueryHandler
    application.add_handler(CallbackQueryHandler(admin_lead_action_callback, pattern=r'^admin_reply:'))
    application.add_handler(CallbackQueryHandler(admin_archive_callback, pattern=r'^admin_archive:'))
    application.add_handler(CallbackQueryHandler(admin_delete_callback, pattern=r'^admin_delete:'))
    application.add_handler(CallbackQueryHandler(offer_response_callback, pattern=r'^offer_(accept|reject):'))

    # Share bot button handler (outside conversation)
    application.add_handler(MessageHandler(filters.Regex(r'🔗 (Jaga sõbraga, kellel on romu hoovis|Поделись с другом, у которого машина на разборку|Share with a friend who\'s scrapping a car)'), handle_share_button))
    
    # Start the Bot
    application.run_polling()

if __name__ == '__main__':
    main()
