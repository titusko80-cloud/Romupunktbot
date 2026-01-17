"""
Database models for storing vehicle dismantling leads
"""

import sqlite3
import threading
from datetime import datetime
from contextlib import contextmanager
from config import DATABASE_URL

# Thread-local storage for database connections
_local = threading.local()

@contextmanager
def get_db_connection():
    """Get a thread-safe database connection"""
    if not hasattr(_local, 'connection'):
        _local.connection = sqlite3.connect('romupunkt.db', check_same_thread=False)
        _local.connection.row_factory = sqlite3.Row
    try:
        yield _local.connection
    except Exception:
        _local.connection.rollback()
        raise
    finally:
        pass  # Keep connection open for thread reuse

def init_db():
    """Initialize the database and create tables"""
    with get_db_connection() as conn:
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
        
        # Create car_photos table for session-based photo storage
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS car_photos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                session_id TEXT NOT NULL,
                file_id TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, session_id, file_id)
            )
        ''')
        
        # Create photos table for file_id storage
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS photos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lead_id INTEGER NOT NULL,
                file_id TEXT NOT NULL,
                file_path TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (lead_id) REFERENCES leads (id)
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


def update_lead_status(lead_id: int, status: str) -> None:
    """Update the status of a lead (pending, replied, accepted, rejected, archived)"""
    conn = sqlite3.connect('romupunkt.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE leads SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (status, lead_id))
    conn.commit()
    conn.close()


def save_session_photo(user_id: int, session_id: str, file_id: str) -> None:
    """Save a photo to session storage with thread safety"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT OR IGNORE INTO car_photos (user_id, session_id, file_id) VALUES (?, ?, ?)",
                (user_id, session_id, file_id)
            )
            conn.commit()
        except sqlite3.IntegrityError:
            pass  # Photo already saved

def get_session_photos(user_id: int, session_id: str) -> list:
    """Get all photos for a user session with thread safety"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT file_id FROM car_photos WHERE user_id = ? AND session_id = ? ORDER BY created_at",
            (user_id, session_id)
        )
        rows = cursor.fetchall()
        return [row[0] for row in rows]

def move_session_photos_to_lead(user_id: int, session_id: str, lead_id: int) -> None:
    """Move photos from session to permanent lead storage with thread safety"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Get session photos
        cursor.execute(
            "SELECT file_id FROM car_photos WHERE user_id = ? AND session_id = ? ORDER BY created_at",
            (user_id, session_id)
        )
        photos = cursor.fetchall()
        
        # Move to photos table
        for (file_id,) in photos:
            cursor.execute(
                "INSERT INTO photos (lead_id, file_id) VALUES (?, ?)",
                (lead_id, file_id)
            )
        
        # Clear session photos
        cursor.execute(
            "DELETE FROM car_photos WHERE user_id = ? AND session_id = ?",
            (user_id, session_id)
        )
        
        conn.commit()

def save_photo_file_id(lead_id: int, file_id: str, file_path: str = None) -> None:
    """Save a photo file_id for a lead"""
    conn = sqlite3.connect('romupunkt.db')
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO photos (lead_id, file_id, file_path) VALUES (?, ?, ?)",
        (lead_id, file_id, file_path)
    )
    conn.commit()
    conn.close()

def get_lead_photos(lead_id: int) -> list:
    """Get all photo file_ids for a lead"""
    conn = sqlite3.connect('romupunkt.db')
    cursor = conn.cursor()
    cursor.execute(
        "SELECT file_id, file_path FROM photos WHERE lead_id = ? ORDER BY created_at",
        (lead_id,)
    )
    rows = cursor.fetchall()
    conn.close()
    return [{"file_id": row[0], "file_path": row[1]} for row in rows]

def delete_lead_by_id(lead_id: int) -> None:
    """Delete a lead and its associated offers and photos by ID"""
    conn = sqlite3.connect('romupunkt.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM photos WHERE lead_id = ?", (lead_id,))
    cursor.execute("DELETE FROM offers WHERE lead_id = ?", (lead_id,))
    cursor.execute("DELETE FROM leads WHERE id = ?", (lead_id,))
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
