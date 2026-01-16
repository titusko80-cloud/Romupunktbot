"""
Database models for storing vehicle dismantling leads
"""

import sqlite3
from datetime import datetime
from config import DATABASE_URL

def init_db():
    """Initialize the database and create tables"""
    conn = sqlite3.connect('romupunkt.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            telegram_username TEXT,
            language TEXT NOT NULL,
            plate_number TEXT NOT NULL,
            owner_name TEXT NOT NULL,
            curb_weight INTEGER NOT NULL,
            completeness TEXT,
            transport_method TEXT,
            needs_tow BOOLEAN,
            location_latitude REAL,
            location_longitude REAL,
            photos TEXT,
            phone_number TEXT,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS offers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lead_id INTEGER NOT NULL,
            offer_amount REAL,
            transport_cost REAL,
            total_amount REAL,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (lead_id) REFERENCES leads (id)
        )
    ''')
    
    conn.commit()
    conn.close()

def save_lead(user_data, user_id, username=None):
    """Save a new lead to the database"""
    conn = sqlite3.connect('romupunkt.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO leads (
            user_id, telegram_username, language, plate_number, owner_name,
            curb_weight, completeness, transport_method, needs_tow,
            location_latitude, location_longitude, photos, phone_number
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        user_id,
        username,
        user_data.get('language'),
        user_data.get('plate_number'),
        user_data.get('owner_name'),
        user_data.get('curb_weight'),
        user_data.get('completeness'),
        user_data.get('transport_method'),
        user_data.get('needs_tow'),
        user_data.get('location', {}).get('latitude'),
        user_data.get('location', {}).get('longitude'),
        ','.join(user_data.get('photos', [])),
        user_data.get('phone_number')
    ))
    
    lead_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return lead_id

def get_lead_by_user_id(user_id):
    """Get leads for a specific user"""
    conn = sqlite3.connect('romupunkt.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM leads WHERE user_id = ? ORDER BY created_at DESC
    ''', (user_id,))
    
    lead = cursor.fetchone()
    conn.close()
    
    return lead

def update_lead_status(lead_id, status):
    """Update lead status"""
    conn = sqlite3.connect('romupunkt.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE leads SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?
    ''', (status, lead_id))
    
    conn.commit()
    conn.close()
