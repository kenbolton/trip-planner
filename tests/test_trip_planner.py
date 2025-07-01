# tests/test_trip_planner.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, date, time
import discord

from trip_planner import TripPlanner


class TestTripPlanner:
    """Test trip planning functionality"""

    @pytest.fixture
    def trip_planner(self, temp_db):
        """Create trip planner with mocked services"""
        with patch('trip_planner.WeatherService') as mock_weather, \
             patch('trip_planner.TideService') as mock_tide, \
             patch('trip_planner.CurrentService') as mock_current, \
             patch('trip_planner.Nominatim') as mock_geo:

            # Setup mock geocoder
            mock_location = MagicMock()
            mock_location.latitude = 42.3601
            mock_location.longitude = -71.0589
            mock_geo.return_value.geocode.return_value = mock_location

            planner = TripPlanner(temp_db)
            return planner

    @pytest.mark.asyncio
    async def test_plan_trip_success(self, trip_planner):
        """Test successful trip planning"""
        # Mock service responses
        trip_planner.weather_service.get_weather_forecast = AsyncMock(return_value={
            'current': {'temp': 20, 'wind_speed': 5.0, 'description': 'clear'},
            'forecast': []
        })
        trip_planner.tide_service.get_tide_data = AsyncMock(return_value=[
            {'time': '06:00', 'height': 3.2, 'type': 'H'},
            {'time': '12:15', 'height': 0.8, 'type': 'L'}
        ])
        trip_planner.current_service.get_current_data = AsyncMock(return_value=[
            {'time': '09:00', 'speed': 1.2, 'direction': 'N'}
        ])

        trip_plan, error = await trip_planner.plan_trip(
            location="Boston Harbor",
            date=date(2024, 6, 15),
            time=time(9, 0),
            duration=4
        )

        assert error is None
        assert trip_plan is not None
        assert trip_plan['location'] == "Boston Harbor"
        assert trip_plan['duration'] == 4
        assert 'weather' in trip_plan
        assert 'tides' in trip_plan
        assert 'safety' in trip_plan

    @pytest.mark.asyncio
    async def test_plan_trip_invalid_location(self, trip_planner):
        """Test trip planning with invalid location"""
        # Mock geocoder to return None (location not found)
        trip_planner.geolocator.geocode.return_value = None

        trip_plan, error = await trip_planner.plan_trip(
            location="Invalid Location XYZ",
            date=date(2024, 6, 15),
            time=time(9, 0),
            duration=4
        )

        assert trip_plan is None
        assert error == "Location not found"

    def test_safety_assessment_good_conditions(self, trip_planner):
        """Test safety assessment with good conditions"""
        weather_data = {
            'current': {'wind_speed': 5.0},  # Good wind speed
            'forecast': []  # No precipitation
        }

        safety = trip_planner._assess_safety(weather_data, [], [])

        assert safety['score'] == 100
        assert safety['level'] == 'GOOD'
        assert safety['color'] == 0x00FF00
        assert len(safety['warnings']) == 0

    def test_safety_assessment_high_wind(self, trip_planner):
        """Test safety assessment with high wind"""
        weather_data = {
            'current': {'wind_speed': 20.0},  # High wind speed
            'forecast': []
        }

        safety = trip_planner._assess_safety(weather_data, [], [])

        assert safety['score'] == 70  # 100 - 30 for high wind
        assert safety['level'] == 'FAIR'
        assert 'High wind speeds expected' in safety['warnings']

    def test_safety_assessment_precipitation(self, trip_planner):
        """Test safety assessment with precipitation"""
        weather_data = {
            'current': {'wind_speed': 5.0},
            'forecast': [
                {'precipitation': 2.5}  # Rain expected
            ]
        }

        safety = trip_planner._assess_safety(weather_data, [], [])

        assert safety['score'] == 80  # 100 - 20 for precipitation
        assert 'Precipitation expected' in safety['warnings']

    def test_create_trip_embed(self, trip_planner):
        """Test Discord embed creation for trip plan"""
        trip_plan = {
            'location': 'Boston Harbor',
            'date': date(2024, 6, 15),
            'time': time(9, 0),
            'duration': 4,
            'weather': {
                'current': {
                    'temp': 20.5,
                    'wind_speed': 5.2,
                    'description': 'partly cloudy'
                }
            },
            'tides': [
                {'time': '06:00', 'height': 3.2, 'type': 'H'},
                {'time': '12:15', 'height': 0.8, 'type': 'L'}
            ],
            'safety': {
                'score': 85,
                'level': 'GOOD',
                'color': 0x00FF00,
                'warnings': []
            }
        }

        embed = trip_planner.create_trip_embed(trip_plan)

        assert isinstance(embed, discord.Embed)
        assert "Boston Harbor" in embed.title
        # Fix: Compare the color value, not the Colour object
        assert embed.color.value == 0x00FF00
        assert len(embed.fields) >= 2  # Weather, safety, possibly tides

    @pytest.mark.asyncio
    async def test_plan_trip_service_error(self, trip_planner):
        """Test trip planning when weather service fails"""
        trip_planner.weather_service.get_weather_forecast = AsyncMock(
            side_effect=Exception("API Error")
        )

        trip_plan, error = await trip_planner.plan_trip(
            location="Boston Harbor",
            date=date(2024, 6, 15),
            time=time(9, 0),
            duration=4
        )

        assert trip_plan is None
        assert "Error planning trip" in error
