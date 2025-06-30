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

    def add_trip(self, user_id, location, trip_date, start_time, duration, participants, emergency_contact):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO trips (user_id, location, trip_date, start_time, duration, participants, emergency_contact)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, location, trip_date, start_time, duration, participants, emergency_contact))

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
