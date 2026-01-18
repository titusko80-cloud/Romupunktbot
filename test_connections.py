#!/usr/bin/env python3
"""
Test script to verify all critical connections
"""
import sys
import os
sys.path.append(os.path.dirname(__file__))

from database.models import init_db, get_lead_photos, save_lead
from handlers.photos import photo_collection
from handlers.admin import admin_price_message, _parse_price

def test_database_connection():
    """Test database connection and photo retrieval"""
    print("🔍 Testing database connection...")
    try:
        init_db()
        print("✅ Database connection OK")
        
        # Test photo retrieval for a non-existent lead
        photos = get_lead_photos(999)
        print(f"✅ Photo retrieval works (found {len(photos)} photos for test lead)")
        
        return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

def test_price_parsing():
    """Test admin price parsing"""
    print("🔍 Testing price parsing...")
    test_cases = [
        ("245", 245.0),
        ("245€", 245.0),
        ("245 eur", 245.0),
        ("€245", 245.0),
        ("eur245", 245.0),
        ("invalid", None),
    ]
    
    for text, expected in test_cases:
        result = _parse_price(text)
        if result == expected:
            print(f"✅ '{text}' -> {result}")
        else:
            print(f"❌ '{text}' -> {result} (expected {expected})")
            return False
    
    return True

def test_lead_creation():
    """Test lead creation"""
    print("🔍 Testing lead creation...")
    try:
        # Mock user data
        user_data = {
            'plate_number': '123ABC',
            'owner_name': 'Test User',
            'phone_number': '53504299',
            'curb_weight': 1500,
            'language': 'ee',
            'is_owner': True,
            'transport_method': '🚗 Toon ise',
            'needs_tow': False
        }
        
        lead_id = save_lead(user_data, 123, 'testuser')
        print(f"✅ Lead created with ID: {lead_id}")
        
        # Test photo retrieval for this lead
        photos = get_lead_photos(lead_id)
        print(f"✅ Photo retrieval for new lead: {len(photos)} photos")
        
        return True
    except Exception as e:
        print(f"❌ Lead creation failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🧪 TESTING ALL CRITICAL CONNECTIONS")
    print("=" * 50)
    
    tests = [
        test_database_connection,
        test_price_parsing,
        test_lead_creation,
    ]
    
    results = []
    for test in tests:
        result = test()
        results.append(result)
        print()
    
    print("=" * 50)
    passed = sum(results)
    total = len(results)
    print(f"📊 RESULTS: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED!")
    else:
        print("❌ SOME TESTS FAILED!")
    
    return passed == total

if __name__ == "__main__":
    main()
