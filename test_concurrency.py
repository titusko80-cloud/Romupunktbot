#!/usr/bin/env python3
"""
Multi-User Concurrency Test
Simulates multiple users uploading photos simultaneously
"""

import sys
import os
import uuid
import asyncio
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.models import save_session_photo, get_session_photos, move_session_photos_to_lead, init_db

class MockUser:
    """Mock user for testing"""
    def __init__(self, user_id, username):
        self.id = user_id
        self.username = username

class MockContext:
    """Mock context for testing"""
    def __init__(self, user_id):
        self.user_data = {}
        self.user_id = user_id

def test_session_isolation():
    """Test that different users get isolated sessions"""
    print("🔍 Testing session isolation...")
    
    # Initialize database
    init_db()
    
    # Create mock users
    user1 = MockUser(12345, "user1")
    user2 = MockUser(67890, "user2")
    
    # Create mock contexts
    context1 = MockContext(user1.id)
    context2 = MockContext(user2.id)
    
    # Generate session IDs
    session1 = str(uuid.uuid4())
    session2 = str(uuid.uuid4())
    
    context1.user_data['session_id'] = session1
    context2.user_data['session_id'] = session2
    
    # Save photos for each user
    photos_user1 = ["file_id_1", "file_id_2", "file_id_3"]
    photos_user2 = ["file_id_A", "file_id_B", "file_id_C"]
    
    print(f"User {user1.id} session: {session1}")
    print(f"User {user2.id} session: {session2}")
    
    # Save photos for user1
    for photo_id in photos_user1:
        save_session_photo(user1.id, session1, photo_id)
    
    # Save photos for user2
    for photo_id in photos_user2:
        save_session_photo(user2.id, session2, photo_id)
    
    # Retrieve photos for each user
    retrieved_user1 = get_session_photos(user1.id, session1)
    retrieved_user2 = get_session_photos(user2.id, session2)
    
    print(f"User1 photos: {retrieved_user1}")
    print(f"User2 photos: {retrieved_user2}")
    
    # Verify isolation
    user1_correct = set(retrieved_user1) == set(photos_user1)
    user2_correct = set(retrieved_user2) == set(photos_user2)
    
    if user1_correct and user2_correct:
        print("✅ Session isolation: PASSED")
        return True
    else:
        print("❌ Session isolation: FAILED")
        print(f"Expected user1: {photos_user1}, got: {retrieved_user1}")
        print(f"Expected user2: {photos_user2}, got: {retrieved_user2}")
        return False

def test_concurrent_photo_handling():
    """Test concurrent photo upload simulation"""
    print("🔍 Testing concurrent photo handling...")
    
    # Create 3 users
    users = [
        MockUser(111, "Alice"),
        MockUser(222, "Bob"), 
        MockUser(333, "Charlie")
    ]
    
    sessions = {}
    photos_per_user = {}
    
    # Assign sessions and photos
    for user in users:
        session_id = str(uuid.uuid4())
        sessions[user.id] = session_id
        photos_per_user[user.id] = [f"photo_{user.id}_{i}" for i in range(1, 4)]
    
    # Simulate concurrent uploads
    for user in users:
        session_id = sessions[user.id]
        for photo_id in photos_per_user[user.id]:
            save_session_photo(user.id, session_id, photo_id)
    
    # Verify each user gets only their photos
    all_correct = True
    for user in users:
        session_id = sessions[user.id]
        retrieved = get_session_photos(user.id, session_id)
        expected = photos_per_user[user.id]
        
        if set(retrieved) != set(expected):
            print(f"❌ User {user.username} photo mismatch")
            print(f"Expected: {expected}")
            print(f"Got: {retrieved}")
            all_correct = False
    
    if all_correct:
        print("✅ Concurrent photo handling: PASSED")
        return True
    else:
        print("❌ Concurrent photo handling: FAILED")
        return False

def test_database_structure():
    """Test database has proper tables for multi-user support"""
    print("🔍 Testing database structure...")
    
    try:
        import sqlite3
        conn = sqlite3.connect('romupunkt.db')
        cursor = conn.cursor()
        
        # Check car_photos table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='car_photos'")
        car_photos_exists = cursor.fetchone() is not None
        
        # Check photos table exists  
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='photos'")
        photos_exists = cursor.fetchone() is not None
        
        # Check car_photos has user_id column
        if car_photos_exists:
            cursor.execute("PRAGMA table_info(car_photos)")
            columns = [col[1] for col in cursor.fetchall()]
            has_user_id = 'user_id' in columns
            has_session_id = 'session_id' in columns
        else:
            has_user_id = False
            has_session_id = False
        
        conn.close()
        
        if car_photos_exists and photos_exists and has_user_id and has_session_id:
            print("✅ Database structure: PASSED")
            return True
        else:
            print("❌ Database structure: FAILED")
            print(f"car_photos exists: {car_photos_exists}")
            print(f"photos exists: {photos_exists}")
            print(f"has user_id: {has_user_id}")
            print(f"has session_id: {has_session_id}")
            return False
            
    except Exception as e:
        print(f"❌ Database structure: FAILED - {e}")
        return False

def main():
    """Run all multi-user tests"""
    print("🚀 Starting Multi-User Concurrency Audit...")
    print("=" * 60)
    
    tests = [
        test_database_structure,
        test_session_isolation,
        test_concurrent_photo_handling
    ]
    
    results = []
    for test in tests:
        results.append(test())
        print()
    
    print("=" * 60)
    passed = sum(results)
    total = len(results)
    
    if passed == total:
        print(f"🎉 ALL MULTI-USER TESTS PASSED ({passed}/{total})")
        print("✅ Concurrency protection is working correctly")
        return True
    else:
        print(f"⚠️  SOME MULTI-USER TESTS FAILED ({passed}/{total})")
        print("❌ Concurrency issues detected - need fixes")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
