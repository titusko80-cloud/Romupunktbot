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
from config import BOT_TOKEN, ADMIN_TELEGRAM_USER_ID
from handlers.start import start, language_selection, welcome_continue
from handlers.admin import leads_command, admin_lead_action_callback, offer_response_callback, admin_price_message, admin_archive_callback
from handlers.vehicle import vehicle_info, plate_validation, owner_name, owner_confirm, curb_weight, missing_parts
from handlers.photos import photo_collection, photo_text
from handlers.logistics import logistics_selection, location_received
from handlers.finalize import phone_number, handle_share_button
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
    
    async def _post_init(app: Application) -> None:
        """Set up bot descriptions and commands"""
        try:
            # Set bot descriptions for each language (pre-start empty chat text)
            await app.bot.set_my_description(
                description="🏎️ ROMUPUNKT\n\nOstame autosid, millega omanik ei taha enam tegeleda.\n\nKui auto seisab, on katki või lihtsalt mittevajalik — vajuta START.",
                language_code="et"
            )
            logger.info("✅ Bot description set for Estonian")
            
            await app.bot.set_my_description(
                description="🏎️ ROMUPUNKT\n\nПокупаем автомобили, с которыми владелец больше не хочет возиться.\n\nЕсли машина стоит, сломана или просто не нужна — нажми START.",
                language_code="ru"
            )
            logger.info("✅ Bot description set for Russian")
            
            await app.bot.set_my_description(
                description="🏎️ ROMUPUNKT\n\nWe buy cars people no longer want to deal with.\n\nIf the car is standing, broken or simply unwanted — press START.",
                language_code="en"
            )
            logger.info("✅ Bot description set for English")
            
        except Exception as e:
            logger.warning("Failed to set bot descriptions: %s", e)
        
        # Set commands for all users
        try:
            await app.bot.set_my_commands(
                [
                    BotCommand("start", "Alusta"),
                    BotCommand("new", "Uus päring"),
                ]
            )
        except Exception:
            pass

        if ADMIN_TELEGRAM_USER_ID and ADMIN_TELEGRAM_USER_ID > 0:
            try:
                from telegram import BotCommandScopeChat

                await app.bot.set_my_commands(
                    [
                        BotCommand("start", "Alusta"),
                        BotCommand("new", "Uus päring"),
                        BotCommand("leads", "Admin: päringud"),
                    ],
                    scope=BotCommandScopeChat(ADMIN_TELEGRAM_USER_ID),
                )
            except Exception:
                pass

    application = Application.builder().token(BOT_TOKEN).post_init(_post_init).build()

    application.add_handler(
        MessageHandler(
            filters.User(user_id=ADMIN_TELEGRAM_USER_ID)
            & filters.TEXT
            & ~filters.COMMAND
            & filters.Regex(r"(?i).*(€|eur).*"),
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
            PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, phone_number)],
        },
        fallbacks=[
            CommandHandler('start', start),
            CommandHandler('new', start),
            MessageHandler(filters.Regex(r'^🔄'), start),
        ],
    )
    
    application.add_handler(conv_handler)

    application.add_handler(CommandHandler('leads', leads_command))

    application.add_handler(MessageHandler(filters.User(user_id=ADMIN_TELEGRAM_USER_ID) & filters.Regex(r'^🔄'), start))

    from telegram.ext import CallbackQueryHandler
    application.add_handler(CallbackQueryHandler(admin_lead_action_callback, pattern=r'^admin_reply:'))
    application.add_handler(CallbackQueryHandler(admin_archive_callback, pattern=r'^admin_archive:'))
    application.add_handler(CallbackQueryHandler(offer_response_callback, pattern=r'^offer_(accept|reject):'))

    # Share bot button handler (outside conversation)
    application.add_handler(MessageHandler(filters.Regex(r'🔗 (Jaga sõbraga, kellel on romu hoovis|Поделись с другом, у которого машина на разборку|Share with a friend who\'s scrapping a car)'), handle_share_button))
    
    # Start the Bot
    application.run_polling()

if __name__ == '__main__':
    main()
