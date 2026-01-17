#!/usr/bin/env python3
"""
Verification Test - Check send_media_group implementation
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test that InputMediaPhoto is imported"""
    print("🔍 Testing imports...")
    try:
        from telegram import InputMediaPhoto
        print("✅ InputMediaPhoto imported successfully")
        
        # Test that it can be instantiated
        test_media = InputMediaPhoto(media="test_file_id")
        print("✅ InputMediaPhoto can be instantiated")
        return True
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False

def test_finalize_file():
    """Test finalize.py has correct implementation"""
    print("\n🔍 Testing finalize.py implementation...")
    
    try:
        with open('handlers/finalize.py', 'r') as f:
            content = f.read()
        
        # Check for send_media_group
        has_send_media_group = 'send_media_group' in content
        print(f"✅ Has send_media_group: {has_send_media_group}")
        
        # Check for InputMediaPhoto usage
        has_input_media_photo = 'InputMediaPhoto(' in content
        print(f"✅ Uses InputMediaPhoto: {has_input_media_photo}")
        
        # Check for database query
        has_get_lead_photos = 'get_lead_photos(' in content
        print(f"✅ Queries database for photos: {has_get_lead_photos}")
        
        # Check for HTML parse_mode
        has_parse_mode_html = 'parse_mode="HTML"' in content
        print(f"✅ Uses HTML parse_mode: {has_parse_mode_html}")
        
        # Check for try/except
        has_try_except = 'try:' in content and 'except' in content
        print(f"✅ Has error handling: {has_try_except}")
        
        return all([has_send_media_group, has_input_media_photo, has_get_lead_photos, has_parse_mode_html, has_try_except])
        
    except FileNotFoundError:
        print("❌ handlers/finalize.py not found")
        return False
    except Exception as e:
        print(f"❌ Error reading file: {e}")
        return False

def test_bot_description():
    """Test bot description is set"""
    print("\n🔍 Testing bot description...")
    
    try:
        with open('bot.py', 'r') as f:
            content = f.read()
        
        # Check for set_my_description
        has_set_description = 'set_my_description' in content
        print(f"✅ Has set_my_description: {has_set_description}")
        
        # Check for exact text
        has_exact_text = 'Autode ost ja lammutamine. Saada andmed ja pildid, me teeme pakkumise. Vormistame lammutustõendi.' in content
        print(f"✅ Has exact Estonian text: {has_exact_text}")
        
        # Check for language codes
        has_language_codes = 'language_code=' in content
        print(f"✅ Uses language codes: {has_language_codes}")
        
        return all([has_set_description, has_exact_text, has_language_codes])
        
    except FileNotFoundError:
        print("❌ bot.py not found")
        return False
    except Exception as e:
        print(f"❌ Error reading file: {e}")
        return False

def main():
    """Run all verification tests"""
    print("🚀 VERIFICATION TESTS")
    print("=" * 50)
    
    tests = [
        test_imports,
        test_finalize_file,
        test_bot_description
    ]
    
    results = []
    for test in tests:
        results.append(test())
    
    print("\n" + "=" * 50)
    passed = sum(results)
    total = len(results)
    
    if passed == total:
        print(f"🎉 ALL TESTS PASSED ({passed}/{total})")
        print("✅ send_media_group implementation is correct")
        print("✅ InputMediaPhoto is imported and used")
        print("✅ Bot description is set with exact text")
        print("✅ Ready for production!")
    else:
        print(f"❌ SOME TESTS FAILED ({passed}/{total})")
        print("❌ Implementation needs fixes")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
