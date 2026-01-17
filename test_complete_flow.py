#!/usr/bin/env python3
"""
Test the complete flow from photo upload to admin notification
Simulates the user journey without requiring Telegram API
"""

import os
import sys
import asyncio
from unittest.mock import Mock, AsyncMock

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database.models import init_db, save_lead, save_photo_file_id, get_lead_photos, get_lead_by_id
from handlers.finalize import _send_admin_notification

async def test_complete_flow():
    """Test the complete flow from photo upload to admin notification"""
    print("🧪 Testing Complete Photo Flow\n")
    
    # Initialize database
    init_db()
    print("✅ Database initialized")
    
    # Step 1: Simulate user submitting lead with photos
    print("\n📸 Step 1: Simulating photo uploads...")
    
    test_user_data = {
        'language': 'et',
        'plate_number': '789XYZ',
        'owner_name': 'Jaan Tamm',
        'is_owner': True,
        'curb_weight': 1200,
        'completeness': 'Poolik',
        'missing_parts': 'Uksed',
        'transport_method': '🚛 Vajan buksiiri',
        'needs_tow': True,
        'tow_address': 'Tallinn, Pärnu mnt 10',
        'location_latitude': 59.4370,
        'location_longitude': 24.7536,
        'photos': '',
        'phone_number': '+37252345678'
    }
    
    # Create lead (as done in photo_collection)
    lead_id = save_lead(test_user_data, 54321, 'jaantamm')
    print(f"✅ Lead created with ID: {lead_id}")
    
    # Simulate photo uploads (as done in photo_collection)
    test_file_ids = [
        "AgACAgQAAxkDAAICOGZxY7xPHOTO1A",
        "AgACAgQAAxkDAAICOGZxY7xPHOTO2B",
        "AgACAgQAAxkDAAICOGZxY7xPHOTO3C",
    ]
    
    for i, file_id in enumerate(test_file_ids, 1):
        save_photo_file_id(lead_id, file_id)
        print(f"✅ Photo {i} saved: {file_id[:25]}...")
    
    # Step 2: Verify photos are stored
    print("\n🔍 Step 2: Verifying photo storage...")
    photos = get_lead_photos(lead_id)
    print(f"✅ Retrieved {len(photos)} photos from database")
    
    if len(photos) == len(test_file_ids):
        print("✅ All photos stored correctly")
    else:
        print("❌ Photo count mismatch!")
        return False
    
    # Step 3: Test admin notification (mock context)
    print("\n📤 Step 3: Testing admin notification...")
    
    # Mock the context and bot
    mock_context = Mock()
    mock_bot = AsyncMock()
    mock_context.bot = mock_bot
    
    # Mock the send_media_group and send_message methods
    mock_bot.send_media_group = AsyncMock(return_value=None)
    mock_bot.send_message = AsyncMock(return_value=None)
    
    # Set admin ID for testing
    os.environ['ADMIN_TELEGRAM_USER_ID'] = '123456789'
    
    # Import after setting env var
    from config import ADMIN_TELEGRAM_USER_ID
    
    # Call the notification function
    await _send_admin_notification(mock_context, lead_id, '+37252345678')
    
    # Verify the bot methods were called
    if mock_bot.send_media_group.called:
        call_args = mock_bot.send_media_group.call_args
        media_group = call_args[1]['media']
        print(f"✅ send_media_group called with {len(media_group)} photos")
        
        # Check first photo has caption
        if media_group[0].caption:
            print("✅ First photo has caption")
            print(f"   Caption preview: {media_group[0].caption[:50]}...")
        else:
            print("❌ First photo missing caption")
            return False
    else:
        print("❌ send_media_group not called!")
        return False
    
    if mock_bot.send_message.called:
        print("✅ send_message called for control buttons")
        call_args = mock_bot.send_message.call_args
        reply_markup = call_args[1]['reply_markup']
        if reply_markup and reply_markup.inline_keyboard:
            buttons = [button.text for row in reply_markup.inline_keyboard for button in row]
            print(f"✅ Control buttons: {buttons}")
    else:
        print("❌ send_message not called!")
        return False
    
    print("\n✅ Complete flow test passed!")
    return True

async def test_edge_cases():
    """Test edge cases and error handling"""
    print("\n🧪 Testing Edge Cases\n")
    
    # Test 1: Lead with no photos
    print("Test 1: Lead with no photos")
    test_user_data = {
        'language': 'en',
        'plate_number': 'NOWPHOTO',
        'owner_name': 'No Photo User',
        'is_owner': False,
        'curb_weight': 1000,
        'completeness': 'Complete',
        'missing_parts': '',
        'transport_method': 'Self',
        'needs_tow': False,
        'tow_address': '',
        'location_latitude': None,
        'location_longitude': None,
        'photos': '',
        'phone_number': '+1234567890'
    }
    
    lead_id = save_lead(test_user_data, 99999, 'nophoto')
    photos = get_lead_photos(lead_id)
    
    if len(photos) == 0:
        print("✅ Lead with no photos handled correctly")
    else:
        print("❌ Expected 0 photos for new lead")
        return False
    
    # Test 2: Mock notification with no photos
    mock_context = Mock()
    mock_bot = AsyncMock()
    mock_context.bot = mock_bot
    
    mock_bot.send_message = AsyncMock(return_value=None)
    
    await _send_admin_notification(mock_context, lead_id, '+1234567890')
    
    if mock_bot.send_message.called:
        print("✅ Text-only notification sent for lead without photos")
    else:
        print("❌ Text-only notification failed")
        return False
    
    # Test 3: Invalid lead ID
    print("\nTest 3: Invalid lead ID")
    mock_bot.reset_mock()
    
    await _send_admin_notification(mock_context, 999999, '+1234567890')
    
    if not mock_bot.send_media_group.called and not mock_bot.send_message.called:
        print("✅ Invalid lead ID handled correctly (no notification sent)")
    else:
        print("❌ Invalid lead ID should not send notification")
        return False
    
    print("\n✅ All edge cases passed!")
    return True

async def main():
    print("=" * 60)
    print("ROMUPUNKT Bot - Complete Flow Tests")
    print("=" * 60)
    
    success = True
    
    # Run tests
    success &= await test_complete_flow()
    success &= await test_edge_cases()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 ALL TESTS PASSED!")
        print("\nThe complete photo flow is working:")
        print("• Photos are stored with file_ids")
        print("• Admin notification creates media group")
        print("• First photo has HTML caption")
        print("• Control buttons are sent separately")
        print("• Edge cases handled properly")
        print("\n✨ Ready for production testing!")
    else:
        print("❌ SOME TESTS FAILED!")
        print("Please review the errors above")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
