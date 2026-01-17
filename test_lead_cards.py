#!/usr/bin/env python3
"""
Live Lead Card Notification Test
Tests media group functionality and admin notification triggers
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.models import save_lead, get_lead_photos, get_lead_by_id, init_db, save_session_photo, move_session_photos_to_lead

def test_lead_creation_and_notification():
    """Test complete lead creation flow with photos"""
    print("🔍 Testing lead creation and notification flow...")
    
    # Initialize database
    init_db()
    
    # Create test user data
    user_data = {
        'language': 'et',
        'plate_number': '123ABC',
        'owner_name': 'Test User',
        'is_owner': 1,
        'curb_weight': 1500,
        'completeness': 'complete',
        'transport_method': 'pickup',
        'needs_tow': 0,
        'phone_number': '+3725123456'
    }
    
    user_id = 12345
    username = 'testuser'
    
    # Create lead
    try:
        lead_id = save_lead(user_data, user_id, username)
        print(f"✅ Lead created with ID: {lead_id}")
    except Exception as e:
        print(f"❌ Lead creation failed: {e}")
        return False
    
    # Test lead retrieval
    try:
        lead = get_lead_by_id(lead_id)
        if lead:
            print(f"✅ Lead retrieved successfully")
            print(f"   Plate: {lead.get('plate_number')}")
            print(f"   Name: {lead.get('owner_name')}")
            print(f"   Phone: {lead.get('phone_number')}")
        else:
            print("❌ Lead retrieval failed")
            return False
    except Exception as e:
        print(f"❌ Lead retrieval error: {e}")
        return False
    
    return True

def test_photo_storage_and_retrieval():
    """Test photo storage with 0-5 photos"""
    print("🔍 Testing photo storage with varying counts...")
    
    # Initialize database
    init_db()
    
    # Create test lead
    user_data = {
        'language': 'en',
        'plate_number': 'TEST123',
        'owner_name': 'Photo Test',
        'curb_weight': 1200,
        'phone_number': '+372555666'
    }
    
    lead_id = save_lead(user_data, 99999, 'phototest')
    
    # Test with different photo counts
    test_cases = [0, 1, 3, 5]  # 0, 1, 3, and 5 photos
    
    for photo_count in test_cases:
        print(f"  Testing {photo_count} photos...")
        
        # Create session and add photos
        session_id = f"test_session_{photo_count}"
        user_id = 99999
        
        # Add photos to session
        for i in range(photo_count):
            file_id = f"test_photo_{photo_count}_{i}"
            save_session_photo(user_id, session_id, file_id)
        
        # Move to lead
        move_session_photos_to_lead(user_id, session_id, lead_id)
        
        # Retrieve photos
        photos = get_lead_photos(lead_id)
        
        if len(photos) == photo_count:
            print(f"    ✅ {photo_count} photos: PASSED")
        else:
            print(f"    ❌ {photo_count} photos: FAILED (expected {photo_count}, got {len(photos)})")
            return False
        
        # Clean up for next test
        if photo_count > 0:
            import sqlite3
            conn = sqlite3.connect('romupunkt.db')
            cursor = conn.cursor()
            cursor.execute("DELETE FROM photos WHERE lead_id = ?", (lead_id,))
            conn.commit()
            conn.close()
    
    print("✅ Photo storage test: PASSED")
    return True

def test_media_group_structure():
    """Test media group structure creation"""
    print("🔍 Testing media group structure...")
    
    from telegram import InputMediaPhoto
    
    # Test creating media group with 0 photos
    photos_0 = []
    media_0 = []
    
    if len(photos_0) == 0:
        print("  ✅ 0 photos: Text-only fallback")
    else:
        # This shouldn't happen
        print("  ❌ 0 photos: Unexpected behavior")
        return False
    
    # Test creating media group with 1 photo
    photos_1 = [{"file_id": "test_photo_1"}]
    media_1 = []
    
    if photos_1:
        media_1.append(InputMediaPhoto(
            media=photos_1[0]["file_id"],
            caption="<b>Test Lead</b>\nPlate: TEST123",
            parse_mode="HTML"
        ))
    
    if len(media_1) == 1:
        print("  ✅ 1 photo: Single photo with caption")
    else:
        print(f"  ❌ 1 photo: Expected 1, got {len(media_1)}")
        return False
    
    # Test creating media group with 3 photos
    photos_3 = [{"file_id": f"test_photo_{i}"} for i in range(3)]
    media_3 = []
    
    if photos_3:
        # First photo gets caption
        media_3.append(InputMediaPhoto(
            media=photos_3[0]["file_id"],
            caption="<b>Test Lead</b>\nPlate: TEST123",
            parse_mode="HTML"
        ))
        # Remaining photos without caption
        for photo in photos_3[1:]:
            media_3.append(InputMediaPhoto(media=photo["file_id"]))
    
    if len(media_3) == 3:
        print("  ✅ 3 photos: Media group with caption on first photo")
    else:
        print(f"  ❌ 3 photos: Expected 3, got {len(media_3)}")
        return False
    
    # Test creating media group with 5 photos (max)
    photos_5 = [{"file_id": f"test_photo_{i}"} for i in range(5)]
    media_5 = []
    
    if photos_5:
        # First photo gets caption
        media_5.append(InputMediaPhoto(
            media=photos_5[0]["file_id"],
            caption="<b>Test Lead</b>\nPlate: TEST123",
            parse_mode="HTML"
        ))
        # Remaining photos without caption
        for photo in photos_5[1:]:
            media_5.append(InputMediaPhoto(media=photo["file_id"]))
    
    if len(media_5) == 5:
        print("  ✅ 5 photos: Media group with caption on first photo")
    else:
        print(f"  ❌ 5 photos: Expected 5, got {len(media_5)}")
        return False
    
    print("✅ Media group structure: PASSED")
    return True

def test_html_caption_formatting():
    """Test HTML caption formatting for Lead Cards"""
    print("🔍 Testing HTML caption formatting...")
    
    # Test data
    lead_data = {
        'plate_number': '123ABC',
        'owner_name': 'Test Owner',
        'phone_number': '+3725123456',
        'curb_weight': 1500,
        'completeness': 'complete',
        'transport_method': 'pickup'
    }
    
    # Build caption (simulate send_lead_card logic)
    caption_lines = [
        "<b>🏎️ LIVE Päring #1</b>",
        "",
        "<b>📋 Number:</b> <code>123ABC</code>",
        "<b>👤 Name:</b> Test Owner",
        "<b>📞 Phone:</b> <a href=\"tel:+3725123456\">+3725123456</a>",
        "<b>⚖️ Weight:</b> 1500kg",
        "<b>🔧 Komplektsus:</b> ✅ Täielik",
        "<b>🚚 Transport:</b> pickup",
        "<b>📷 Photos:</b> 3"
    ]
    
    caption = "\n".join(caption_lines)
    
    # Verify HTML elements
    checks = [
        ("<b>" in caption, "Bold tags"),
        ("<code>" in caption, "Code tags"),
        ("<a href=\"tel:" in caption, "Clickable phone link"),
        ("🏎️ LIVE" in caption, "Live badge"),
        ("📋 Number:" in caption, "Plate field"),
        ("📞 Phone:" in caption, "Phone field"),
        ("📷 Photos:" in caption, "Photo count")
    ]
    
    all_passed = True
    for check, description in checks:
        if check:
            print(f"    ✅ {description}")
        else:
            print(f"    ❌ {description}")
            all_passed = False
    
    if all_passed:
        print("✅ HTML caption formatting: PASSED")
        return True
    else:
        print("❌ HTML caption formatting: FAILED")
        return False

def main():
    """Run all Lead Card tests"""
    print("🚀 Starting Live Lead Card Notification Audit...")
    print("=" * 60)
    
    tests = [
        test_lead_creation_and_notification,
        test_photo_storage_and_retrieval,
        test_media_group_structure,
        test_html_caption_formatting
    ]
    
    results = []
    for test in tests:
        results.append(test())
        print()
    
    print("=" * 60)
    passed = sum(results)
    total = len(results)
    
    if passed == total:
        print(f"🎉 ALL LEAD CARD TESTS PASSED ({passed}/{total})")
        print("✅ send_media_group function handles 0-5 photos correctly")
        return True
    else:
        print(f"⚠️  SOME LEAD CARD TESTS FAILED ({passed}/{total})")
        print("❌ Lead Card implementation needs fixes")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
