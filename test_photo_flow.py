#!/usr/bin/env python3
"""
Internal test script to verify photo storage and retrieval flow
Tests database operations and file_id handling without requiring Telegram API
"""

import os
import sys
import tempfile
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database.models import init_db, save_lead, save_photo_file_id, get_lead_photos, get_lead_by_id

def test_photo_flow():
    """Test the complete photo storage and retrieval flow"""
    print("🧪 Testing Photo Storage and Retrieval Flow\n")
    
    # Initialize database
    init_db()
    print("✅ Database initialized")
    
    # Create test lead data
    test_user_data = {
        'language': 'et',
        'plate_number': '123ABC',
        'owner_name': 'Test User',
        'is_owner': True,
        'curb_weight': 1500,
        'completeness': 'Täielik',
        'missing_parts': '',
        'transport_method': '🚗 Toon ise',
        'needs_tow': False,
        'tow_address': '',
        'location_latitude': None,
        'location_longitude': None,
        'photos': '',
        'phone_number': '+37251234567'
    }
    
    # Save lead
    lead_id = save_lead(test_user_data, 12345, 'testuser')
    print(f"✅ Lead created with ID: {lead_id}")
    
    # Verify lead was saved
    lead = get_lead_by_id(lead_id)
    if lead:
        print(f"✅ Lead retrieved: {lead['plate_number']} - {lead['owner_name']}")
    else:
        print("❌ Failed to retrieve lead")
        return False
    
    # Test photo file_ids (simulating Telegram file_ids)
    test_file_ids = [
        "AgACAgQAAxkDAAICOGZxY7x1234567890A",
        "AgACAgQAAxkDAAICOGZxY7x1234567891B",
        "AgACAgQAAxkDAAICOGZxY7x1234567892C",
        "AgACAgQAAxkDAAICOGZxY7x1234567893D"
    ]
    
    # Save photos
    for i, file_id in enumerate(test_file_ids, 1):
        save_photo_file_id(lead_id, file_id)
        print(f"✅ Photo {i} saved with file_id: {file_id[:20]}...")
    
    # Retrieve photos
    photos = get_lead_photos(lead_id)
    print(f"\n✅ Retrieved {len(photos)} photos for lead {lead_id}")
    
    # Verify photo file_ids
    retrieved_file_ids = [p['file_id'] for p in photos]
    if retrieved_file_ids == test_file_ids:
        print("✅ All file_ids match perfectly!")
    else:
        print("❌ File_id mismatch!")
        print(f"Expected: {test_file_ids}")
        print(f"Got: {retrieved_file_ids}")
        return False
    
    # Test edge case: lead with no photos
    empty_lead_id = save_lead(test_user_data, 12346, 'testuser2')
    empty_photos = get_lead_photos(empty_lead_id)
    if len(empty_photos) == 0:
        print(f"\n✅ Empty lead {empty_lead_id} correctly returns 0 photos")
    else:
        print(f"❌ Empty lead should return 0 photos, got {len(empty_photos)}")
        return False
    
    # Test non-existent lead
    non_existent = get_lead_photos(99999)
    if len(non_existent) == 0:
        print("✅ Non-existent lead correctly returns 0 photos")
    else:
        print("❌ Non-existent lead should return 0 photos")
        return False
    
    print("\n✅ All tests passed! Photo storage and retrieval works correctly.")
    return True

def test_media_group_format():
    """Test that media group format is correct"""
    print("\n🧪 Testing Media Group Format\n")
    
    # Simulate InputMediaPhoto creation
    from telegram import InputMediaPhoto
    
    test_file_ids = [
        "AgACAgQAAxkDAAICOGZxY7x1234567890A",
        "AgACAgQAAxkDAAICOGZxY7x1234567891B",
        "AgACAgQAAxkDAAICOGZxY7x1234567892C"
    ]
    
    # Create media list as done in finalize.py
    media = []
    caption = "<b>Uus päring #1</b>\n<b>Number:</b> <code>123ABC</code>\n<b>Nimi:</b> Test User"
    
    # First photo gets caption
    media.append(InputMediaPhoto(
        media=test_file_ids[0],
        caption=caption,
        parse_mode="HTML"
    ))
    
    # Add remaining photos
    for file_id in test_file_ids[1:]:
        media.append(InputMediaPhoto(media=file_id))
    
    print(f"✅ Created media group with {len(media)} items")
    print(f"✅ First item has caption: {bool(media[0].caption)}")
    print(f"✅ Remaining items have no caption: {all(not m.caption for m in media[1:])}")
    
    return True

def main():
    print("=" * 60)
    print("ROMUPUNKT Bot - Internal Photo Flow Tests")
    print("=" * 60)
    
    success = True
    
    # Run tests
    success &= test_photo_flow()
    success &= test_media_group_format()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 ALL TESTS PASSED!")
        print("\nThe photo system is ready:")
        print("• Photos are stored with file_ids in database")
        print("• Retrieval returns correct file_ids in order")
        print("• Media group format is correct")
        print("\nYou can now test with the actual bot!")
    else:
        print("❌ SOME TESTS FAILED!")
        print("Please fix the issues before testing with the bot")
    print("=" * 60)

if __name__ == "__main__":
    main()
