#!/usr/bin/env python3

import logging
import signal
import sys

from telegram import BotCommand, BotCommandScopeAllPrivateChats, BotCommandScopeChat, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    PicklePersistence,
    filters,
)

from config import BOT_TOKEN, ADMIN_TELEGRAM_USER_ID
from handlers.start import start, language_selection, welcome_continue
from handlers.admin import (
    leads_command,
    admin_lead_action_callback,
    offer_response_callback,
    offer_counter_callback,
    counter_offer_message,
    admin_price_message,
    admin_archive_callback,
    admin_delete_callback,
)
from handlers.vehicle import plate_validation, owner_name, owner_confirm, curb_weight
from handlers.photos import photo_collection, photo_text
from handlers.logistics import logistics_selection, location_received
from handlers.finalize import phone_number
from database.models import init_db
from states import *

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger.info("BOOT: bot process started")


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message:
        await update.message.reply_text("Canceled")
    return ConversationHandler.END


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.exception("Unhandled exception", exc_info=context.error)


def main():
    init_db()

    persistence = PicklePersistence(
        filepath="bot_data.pkl",
    )

    application = Application.builder().token(BOT_TOKEN).persistence(persistence).build()
    application.add_error_handler(error_handler)

    async def post_init(app: Application):
        await app.bot.set_my_commands(
            [
                BotCommand("start", "Start"),
                BotCommand("new", "New inquiry"),
            ],
            scope=BotCommandScopeAllPrivateChats(),
        )

        if ADMIN_TELEGRAM_USER_ID:
            await app.bot.set_my_commands(
                [
                    BotCommand("start", "Start"),
                    BotCommand("new", "New inquiry"),
                    BotCommand("leads", "Admin leads"),
                ],
                scope=BotCommandScopeChat(ADMIN_TELEGRAM_USER_ID),
            )

    application.post_init = post_init

    application.add_handler(CallbackQueryHandler(offer_response_callback, pattern=r"^offer_"))
    application.add_handler(CallbackQueryHandler(offer_counter_callback, pattern=r"^offer_counter"))
    application.add_handler(CallbackQueryHandler(admin_lead_action_callback, pattern=r"^admin_reply"))
    application.add_handler(CallbackQueryHandler(admin_archive_callback, pattern=r"^admin_archive"))
    application.add_handler(CallbackQueryHandler(admin_delete_callback, pattern=r"^admin_delete"))

    if ADMIN_TELEGRAM_USER_ID:
        application.add_handler(CommandHandler("leads", leads_command))
        application.add_handler(
            MessageHandler(
                filters.Chat(chat_id=ADMIN_TELEGRAM_USER_ID) & filters.TEXT & ~filters.COMMAND,
                admin_price_message,
            ),
            group=0,
        )

    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, counter_offer_message),
        group=1,
    )

    conv = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            CommandHandler("new", start),
        ],
        states={
            LANGUAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, language_selection)],
            WELCOME: [MessageHandler(filters.TEXT & ~filters.COMMAND, welcome_continue)],
            VEHICLE_PLATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, plate_validation)],
            OWNER_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, owner_name)],
            OWNER_CONFIRM: [MessageHandler(filters.TEXT & ~filters.COMMAND, owner_confirm)],
            CURB_WEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, curb_weight)],
            LOGISTICS: [MessageHandler(filters.TEXT & ~filters.COMMAND, logistics_selection)],
            PHOTOS: [
                MessageHandler(filters.PHOTO | filters.Document.IMAGE, photo_collection),
                MessageHandler(filters.Regex("^✅"), photo_text),
            ],
            LOCATION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, location_received),
                MessageHandler(filters.LOCATION, location_received),
            ],
            PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, phone_number)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        name="main_conversation",
        persistent=True,
    )

    application.add_handler(conv, group=2)

    def shutdown(*_):
        logger.warning("Received shutdown signal")
        try:
            application.stop()
        except Exception:
            pass
        sys.exit(0)

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)

    logger.info("BOOT: starting polling")
    application.run_polling(
        drop_pending_updates=True,
        allowed_updates=Update.ALL_TYPES,
    )


if __name__ == "__main__":
    main()
