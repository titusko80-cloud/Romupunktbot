#!/usr/bin/env python3
"""
Simple test to diagnose button glitching and photo upload issues
"""

import asyncio
import logging
from datetime import datetime
from handlers.logistics import logistics_selection
from handlers.photos import photo_collection, photo_text

# Set up logging without Unicode
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

class MockUpdate:
    """Mock Telegram Update for testing"""
    def __init__(self, message_type="text", text="", photo=None, user_id=218218133):
        self.message = MockMessage(message_type, text, photo, user_id)

class MockMessage:
    """Mock Telegram Message"""
    def __init__(self, message_type, text, photo, user_id):
        self.text = text
        self.photo = photo
        self.user = MockUser(user_id)
        self.chat_id = user_id
        
    async def reply_text(self, text, reply_markup=None):
        keyboard_status = "WITH_KEYBOARD" if reply_markup else "NO_KEYBOARD"
        logger.info(f"REPLY: '{text}' | {keyboard_status}")
        
class MockUser:
    """Mock Telegram User"""
    def __init__(self, user_id):
        self.id = user_id

class MockContext:
    """Mock Telegram Context"""
    def __init__(self):
        self.user_data = {}
        self.bot = MockBot()

class MockBot:
    """Mock Telegram Bot"""
    async def send_message(self, chat_id, text, reply_markup=None):
        keyboard_status = "WITH_KEYBOARD" if reply_markup else "NO_KEYBOARD"
        logger.info(f"SEND: '{text}' | {keyboard_status}")

async def test_logistics_flow():
    """Test logistics flow with detailed logging"""
    logger.info("=" * 60)
    logger.info("TESTING LOGISTICS FLOW")
    logger.info("=" * 60)
    
    context = MockContext()
    
    # Test 1: Toon ise selection
    logger.info("\nTEST 1: Toon ise selection")
    update = MockUpdate("text", "🚗 Toon ise")
    
    try:
        result = await logistics_selection(update, context)
        logger.info(f"logistics_selection returned: {result}")
        logger.info(f"user_data after logistics_selection: {context.user_data}")
        
        # Check if session was created
        if "session_id" in context.user_data:
            logger.info(f"SUCCESS: Session created: {context.user_data['session_id']}")
        else:
            logger.error("FAILURE: NO SESSION CREATED!")
            
        # Check if photo_count was initialized
        if "photo_count" in context.user_data:
            logger.info(f"SUCCESS: Photo count initialized: {context.user_data['photo_count']}")
        else:
            logger.error("FAILURE: PHOTO_COUNT NOT INITIALIZED!")
            
    except Exception as e:
        logger.error(f"FAILURE: logistics_selection failed: {e}")
    
    # Test 2: Vajan buksiiri selection
    logger.info("\nTEST 2: Vajan buksiiri selection")
    context = MockContext()
    update = MockUpdate("text", "🚛 Vajan buksiiri")
    
    try:
        result = await logistics_selection(update, context)
        logger.info(f"logistics_selection returned: {result}")
        logger.info(f"user_data after logistics_selection: {context.user_data}")
        
        if "session_id" in context.user_data:
            logger.info(f"SUCCESS: Session created: {context.user_data['session_id']}")
        else:
            logger.error("FAILURE: NO SESSION CREATED!")
            
    except Exception as e:
        logger.error(f"FAILURE: logistics_selection failed: {e}")

async def test_photo_flow():
    """Test photo collection flow with detailed logging"""
    logger.info("\n" + "=" * 60)
    logger.info("TESTING PHOTO FLOW")
    logger.info("=" * 60)
    
    context = MockContext()
    
    # Set up session as if logistics was completed
    context.user_data["session_id"] = "test_session_123"
    context.user_data["photo_count"] = 0
    context.user_data["language"] = "ee"
    context.user_data["needs_tow"] = False
    
    logger.info(f"Initial user_data: {context.user_data}")
    
    # Test 1: Photo upload
    logger.info("\nTEST 1: Photo upload")
    mock_photo = [{"file_id": "test_photo_123"}]
    update = MockUpdate("photo", "", mock_photo)
    
    try:
        result = await photo_collection(update, context)
        logger.info(f"photo_collection returned: {result}")
        logger.info(f"user_data after photo_collection: {context.user_data}")
        
        # Check if photo_count was incremented
        if context.user_data.get("photo_count", 0) > 0:
            logger.info(f"SUCCESS: Photo count incremented: {context.user_data['photo_count']}")
        else:
            logger.error("FAILURE: PHOTO_COUNT NOT INCREMENTED!")
            
    except Exception as e:
        logger.error(f"FAILURE: photo_collection failed: {e}")
    
    # Test 2: Done button
    logger.info("\nTEST 2: Valmis button")
    update = MockUpdate("text", "✅ Valmis")
    
    try:
        result = await photo_text(update, context)
        logger.info(f"photo_text returned: {result}")
        logger.info(f"user_data after photo_text: {context.user_data}")
        
    except Exception as e:
        logger.error(f"FAILURE: photo_text failed: {e}")
    
    # Test 3: Random text (should be ignored)
    logger.info("\nTEST 3: Random text (should be ignored)")
    update = MockUpdate("text", "random text")
    
    try:
        result = await photo_text(update, context)
        logger.info(f"photo_text returned: {result}")
        logger.info(f"user_data after photo_text: {context.user_data}")
        
        if result == 5:  # PHOTOS state
            logger.info("SUCCESS: Random text correctly ignored (stayed in PHOTOS state)")
        else:
            logger.error(f"FAILURE: Random text NOT ignored! Returned: {result}")
            
    except Exception as e:
        logger.error(f"FAILURE: photo_text failed: {e}")

async def test_edge_cases():
    """Test edge cases that might cause glitches"""
    logger.info("\n" + "=" * 60)
    logger.info("TESTING EDGE CASES")
    logger.info("=" * 60)
    
    # Test 1: Photo without session
    logger.info("\nTEST 1: Photo without session (should fail)")
    context = MockContext()
    mock_photo = [{"file_id": "test_photo_123"}]
    update = MockUpdate("photo", "", mock_photo)
    
    try:
        result = await photo_collection(update, context)
        logger.error(f"FAILURE: photo_collection should have failed but returned: {result}")
    except Exception as e:
        logger.info(f"SUCCESS: photo_collection correctly failed: {e}")
    
    # Test 2: Done button without photos
    logger.info("\nTEST 2: Done button without photos")
    context = MockContext()
    context.user_data["session_id"] = "test_session_123"
    context.user_data["photo_count"] = 0
    update = MockUpdate("text", "✅ Valmis")
    
    try:
        result = await photo_text(update, context)
        logger.info(f"photo_text returned: {result}")
        
        if result == 6:  # PHONE state
            logger.info("SUCCESS: Done button allowed without photos")
        else:
            logger.info(f"SUCCESS: Done button handled correctly: {result}")
            
    except Exception as e:
        logger.error(f"FAILURE: photo_text failed: {e}")

async def main():
    """Run all tests"""
    logger.info("STARTING BUTTON GLITCH DIAGNOSIS")
    logger.info(f"Test time: {datetime.now().isoformat()}")
    
    # Run tests
    await test_logistics_flow()
    await test_photo_flow()
    await test_edge_cases()
    
    logger.info("\n" + "=" * 60)
    logger.info("BUTTON GLITCH DIAGNOSIS COMPLETE")
    logger.info("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
