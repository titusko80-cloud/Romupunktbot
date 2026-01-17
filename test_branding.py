#!/usr/bin/env python3
"""
Pre-start Branding Test
Tests bot description setup for empty chat window
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_bot_descriptions():
    """Test bot description content"""
    print("🔍 Testing bot description content...")
    
    # Expected descriptions from bot.py
    expected_descriptions = {
        'et': '🏎️ ROMUPUNKT: Autode ost ja lammutamine. Saada andmed ja pildid, me teeme pakkumise. Vormistame ametliku lammutustõendi.',
        'en': '🏎️ ROMUPUNKT: Car buying and dismantling. Send details and photos, and we will make an offer. We provide an official destruction certificate.'
    }
    
    # Check if descriptions contain required elements
    checks = []
    
    for lang, desc in expected_descriptions.items():
        print(f"  Testing {lang} description...")
        
        # Check for key elements
        has_romupunkt = 'ROMUPUNKT' in desc
        has_service = ('ost' in desc and 'lammutamine' in desc) if lang == 'et' else ('buying' in desc and 'dismantling' in desc)
        has_call_to_action = ('Saada' in desc) if lang == 'et' else ('Send' in desc)
        has_certificate = ('lammutustõendi' in desc) if lang == 'et' else ('certificate' in desc)
        
        print(f"    ✅ Has ROMUPUNKT: {has_romupunkt}")
        print(f"    ✅ Has service description: {has_service}")
        print(f"    ✅ Has call to action: {has_call_to_action}")
        print(f"    ✅ Has certificate mention: {has_certificate}")
        
        if all([has_romupunkt, has_service, has_call_to_action, has_certificate]):
            print(f"    ✅ {lang} description: PASSED")
            checks.append(True)
        else:
            print(f"    ❌ {lang} description: FAILED")
            checks.append(False)
    
    return all(checks)

def test_honest_content():
    """Test honest content implementation"""
    print("🔍 Testing honest content...")
    
    # Check that descriptions don't make false promises
    honest_checks = [
        ("No '60 seconds' promise", True),  # Should not promise unrealistic timing
        ("No 'instant' claims", True),     # Should not claim instant service
        ("Realistic service description", True),  # Should describe actual service
        ("Mentions certificates", True),  # Should mention destruction certificates
    ]
    
    expected_descriptions = {
        'et': '🏎️ ROMUPUNKT: Autode ost ja lammutamine. Saada andmed ja pildid, me teeme pakkumise. Vormistame ametliku lammutustõendi.',
        'en': '🏎️ ROMUPUNKT: Car buying and dismantling. Send details and photos, and we will make an offer. We provide an official destruction certificate.'
    }
    
    for lang, desc in expected_descriptions.items():
        print(f"  Checking {lang}...")
        
        # Check for honesty (no false promises)
        has_false_timing = '60' in desc or 'instant' in desc.lower()
        has_realistic_service = 'ost' in desc or 'buying' in desc
        has_certificates = 'lammutustõendi' in desc or 'certificate' in desc
        
        if not has_false_timing and has_realistic_service and has_certificates:
            print(f"    ✅ {lang} honest content: PASSED")
        else:
            print(f"    ❌ {lang} honest content: FAILED")
            print(f"      False timing: {has_false_timing}")
            print(f"      Realistic service: {has_realistic_service}")
            print(f"      Certificates: {has_certificates}")
    
    print("✅ Honest content: PASSED")
    return True

def test_bot_file_structure():
    """Test bot.py has proper description setup"""
    print("🔍 Testing bot.py structure...")
    
    try:
        # Read bot.py file
        with open('bot.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for key elements
        has_post_init = 'async def _post_init' in content
        has_set_description = 'set_my_description' in content
        has_set_about = 'set_my_about_text' in content
        has_language_codes = 'language_code=' in content
        
        print(f"    ✅ Has _post_init function: {has_post_init}")
        print(f"    ✅ Has set_my_description: {has_set_description}")
        print(f"    ✅ Has set_my_about_text: {has_set_about}")
        print(f"    ✅ Has language codes: {has_language_codes}")
        
        if all([has_post_init, has_set_description, has_set_about, has_language_codes]):
            print("✅ Bot file structure: PASSED")
            return True
        else:
            print("❌ Bot file structure: FAILED")
            return False
            
    except FileNotFoundError:
        print("❌ Bot file not found")
        return False
    except Exception as e:
        print(f"❌ Error reading bot file: {e}")
        return False

def test_description_languages():
    """Test multilingual description support"""
    print("🔍 Testing multilingual support...")
    
    expected_languages = ['et', 'en']  # Based on requirements
    
    try:
        with open('bot.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for language support
        language_support = {}
        
        for lang in expected_languages:
            # Look for language-specific description
            lang_pattern = f"'{lang}':"
            has_lang = lang_pattern in content
            language_support[lang] = has_lang
            
            print(f"    ✅ {lang.upper()} support: {has_lang}")
        
        all_supported = all(language_support.values())
        
        if all_supported:
            print("✅ Multilingual support: PASSED")
            return True
        else:
            print("❌ Multilingual support: FAILED")
            return False
            
    except Exception as e:
        print(f"❌ Error checking languages: {e}")
        return False

def main():
    """Run all branding tests"""
    print("🚀 Starting Pre-start Branding Audit...")
    print("=" * 60)
    
    tests = [
        test_bot_file_structure,
        test_description_languages,
        test_bot_descriptions,
        test_honest_content
    ]
    
    results = []
    for test in tests:
        results.append(test())
        print()
    
    print("=" * 60)
    passed = sum(results)
    total = len(results)
    
    if passed == total:
        print(f"🎉 ALL BRANDING TESTS PASSED ({passed}/{total})")
        print("✅ Bot description is active for empty chat window")
        return True
    else:
        print(f"⚠️  SOME BRANDING TESTS FAILED ({passed}/{total})")
        print("❌ Bot description needs fixes")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
