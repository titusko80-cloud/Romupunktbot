#!/usr/bin/env python3
"""
Final acceptance test for the bot flow
"""

import asyncio
import logging
from handlers.logistics import show_logistics_inline, logistics_selection
from handlers.photos import photo_collection, photo_text

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MockUpdate:
    def __init__(self, message_type="text", text="", photo=None, callback_query=None):
        self.message = MockMessage(message_type, text, photo)
        self.callback_query = callback_query

class MockMessage:
    def __init__(self, message_type, text, photo=None):
        self.text = text
        self.photo = photo
        self.user = MockUser()
        self.chat_id = 12345
        
    async def reply_text(self, text, reply_markup=None):
        logger.info(f"REPLY: '{text}' | Keyboard: {reply_markup is not None}")

class MockUser:
    def __init__(self):
        self.id = 12345

class MockQuery:
    def __init__(self, data, message):
        self.data = data
        self.message = message
        
    async def answer(self):
        logger.info(f"QUERY ANSWERED: {self.data}")
        
    async def edit_message_reply_markup(self, reply_markup):
        logger.info(f"KEYBOARD REMOVED: {reply_markup}")

class MockContext:
    def __init__(self):
        self.user_data = {}
        self.bot = MockBot()

class MockBot:
    async def send_message(self, chat_id, text, reply_markup=None):
        logger.info(f"SEND: '{text}' | Keyboard: {reply_markup is not None}")

async def test_flow():
    """Test the complete flow"""
    logger.info("=" * 60)
    logger.info("FINAL ACCEPTANCE TEST")
    logger.info("=" * 60)
    
    context = MockContext()
    
    # Step 1: Show logistics inline keyboard
    logger.info("\nSTEP 1: Show logistics inline keyboard")
    update = MockUpdate("text", "test")
    context.user_data["language"] = "ee"
    
    try:
        result = await show_logistics_inline(update, context)
        logger.info(f"show_logistics_inline returned: {result}")
    except Exception as e:
        logger.error(f"show_logistics_inline failed: {e}")
    
    # Step 2: Click "🚗 Toon ise"
    logger.info("\nSTEP 2: Click '🚗 Toon ise'")
    message = MockMessage("text", "test")
    query = MockQuery("LOGISTICS_SELF", message)
    update = MockUpdate("text", "test", None, query)
    
    try:
        result = await logistics_selection(update, context)
        logger.info(f"logistics_selection returned: {result}")
        logger.info(f"user_data: {context.user_data}")
        
        # Check session created
        if "session_id" in context.user_data:
            logger.info("✅ Session created successfully")
        else:
            logger.error("❌ Session not created")
            
        # Check photo_count initialized
        if "photo_count" in context.user_data:
            logger.info("✅ Photo count initialized")
        else:
            logger.error("❌ Photo count not initialized")
            
    except Exception as e:
        logger.error(f"logistics_selection failed: {e}")
    
    # Step 3: Upload photos
    logger.info("\nSTEP 3: Upload photos")
    # Mock photo structure as list of objects with file_id
    class MockPhoto:
        def __init__(self, file_id):
            self.file_id = file_id
    
    mock_photo = [MockPhoto("test_photo_123")]
    update = MockUpdate("photo", "", mock_photo)
    
    try:
        result = await photo_collection(update, context)
        logger.info(f"photo_collection returned: {result}")
        logger.info(f"user_data: {context.user_data}")
        
        if context.user_data.get("photo_count", 0) > 0:
            logger.info("✅ Photo count incremented")
        else:
            logger.error("❌ Photo count not incremented")
            
    except Exception as e:
        logger.error(f"photo_collection failed: {e}")
    
    # Step 4: Click Done button
    logger.info("\nSTEP 4: Click Done button")
    update = MockUpdate("text", "✅ Valmis")
    
    try:
        result = await photo_text(update, context)
        logger.info(f"photo_text returned: {result}")
        
        if result == 6:  # PHONE state
            logger.info("✅ Done button proceeded to phone")
        else:
            logger.error(f"❌ Done button failed: {result}")
            
    except Exception as e:
        logger.error(f"photo_text failed: {e}")
    
    logger.info("\n" + "=" * 60)
    logger.info("FINAL ACCEPTANCE TEST COMPLETE")
    logger.info("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_flow())
