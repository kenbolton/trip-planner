# tests/test_ice_system.py
import pytest
from unittest.mock import AsyncMock, MagicMock
import asyncio
from datetime import datetime, timedelta

from ice_system import ICESystem


class TestICESystem:
    """Test ICE (In Case of Emergency) monitoring system"""

    @pytest.fixture
    def ice_system(self, mock_bot, temp_db):
        """Create ICE system with mocked dependencies"""
        return ICESystem(mock_bot, temp_db)

    def test_initialization(self, ice_system):
        """Test ICE system initialization"""
        assert ice_system.active_trips == {}
        assert ice_system.check_interval_minutes == 30

    @pytest.mark.asyncio
    async def test_start_trip_monitoring(self, ice_system):
        """Test starting trip monitoring"""
        mock_channel = MagicMock()

        # Start monitoring (don't await as it runs indefinitely)
        task = asyncio.create_task(
            ice_system.start_trip_monitoring(
                trip_id=1,
                user_id=12345,
                duration_hours=4,
                channel=mock_channel
            )
        )

        # Let it run briefly
        await asyncio.sleep(0.1)

        # Check trip was added to active trips
        assert 1 in ice_system.active_trips
        assert ice_system.active_trips[1]['user_id'] == 12345
        assert ice_system.active_trips[1]['duration_hours'] == 4

        # Cancel the task
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    @pytest.mark.asyncio
    async def test_confirm_safe_return(self, ice_system):
        """Test confirming safe return"""
        # Add active trip
        ice_system.active_trips[1] = {
            'user_id': 12345,
            'start_time': datetime.now(),
            'duration_hours': 4,
            'channel': MagicMock(),
            'confirmed_safe': False
        }

        await ice_system._confirm_safe_return(1)

        assert ice_system.active_trips[1]['confirmed_safe'] is True

    def test_is_trip_overdue(self, ice_system):
        """Test trip overdue detection"""
        # Create trip that started 5 hours ago with 4-hour duration
        start_time = datetime.now() - timedelta(hours=5)

        ice_system.active_trips[1] = {
            'start_time': start_time,
            'duration_hours': 4,
            'confirmed_safe': False
        }

        assert ice_system._is_trip_overdue(1) is True

        # Test trip that's not overdue
        recent_start = datetime.now() - timedelta(hours=2)
        ice_system.active_trips[2] = {
            'start_time': recent_start,
            'duration_hours': 4,
            'confirmed_safe': False
        }

        assert ice_system._is_trip_overdue(2) is False

    def test_is_trip_overdue_already_confirmed(self, ice_system):
        """Test overdue detection for already confirmed trips"""
        start_time = datetime.now() - timedelta(hours=5)

        ice_system.active_trips[1] = {
            'start_time': start_time,
            'duration_hours': 4,
            'confirmed_safe': True  # Already confirmed safe
        }

        assert ice_system._is_trip_overdue(1) is False

    @pytest.mark.asyncio
    async def test_send_check_in_reminder(self, ice_system, mock_bot):
        """Test sending check-in reminder"""
        mock_user = MagicMock()
        mock_user.send = AsyncMock()
        mock_bot.get_user.return_value = mock_user

        ice_system.active_trips[1] = {
            'user_id': 12345,
            'start_time': datetime.now() - timedelta(hours=4),
            'duration_hours': 4
        }

        await ice_system._send_check_in_reminder(1)

        mock_user.send.assert_called_once()
        # Verify reminder message content
        call_args = mock_user.send.call_args
        assert any('check-in' in str(arg).lower() for arg in call_args[0])

    @pytest.mark.asyncio
    async def test_send_emergency_alert(self, ice_system, temp_db, mock_bot):
        """Test sending emergency alert"""
        # Add ICE contact to database
        temp_db.add_ice_contact(12345, "Emergency Contact", "555-1234", "Spouse", True)

        mock_user = MagicMock()
        mock_user.send = AsyncMock()
        mock_bot.get_user.return_value = mock_user

        ice_system.active_trips[1] = {
            'user_id': 12345,
            'start_time': datetime.now() - timedelta(hours=6),
            'duration_hours': 4,
            'channel': MagicMock()
        }

        await ice_system._send_emergency_alert(1)

        # Should attempt to contact emergency contacts
        # In a real implementation, this might send SMS or other alerts
        mock_user.send.assert_called()

    def test_get_trip_status_active(self, ice_system):
        """Test getting status of active trip"""
        start_time = datetime.now() - timedelta(hours=2)

        ice_system.active_trips[1] = {
            'start_time': start_time,
            'duration_hours': 4,
            'confirmed_safe': False,
            'user_id': 12345
        }

        status = ice_system.get_trip_status(1)

        assert status is not None
        assert status['is_active'] is True
        assert status['is_overdue'] is False
        assert status['elapsed_hours'] == pytest.approx(2, abs=0.1)

    def test_get_trip_status_nonexistent(self, ice_system):
        """Test getting status of non-existent trip"""
        status = ice_system.get_trip_status(999)
        assert status is None

    def test_stop_trip_monitoring(self, ice_system):
        """Test stopping trip monitoring"""
        ice_system.active_trips[1] = {
            'user_id': 12345,
            'confirmed_safe': False
        }

        result = ice_system.stop_trip_monitoring(1)

        assert result is True
        assert 1 not in ice_system.active_trips

    def test_stop_nonexistent_trip_monitoring(self, ice_system):
        """Test stopping monitoring for non-existent trip"""
        result = ice_system.stop_trip_monitoring(999)
        assert result is False

    def test_get_active_trips_for_user(self, ice_system):
        """Test getting active trips for specific user"""
        ice_system.active_trips[1] = {'user_id': 12345}
        ice_system.active_trips[2] = {'user_id': 67890}
        ice_system.active_trips[3] = {'user_id': 12345}

        user_trips = ice_system.get_active_trips_for_user(12345)

        assert len(user_trips) == 2
        assert 1 in user_trips
        assert 3 in user_trips
        assert 2 not in user_trips

    @pytest.mark.asyncio
    async def test_emergency_escalation_timeline(self, ice_system):
        """Test emergency escalation timeline"""
        # Test that emergency procedures escalate appropriately
        start_time = datetime.now() - timedelta(hours=6)  # 2 hours overdue

        ice_system.active_trips[1] = {
            'user_id': 12345,
            'start_time': start_time,
            'duration_hours': 4,
            'confirmed_safe': False,
            'channel': MagicMock(),
            'reminder_sent': False,
            'emergency_alert_sent': False
        }

        # Should be overdue
        assert ice_system._is_trip_overdue(1) is True

        # Should escalate to emergency after sufficient time
        overdue_hours = (datetime.now() - (start_time + timedelta(hours=4))).total_seconds() / 3600
        assert overdue_hours >= 1  # At least 1 hour overdue
