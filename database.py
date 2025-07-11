# database.py
import sqlite3
import asyncio
from datetime import datetime

class Database:
    def __init__(self, db_path):
        self.db_path = db_path
        self.init_db()

    def init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Trips table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS trips (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                location TEXT NOT NULL,
                trip_date TEXT NOT NULL,
                start_time TEXT NOT NULL,
                duration INTEGER NOT NULL,
                participants TEXT,
                emergency_contact TEXT,
                trip_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # ICE contacts table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ice_contacts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                contact_name TEXT NOT NULL,
                contact_phone TEXT NOT NULL,
                relationship TEXT,
                is_primary BOOLEAN DEFAULT FALSE
            )
        ''')

        conn.commit()
        conn.close()

    def add_trip(self, user_id, location, trip_date, start_time, duration, participants, emergency_contact, trip_name=None):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO trips (user_id, location, trip_date, start_time, duration, participants, emergency_contact, trip_name)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, location, trip_date, start_time, duration, participants, emergency_contact, trip_name))

        trip_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return trip_id

    def add_ice_contact(self, user_id, name, phone, relationship, is_primary=False):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        if is_primary:
            # Remove primary status from other contacts
            cursor.execute('UPDATE ice_contacts SET is_primary = FALSE WHERE user_id = ?', (user_id,))

        cursor.execute('''
            INSERT INTO ice_contacts (user_id, contact_name, contact_phone, relationship, is_primary)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, name, phone, relationship, is_primary))

        conn.commit()
        conn.close()

    def get_ice_contacts(self, user_id):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM ice_contacts WHERE user_id = ?', (user_id,))
        contacts = cursor.fetchall()
        conn.close()
        return contacts

    def get_user_trips(self, user_id, limit=None):
        """Get trips for a specific user"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        query = 'SELECT * FROM trips WHERE user_id = ? ORDER BY created_at DESC'
        params = (user_id,)
        
        if limit:
            query += ' LIMIT ?'
            params = (user_id, limit)

        cursor.execute(query, params)
        trips = cursor.fetchall()
        conn.close()
        return trips

    def get_trip_by_id(self, trip_id, user_id=None):
        """Get a specific trip by ID, optionally filtered by user"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        if user_id:
            cursor.execute('SELECT * FROM trips WHERE id = ? AND user_id = ?', (trip_id, user_id))
        else:
            cursor.execute('SELECT * FROM trips WHERE id = ?', (trip_id,))
        
        trip = cursor.fetchone()
        conn.close()
        return trip

    def add_trip_name_column(self):
        """Add trip_name column if it doesn't exist"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('ALTER TABLE trips ADD COLUMN trip_name TEXT')
            conn.commit()
        except sqlite3.OperationalError:
            # Column already exists
            pass
        
        conn.close()
