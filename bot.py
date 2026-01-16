#!/usr/bin/env python3
"""
Romupunkt Bot - Estonian Car Dismantling Market Bot
A specialized Telegram bot for collecting vehicle data and handling
legal requirements for car dismantling in Estonia.
"""

import asyncio
import logging
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ConversationHandler
from config import BOT_TOKEN
from handlers.start import start, language_selection
from handlers.vehicle import vehicle_info, plate_validation, owner_name, curb_weight
from handlers.photos import photo_collection
from handlers.logistics import logistics_selection, location_received
from handlers.finalize import phone_number
from database.models import init_db
from states import (
    LANGUAGE,
    VEHICLE_PLATE,
    OWNER_NAME,
    CURB_WEIGHT,
    COMPLETENESS,
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
    
    # Create the Application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add conversation handler
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            LANGUAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, language_selection)],
            VEHICLE_PLATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, plate_validation)],
            OWNER_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, owner_name)],
            CURB_WEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, curb_weight)],
            COMPLETENESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, vehicle_info)],
            LOGISTICS: [MessageHandler(filters.TEXT & ~filters.COMMAND, logistics_selection)],
            LOCATION: [MessageHandler(filters.LOCATION, location_received)],
            PHOTOS: [MessageHandler(filters.PHOTO, photo_collection)],
            PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, phone_number)],
        },
        fallbacks=[CommandHandler('start', start)],
    )
    
    application.add_handler(conv_handler)
    
    # Start the Bot
    application.run_polling()

if __name__ == '__main__':
    main()
