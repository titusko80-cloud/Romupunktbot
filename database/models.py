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
            is_owner INTEGER,
            curb_weight INTEGER NOT NULL,
            completeness TEXT,
            missing_parts TEXT,
            transport_method TEXT,
            needs_tow BOOLEAN,
            tow_address TEXT,
            location_latitude REAL,
            location_longitude REAL,
            photos TEXT,
            phone_number TEXT,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    try:
        cursor.execute("ALTER TABLE leads ADD COLUMN is_owner INTEGER")
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute("ALTER TABLE leads ADD COLUMN missing_parts TEXT")
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute("ALTER TABLE leads ADD COLUMN tow_address TEXT")
    except sqlite3.OperationalError:
        pass
    
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


def get_lead_by_id(lead_id: int):
    conn = sqlite3.connect('romupunkt.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            id,
            created_at,
            language,
            plate_number,
            owner_name,
            is_owner,
            curb_weight,
            completeness,
            missing_parts,
            transport_method,
            needs_tow,
            tow_address,
            location_latitude,
            location_longitude,
            photos,
            phone_number,
            telegram_username,
            user_id
        FROM leads
        WHERE id = ?
        LIMIT 1
        """,
        (int(lead_id),),
    )
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def create_offer(lead_id: int, offer_amount: float, status: str = "sent") -> int:
    conn = sqlite3.connect('romupunkt.db')
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO offers (lead_id, offer_amount, transport_cost, total_amount, status)
        VALUES (?, ?, ?, ?, ?)
        """,
        (int(lead_id), float(offer_amount), None, float(offer_amount), status),
    )
    offer_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return offer_id


def get_offer_by_id(offer_id: int):
    conn = sqlite3.connect('romupunkt.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT id, lead_id, offer_amount, transport_cost, total_amount, status, created_at
        FROM offers
        WHERE id = ?
        LIMIT 1
        """,
        (int(offer_id),),
    )
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def update_offer_status(offer_id: int, status: str) -> None:
    conn = sqlite3.connect('romupunkt.db')
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE offers SET status = ? WHERE id = ?",
        (status, int(offer_id)),
    )
    conn.commit()
    conn.close()


def get_latest_leads(limit: int = 10):
    conn = sqlite3.connect('romupunkt.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            id,
            created_at,
            language,
            plate_number,
            owner_name,
            is_owner,
            curb_weight,
            completeness,
            missing_parts,
            transport_method,
            needs_tow,
            tow_address,
            location_latitude,
            location_longitude,
            photos,
            phone_number,
            telegram_username,
            user_id,
            status
        FROM leads
        ORDER BY id DESC
        LIMIT ?
        """,
        (int(limit),),
    )

    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def save_lead(user_data, user_id, username=None):
    """Save a new lead to the database"""
    conn = sqlite3.connect('romupunkt.db')
    cursor = conn.cursor()

    try:
        plate = user_data.get('plate_number')
        phone = user_data.get('phone_number')
        if plate and phone:
            cursor.execute(
                """
                SELECT id, created_at
                FROM leads
                WHERE user_id = ? AND plate_number = ? AND phone_number = ?
                ORDER BY id DESC
                LIMIT 1
                """,
                (user_id, plate, phone),
            )
            row = cursor.fetchone()
            if row:
                lead_id_existing, created_at = row
                cursor.execute(
                    "SELECT (strftime('%s','now') - strftime('%s', ?))",
                    (created_at,),
                )
                age_seconds = cursor.fetchone()[0]
                if age_seconds is not None and int(age_seconds) < 120:
                    conn.close()
                    return lead_id_existing
    except Exception:
        pass
    
    cursor.execute('''
        INSERT INTO leads (
            user_id, telegram_username, language, plate_number, owner_name,
            is_owner, curb_weight, completeness, missing_parts, transport_method, needs_tow,
            tow_address, location_latitude, location_longitude, photos, phone_number
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        user_id,
        username,
        user_data.get('language'),
        user_data.get('plate_number'),
        user_data.get('owner_name'),
        1 if user_data.get('is_owner') else 0 if user_data.get('is_owner') is not None else None,
        user_data.get('curb_weight'),
        user_data.get('completeness'),
        user_data.get('missing_parts'),
        user_data.get('transport_method'),
        user_data.get('needs_tow'),
        user_data.get('tow_address'),
        user_data.get('location', {}).get('latitude'),
        user_data.get('location', {}).get('longitude'),
        ','.join(user_data.get('photos', [])),
        user_data.get('phone_number')
    ))
    
    lead_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return lead_id

def get_lead_photos(lead_id: int) -> list[dict]:
    """
    Returns list of dicts: [{ "file_id": "..."}]
    Extracts photo file_ids from the photos column (comma-separated string)
    """
    conn = sqlite3.connect('romupunkt.db')
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT photos FROM leads WHERE id = ?",
        (lead_id,)
    )
    
    row = cursor.fetchone()
    conn.close()
    
    if not row or not row[0]:
        return []
    
    # photos are stored as comma-separated file_ids
    photo_file_ids = row[0].split(',') if row[0] else []
    
    # Filter out empty strings and return as list of dicts
    return [{"file_id": file_id.strip()} for file_id in photo_file_ids if file_id.strip()]


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
