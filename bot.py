#!/usr/bin/env python3
"""
Romupunkt Bot - Estonian Car Dismantling Market Bot
A specialized Telegram bot for collecting vehicle data and handling
legal requirements for car dismantling in Estonia.
"""

# 🔥 DEBUG: Find actual running directory
import sys
print("🔥 BOT.PY PATH:", __file__)
print("🔥 PYTHONPATH:")
for p in sys.path:
    print("   ", p)

import asyncio
import logging
from telegram import BotCommand
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ConversationHandler
from telegram.ext import PicklePersistence
from config import BOT_TOKEN, ADMIN_TELEGRAM_USER_ID
from handlers.start import start, language_selection, welcome_continue
from handlers.admin import leads_command, admin_lead_action_callback, offer_response_callback, admin_price_message, admin_archive_callback, admin_delete_callback
from handlers.vehicle import plate_validation, owner_name, owner_confirm, curb_weight
from handlers.photos import photo_collection, photo_text, _done_keyboard
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

# Media group handler - defined outside main function
async def handle_media_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle ALL photos - both media groups and single photos"""
    logger.info(f"Media group handler triggered! User: {update.effective_user.id}, Message type: {type(update.message)}")
    
    # Initialize photos array if needed
    if 'photos' not in context.user_data:
        context.user_data['photos'] = []
        context.user_data['last_response_time'] = 0
    
    # Create session_id if not exists
    if 'session_id' not in context.user_data:
        import uuid
        context.user_data['session_id'] = str(uuid.uuid4())
        logger.info(f"Created session {context.user_data['session_id']} for user {update.effective_user.id}")
    
    # Process each photo in the message
    photos_in_message = 0
    
    # Handle photo uploads
    if update.message.photo:
        # Each message = one photo (but with multiple sizes)
        photos_in_message = 1
        
        # Get the smallest size for admin (thumbnail)
        file_id = update.message.photo[0].file_id  # Smallest size
        
        # Store the photo in both context and session database
        context.user_data['photos'].append(file_id)
        if 'photo_count' not in context.user_data:
            context.user_data['photo_count'] = 0
        context.user_data['photo_count'] += 1
        
        # Also save to session database for Done button to work
        from database.models import save_session_photo
        save_session_photo(update.effective_user.id, context.user_data['session_id'], file_id)
        
        logger.info(f"Photo saved: {file_id} (message {photos_in_message} photo, total: {context.user_data['photo_count']})")
    
    # Handle document uploads (images sent as documents)
    elif update.message.document and (update.message.document.mime_type or "").startswith("image/"):
        file_id = update.message.document.file_id
        
        # Store the photo in both context and session database
        context.user_data['photos'].append(file_id)
        if 'photo_count' not in context.user_data:
            context.user_data['photo_count'] = 0
        context.user_data['photo_count'] += 1
        photos_in_message += 1
        
        # Also save to session database for Done button to work
        from database.models import save_session_photo
        save_session_photo(update.effective_user.id, context.user_data['session_id'], file_id)
        
        logger.info(f"Document photo saved: {file_id}")
    else:
        logger.warning(f"Media group handler called but no photo/document found. Message: {update.message}")
    
    # Smart response logic - only show Done button after first photo
    total_count = context.user_data['photo_count']
    
    # Only show Done button after first photo, no counting messages
    if total_count == 1:
        # First photo - show Done button only
        lang = context.user_data.get('language')
        if lang == 'ee':
            msg = "✅ Valmis"
        elif lang == 'ru':
            msg = "✅ Готово"
        else:
            msg = "✅ Done"
        await update.message.reply_text(msg, reply_markup=_done_keyboard(lang))
    elif total_count >= 5:
        # Maximum reached - show Done button with message
        lang = context.user_data.get('language')
        if lang == 'ee':
            msg = "Maksimum 5 fotot. ✅ Valmis"
        elif lang == 'ru':
            msg = "Максимум 5 фото. ✅ Готово"
        else:
            msg = "Maximum 5 photos. ✅ Done"
        await update.message.reply_text(msg, reply_markup=_done_keyboard(lang))
    # For photos 2-4: NO MESSAGE - let user continue smoothly
    return


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
                'et': 'Autode ost ja lammutamine. Saada andmed ja pildid, me teeme pakkumise. Vormistame lammutustõendi.',
                'en': 'Car buying and dismantling. Send details and photos, and we will make an offer. We provide destruction certificate and deregister the vehicle.'
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
            PHOTOS: [
                MessageHandler(filters.PHOTO, photo_collection),
                MessageHandler(filters.Document.IMAGE, photo_collection),
                MessageHandler(filters.TEXT & ~filters.COMMAND, photo_text),
            ],
            LOGISTICS: [MessageHandler(filters.TEXT & ~filters.COMMAND, logistics_selection)],
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
