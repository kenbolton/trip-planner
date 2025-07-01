# tests/test_hudson_alert_service.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, date
import discord

from hudson_alert_service import HudsonValleyAlertService


class TestHudsonAlertService:
    """Test Hudson Valley alert service"""

    @pytest.fixture
    def alert_service(self, mock_bot):
        """Create alert service with mocked dependencies"""
        weather_service = MagicMock()
        current_service = MagicMock()

        # Fix: Mock the convert_wind_speed method to return actual numbers
        weather_service.convert_wind_speed.return_value = 12.0
        weather_service._parse_current_direction.return_value = 180.0
        weather_service.get_wind_direction_text.return_value = 'S'

        service = HudsonValleyAlertService(mock_bot, weather_service, current_service)
        return service

    def test_analyze_downwind_potential_good_conditions(self, alert_service):
        """Test downwind analysis with good conditions"""
        weather_data = {
            'current': {
                'wind_speed': 6.0,  # ~12 mph
                'wind_direction': 0  # North
            },
            'forecast': []
        }

        current_data = [
            {
                'speed': 1.2,
                'direction': '180',  # South (opposing)
                'time': '10:00'
            }
        ]

        # Mock the weather service methods that are called internally
        with patch.object(alert_service.weather_service, 'convert_wind_speed', return_value=12.0), \
             patch.object(alert_service.weather_service, '_parse_current_direction', return_value=180.0), \
             patch.object(alert_service.weather_service, 'get_wind_direction_text', return_value='S'):

            result = alert_service.analyze_downwind_potential(weather_data, current_data)

            assert result is not None
            assert result['quality_score'] >= 50
            assert result['wind_speed_mph'] >= 10
            assert result['current_speed_knots'] >= 1.0

    def test_analyze_downwind_potential_insufficient_wind(self, alert_service):
        """Test downwind analysis with insufficient wind"""
        weather_data = {
            'current': {
                'wind_speed': 3.0,  # ~6 mph (too low)
                'wind_direction': 0
            },
            'forecast': []
        }

        current_data = [
            {'speed': 1.5, 'direction': '180', 'time': '10:00'}
        ]

        # Mock to return low wind speed
        with patch.object(alert_service.weather_service, 'convert_wind_speed', return_value=6.0):
            result = alert_service.analyze_downwind_potential(weather_data, current_data)

            assert result is None

    def test_analyze_downwind_potential_weak_current(self, alert_service):
        """Test downwind analysis with weak current"""
        weather_data = {
            'current': {
                'wind_speed': 6.0,  # Good wind
                'wind_direction': 0
            },
            'forecast': []
        }

        current_data = [
            {
                'speed': 0.5,  # Too weak
                'direction': '180',
                'time': '10:00'
            }
        ]

        with patch.object(alert_service.weather_service, 'convert_wind_speed', return_value=12.0):
            result = alert_service.analyze_downwind_potential(weather_data, current_data)

            assert result is None

    def test_create_downwind_embed_epic_conditions(self, alert_service):
        """Test embed creation for epic conditions"""
        conditions = {
            'quality_score': 92,
            'wind_speed_mph': 18,
            'wind_direction': 0,
            'wind_direction_text': 'N',
            'current_speed_knots': 1.8,
            'current_direction_text': 'S',
            'opposition_angle': 180,
            'time': 'Now',
            'opportunities': [
                'Epic downwind run from Beacon to Cold Spring',
                'Fast runs with current assistance'
            ]
        }

        embed = alert_service.create_downwind_embed(conditions)

        assert isinstance(embed, discord.Embed)
        assert 'Hudson Valley Downwind Alert' in embed.title
        assert 'EPIC' in embed.description
        # Fix: Compare the color value, not the Colour object
        assert embed.color.value == 0x9932CC  # Purple for epic
        assert len(embed.fields) >= 4  # Wind, current, quality, opportunities

    @pytest.mark.asyncio
    async def test_check_downwind_conditions_api_success(self, alert_service):
        """Test checking downwind conditions with successful API calls"""
        # Mock weather service
        alert_service.weather_service.get_weather_forecast = AsyncMock(return_value={
            'current': {
                'wind_speed': 6.0,
                'wind_direction': 0
            },
            'forecast': []
        })

        # Mock current service
        alert_service.current_service.get_current_data = AsyncMock(return_value=[
            {'speed': 1.5, 'direction': '180', 'time': '10:00'}
        ])

        # Mock the weather service methods
        with patch.object(alert_service.weather_service, 'convert_wind_speed', return_value=12.0), \
             patch.object(alert_service.weather_service, '_parse_current_direction', return_value=180.0), \
             patch.object(alert_service.weather_service, 'get_wind_direction_text', return_value='S'):

            result = await alert_service.check_downwind_conditions()

            assert result is not None
            assert 'quality_score' in result

    @pytest.mark.asyncio
    async def test_manual_check_with_conditions(self, alert_service):
        """Test manual check command with good conditions"""
        mock_ctx = MagicMock()
        mock_ctx.send = AsyncMock()

        # Mock check_downwind_conditions to return complete conditions
        good_conditions = {
            'quality_score': 80,
            'wind_speed_mph': 15,
            'wind_direction': 0,
            'wind_direction_text': 'N',  # Fix: Add missing key
            'current_speed_knots': 1.2,
            'current_direction_text': 'S',  # Fix: Add missing key
            'opposition_angle': 180,
            'time': 'Now',
            'opportunities': ['Great conditions']
        }

        alert_service.check_downwind_conditions = AsyncMock(return_value=good_conditions)

        await alert_service.manual_check(mock_ctx)

        mock_ctx.send.assert_called_once()
        call_args = mock_ctx.send.call_args
        assert "Manual Hudson Valley Check" in call_args[0][0]
