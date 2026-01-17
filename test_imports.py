#!/usr/bin/env python3
"""
Internal Test Script - Dependency Validation
Tests all imports to ensure no ImportError occurs
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_admin_imports():
    """Test admin.py imports"""
    print("🔍 Testing admin.py imports...")
    try:
        from database.models import (
            get_latest_leads, get_lead_by_id, create_offer, get_offer_by_id, 
            update_offer_status, update_lead_status, delete_lead_by_id, get_lead_photos
        )
        print("✅ admin.py imports: PASSED")
        return True
    except ImportError as e:
        print(f"❌ admin.py imports: FAILED - {e}")
        return False

def test_finalize_imports():
    """Test finalize.py imports"""
    print("🔍 Testing finalize.py imports...")
    try:
        from database.models import save_lead, get_lead_photos, get_lead_by_id
        print("✅ finalize.py imports: PASSED")
        return True
    except ImportError as e:
        print(f"❌ finalize.py imports: FAILED - {e}")
        return False

def test_database_functions():
    """Test database function availability"""
    print("🔍 Testing database functions...")
    try:
        from database.models import (
            save_session_photo, get_session_photos, move_session_photos_to_lead,
            get_lead_photos, save_lead, get_lead_by_id, update_lead_status
        )
        print("✅ Database functions: PASSED")
        return True
    except ImportError as e:
        print(f"❌ Database functions: FAILED - {e}")
        return False

def test_bot_imports():
    """Test main bot imports"""
    print("🔍 Testing bot.py imports...")
    try:
        from handlers.admin import leads_command, admin_lead_action_callback
        from handlers.finalize import phone_number, send_lead_card
        print("✅ Bot imports: PASSED")
        return True
    except ImportError as e:
        print(f"❌ Bot imports: FAILED - {e}")
        return False

def main():
    """Run all import tests"""
    print("🚀 Starting Internal Dependency Audit...")
    print("=" * 50)
    
    tests = [
        test_admin_imports,
        test_finalize_imports,
        test_database_functions,
        test_bot_imports
    ]
    
    results = []
    for test in tests:
        results.append(test())
        print()
    
    print("=" * 50)
    passed = sum(results)
    total = len(results)
    
    if passed == total:
        print(f"🎉 ALL TESTS PASSED ({passed}/{total})")
        print("✅ No ImportError issues detected")
        return True
    else:
        print(f"⚠️  SOME TESTS FAILED ({passed}/{total})")
        print("❌ ImportError issues detected - need fixes")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
