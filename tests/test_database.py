# tests/test_database.py
import pytest
import sqlite3
from datetime import datetime
from database import Database


class TestDatabase:
    """Test database operations"""

    def test_database_initialization(self, temp_db):
        """Test database tables are created correctly"""
        conn = sqlite3.connect(temp_db.db_path)
        cursor = conn.cursor()

        # Check trips table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='trips'")
        assert cursor.fetchone() is not None

        # Check ice_contacts table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ice_contacts'")
        assert cursor.fetchone() is not None

        conn.close()

    def test_add_trip(self, temp_db):
        """Test adding a trip to database"""
        trip_id = temp_db.add_trip(
            user_id=12345,
            location="Boston Harbor",
            trip_date="2024-06-15",
            start_time="09:00",
            duration=4,
            participants="user1,user2",
            emergency_contact="John Doe - 555-1234"
        )

        assert trip_id is not None
        assert isinstance(trip_id, int)

        # Verify trip was added
        conn = sqlite3.connect(temp_db.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM trips WHERE id = ?", (trip_id,))
        trip = cursor.fetchone()
        conn.close()

        assert trip is not None
        assert trip[1] == 12345  # user_id
        assert trip[2] == "Boston Harbor"  # location
        assert trip[3] == "2024-06-15"  # trip_date

    def test_add_ice_contact(self, temp_db):
        """Test adding ICE contact"""
        temp_db.add_ice_contact(
            user_id=12345,
            name="Emergency Contact",
            phone="555-1234",
            relationship="Spouse",
            is_primary=True
        )

        contacts = temp_db.get_ice_contacts(12345)
        assert len(contacts) == 1
        assert contacts[0][2] == "Emergency Contact"  # contact_name
        assert contacts[0][3] == "555-1234"  # contact_phone
        assert contacts[0][5] == 1  # is_primary (boolean stored as int)

    def test_primary_ice_contact_enforcement(self, temp_db):
        """Test only one primary contact allowed per user"""
        # Add first primary contact
        temp_db.add_ice_contact(12345, "Contact 1", "555-1111", "Friend", True)

        # Add second primary contact
        temp_db.add_ice_contact(12345, "Contact 2", "555-2222", "Spouse", True)

        contacts = temp_db.get_ice_contacts(12345)
        primary_contacts = [c for c in contacts if c[5] == 1]  # is_primary

        assert len(primary_contacts) == 1
        assert primary_contacts[0][2] == "Contact 2"  # Latest should be primary

    def test_get_ice_contacts_empty(self, temp_db):
        """Test getting ICE contacts when none exist"""
        contacts = temp_db.get_ice_contacts(99999)
        assert contacts == []
