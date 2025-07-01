# -*- coding: utf-8 -*-

import pytest
import sqlite3
import tempfile
import os
from datetime import datetime, date, time
try:
    from unittest.mock import AsyncMock, MagicMock, patch
except ImportError:
    try:
        from mock import MagicMock, patch
        from unittest.mock import AsyncMock
    except ImportError:
        from mock import MagicMock, patch
        # Create AsyncMock for older Python versions
        class AsyncMock(MagicMock):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self._mock_return_value = None

            async def __call__(self, *args, **kwargs):
                return super(AsyncMock, self).__call__(*args, **kwargs)

            def __await__(self):
                async def _async_mock():
                    return self._mock_return_value
                return _async_mock().__await__()
import discord
from discord.ext import commands

from database import Database
from weather_service import WeatherService
from current_service import CurrentService
from tide_service import TideService
from trip_planner import TripPlanner
from hudson_alert_service import HudsonValleyAlertService
from ice_system import ICESystem


@pytest.fixture
def temp_db():
    """Create a temporary database for testing"""
    with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as f:
        db_path = f.name

    db = Database(db_path)
    yield db

    # Cleanup
    os.unlink(db_path)


@pytest.fixture
def mock_bot():
    """Mock Discord bot for testing"""
    bot = MagicMock(spec=commands.Bot)
    bot.user = MagicMock()
    bot.user.name = "KayakBot"
    bot.get_channel = MagicMock()
    bot.get_user = MagicMock()
    bot.wait_until_ready = AsyncMock()
    bot.change_presence = AsyncMock()
    return bot


@pytest.fixture
def mock_discord_channel():
    """Mock Discord channel for testing"""
    channel = MagicMock()
    channel.send = AsyncMock()
    channel.id = 123456789012345678
    channel.name = "test-channel"
    return channel


@pytest.fixture
def mock_discord_user():
    """Mock Discord user for testing"""
    user = MagicMock()
    user.id = 987654321098765432
    user.name = "TestUser"
    user.display_name = "Test User"
    user.send = AsyncMock()
    return user


@pytest.fixture
def mock_discord_context(mock_discord_user, mock_discord_channel, mock_bot):
    """Mock Discord command context for testing"""
    ctx = MagicMock()
    ctx.author = mock_discord_user
    ctx.channel = mock_discord_channel
    ctx.bot = mock_bot
    ctx.send = AsyncMock()
    ctx.message = MagicMock()
    ctx.message.id = 555666777888999000
    ctx.command = MagicMock()
    ctx.command.name = "test_command"
    return ctx


@pytest.fixture
def mock_geocoder():
    """Mock geocoder for location testing"""
    geocoder = MagicMock()

    # Default mock location (Boston Harbor)
    mock_location = MagicMock()
    mock_location.latitude = 42.3601
    mock_location.longitude = -71.0589
    mock_location.address = "Boston Harbor, MA, USA"

    geocoder.geocode.return_value = mock_location
    return geocoder


@pytest.fixture
def sample_weather_data():
    """Sample weather data for testing"""
    return {
        'current': {
            'temp': 20.5,
            'feels_like': 19.2,
            'humidity': 65,
            'wind_speed': 5.2,  # m/s
            'wind_direction': 180,
            'description': 'partly cloudy',
            'visibility': 10000
        },
        'forecast': [
            {
                'time': '12:00',
                'temp': 22.1,
                'wind_speed': 4.8,
                'wind_direction': 170,
                'description': 'sunny',
                'precipitation': 0
            },
            {
                'time': '15:00',
                'temp': 24.3,
                'wind_speed': 6.1,
                'wind_direction': 185,
                'description': 'partly cloudy',
                'precipitation': 0
            }
        ]
    }


@pytest.fixture
def sample_tide_data():
    """Sample tide data for testing"""
    return [
        {
            'time': '06:15',
            'height': 3.2,
            'type': 'H'  # High tide
        },
        {
            'time': '12:30',
            'height': 0.8,
            'type': 'L'  # Low tide
        },
        {
            'time': '18:45',
            'height': 3.1,
            'type': 'H'  # High tide
        }
    ]


@pytest.fixture
def sample_current_data():
    """Sample current data for testing"""
    return [
        {
            'time': '09:00',
            'speed': 1.2,
            'direction': 'N',
            'type': 'flood'
        },
        {
            'time': '15:00',
            'speed': 1.8,
            'direction': 'S',
            'type': 'ebb'
        },
        {
            'time': '21:00',
            'speed': 0.3,
            'direction': 'N',
            'type': 'slack'
        }
    ]


@pytest.fixture
def sample_trip_plan(sample_weather_data, sample_tide_data, sample_current_data):
    """Sample complete trip plan for testing"""
    return {
        'location': 'Boston Harbor',
        'coordinates': (42.3601, -71.0589),
        'date': date(2024, 6, 15),
        'time': time(9, 0),
        'duration': 4,
        'weather': sample_weather_data,
        'tides': sample_tide_data,
        'currents': sample_current_data,
        'safety': {
            'score': 85,
            'level': 'GOOD',
            'color': 0x00FF00,
            'warnings': []
        }
    }


@pytest.fixture
def mock_aiohttp_session():
    """Mock aiohttp session for API testing"""
    session = MagicMock()
    response = MagicMock()
    response.status = 200
    response.json = AsyncMock()

    context_manager = MagicMock()
    context_manager.__aenter__ = AsyncMock(return_value=response)
    context_manager.__aexit__ = AsyncMock(return_value=None)

    session.get.return_value = context_manager
    session.post.return_value = context_manager

    return session


@pytest.fixture
def hudson_valley_conditions():
    """Sample Hudson Valley downwind conditions for testing"""
    return {
        'time': 'Now',
        'wind_speed_mph': 15.2,
        'wind_direction': 0,
        'wind_direction_text': 'N',
        'current_speed_knots': 1.3,
        'current_direction': 180,
        'current_direction_text': 'S',
        'opposition_angle': 180,
        'quality_score': 78,
        'current_time': '10:30',
        'opportunities': [
            '🌊 Great downwind run from Beacon to Cold Spring',
            '🚀 Fast runs with current assistance',
            '📍 Launch from Beacon, ride south to Cold Spring'
        ]
    }


@pytest.fixture
def mock_weather_service():
    """Mock weather service with sample data"""
    service = MagicMock(spec=WeatherService)

    # Mock basic conversion methods
    service.get_wind_direction_text.return_value = 'N'
    service.convert_wind_speed.return_value = 7.0
    service.get_uv_index_description.return_value = {
        'level': 'Moderate',
        'color': 0xFFFF00,
        'advice': 'Some protection needed'
    }

    # Mock weather forecast method - define async function separately
    sample_weather_response = {
        'current': {
            'temp': 20.5,
            'feels_like': 19.2,
            'humidity': 65,
            'wind_speed': 5.2,  # m/s
            'wind_direction': 180,
            'description': 'partly cloudy',
            'visibility': 10000
        },
        'forecast': [
            {
                'time': '12:00',
                'temp': 22.1,
                'wind_speed': 4.8,
                'wind_direction': 170,
                'description': 'sunny',
                'precipitation': 0
            },
            {
                'time': '15:00',
                'temp': 24.3,
                'wind_speed': 6.1,
                'wind_direction': 185,
                'description': 'partly cloudy',
                'precipitation': 0.5
            }
        ]
    }

    service.get_weather_forecast = AsyncMock(return_value=sample_weather_response)

    # Mock marine weather method
    sample_marine_response = {
        'sea_state': {
            'state': 2,
            'description': 'Smooth (wavelets)',
            'wave_height': '0.1-0.5m'
        },
        'water_temp_estimate': {
            'estimated_temp': 15.0,
            'risk_level': 'Low hypothermia risk',
            'recommendation': 'Standard gear sufficient'
        },
        'kayak_comfort': {
            'level': 'Good',
            'score': 85
        },
        'marine_warnings': []
    }

    service.get_marine_weather = AsyncMock(return_value=sample_marine_response)

    # Mock safety assessment methods
    service.assess_kayaking_conditions.return_value = {
        'overall_score': 85,
        'factors': {
            'wind_safety': {'score': 90, 'level': 'Good'},
            'visibility_safety': {'score': 100, 'level': 'Excellent'},
            'precipitation_safety': {'score': 80, 'level': 'Good'},
            'temperature_safety': {'score': 70, 'level': 'Cool'}
        },
        'recommendation': {
            'level': 'GO',
            'color': 0x00FF00,
            'message': 'Good conditions for kayaking'
        },
        'warnings': []
    }

    # Mock individual assessment methods
    service._assess_wind_safety.return_value = {
        'score': 90,
        'level': 'Good',
        'description': 'Light winds'
    }

    service._assess_visibility_safety.return_value = {
        'score': 100,
        'level': 'Excellent',
        'description': 'Clear visibility'
    }

    service._assess_precipitation_safety.return_value = {
        'score': 80,
        'level': 'Good',
        'description': 'Light precipitation'
    }

    service._assess_temperature_safety.return_value = {
        'score': 70,
        'level': 'Cool',
        'description': 'Cool - dress appropriately'
    }

    # Mock sea state methods
    service._estimate_sea_state.return_value = {
        'state': 2,
        'description': 'Smooth (wavelets)',
        'wave_height': '0.1-0.5m'
    }

    service._estimate_water_temp.return_value = {
        'estimated_temp': 15.0,
        'risk_level': 'Low hypothermia risk',
        'recommendation': 'Standard gear sufficient'
    }

    service._assess_kayak_comfort.return_value = {
        'level': 'Good',
        'score': 85
    }

    service._get_marine_warnings.return_value = []

    # Mock wind-current interaction analysis
    def mock_check_wind_current_interaction(wind_dir, wind_speed_ms, current_dir, current_speed_knots):
        wind_knots = wind_speed_ms * 1.944  # Convert to knots

        if wind_knots >= 8 and current_speed_knots >= 1.0:
            direction_diff = abs(wind_dir - current_dir)
            if direction_diff > 180:
                direction_diff = 360 - direction_diff

            if 120 <= direction_diff <= 240:  # Opposition
                return {
                    'alert_type': 'SEA_KAYAK_CONDITIONS',
                    'wind_speed_knots': wind_knots,
                    'current_speed_knots': current_speed_knots,
                    'direction_difference': direction_diff,
                    'wind_direction_text': 'N',
                    'current_direction_text': 'S',
                    'interaction_type': {
                        'type': 'OPPOSING',
                        'emoji': '🌊',
                        'description': 'Wind against current - steep waves'
                    },
                    'conditions': {
                        'level': 'GOOD',
                        'color': 0xFFD700,
                        'emoji': '🙂',
                        'description': 'Good conditions',
                        'skill_level': 'INTERMEDIATE',
                        'excitement_level': 'MODERATE',
                        'score': 75
                    },
                    'message': '🌊 Good conditions for sea kayaking adventure!'
                }
        return None

    service.check_wind_current_interaction.side_effect = mock_check_wind_current_interaction

    # Mock sea kayaking analysis
    service.analyze_sea_kayak_potential.return_value = [
        {
            'alert_type': 'SEA_KAYAK_CONDITIONS',
            'wind_speed_knots': 12.0,
            'current_speed_knots': 1.5,
            'time': '10:00',
            'message': '🌊 Great conditions for sea kayaking!'
        }
    ]

    # Mock wind comfort index
    service.get_wind_comfort_index.return_value = {
        'overall_score': 85,
        'temperature_score': 80,
        'wind_score': 90,
        'humidity_score': 85,
        'description': {
            'level': 'Very Good',
            'emoji': '😄',
            'color': 0x32CD32
        },
        'recommendations': [
            'Great wind conditions for adventure!',
            'Perfect for practicing advanced techniques'
        ]
    }

    # Mock sea state description
    service.get_sea_state_description.return_value = {
        'state': 'Gentle Breeze',
        'description': 'Large wavelets, some crests begin to break',
        'kayak_impact': 'Good conditions for intermediate paddlers',
        'wave_height': '0.5-1m',
        'color': 0x32CD32
    }

    # Mock apparent wind calculation
    service.calculate_apparent_wind.return_value = {
        'speed_knots': 12.5,
        'direction_degrees': 15,
        'direction_text': 'NNE',
        'relative_to_kayak': 'Port bow'
    }

    # Mock direction parsing
    def mock_parse_current_direction(direction_str):
        direction_map = {
            'N': 0, 'NE': 45, 'E': 90, 'SE': 135,
            'S': 180, 'SW': 225, 'W': 270, 'NW': 315,
            '0': 0, '90': 90, '180': 180, '270': 270
        }
        return direction_map.get(str(direction_str), None)

    service._parse_current_direction.side_effect = mock_parse_current_direction

    # Mock Beaufort scale conversion
    def mock_ms_to_beaufort(speed_ms):
        if speed_ms < 0.3:
            return 0
        elif speed_ms < 1.6:
            return 1
        elif speed_ms < 3.4:
            return 2
        elif speed_ms < 5.5:
            return 3
        elif speed_ms < 8.0:
            return 4
        elif speed_ms < 10.8:
            return 5
        else:
            return 6

    service._ms_to_beaufort.side_effect = mock_ms_to_beaufort

    return service


@pytest.fixture
def ice_contact_data():
    """Sample ICE contact data for testing"""
    return {
        'name': 'Emergency Contact',
        'phone': '555-123-4567',
        'relationship': 'Spouse',
        'is_primary': True
    }


@pytest.fixture
def active_trip_data():
    """Sample active trip data for ICE system testing"""
    return {
        'trip_id': 1,
        'user_id': 987654321098765432,
        'start_time': datetime.now(),
        'duration_hours': 4,
        'confirmed_safe': False,
        'reminder_sent': False,
        'emergency_alert_sent': False
    }


@pytest.fixture
def mock_noaa_api_response():
    """Mock NOAA API response for tide/current data"""
    return {
        'predictions': [
            {
                't': '2024-06-15 06:15',
                'v': '3.2',
                'type': 'H'
            },
            {
                't': '2024-06-15 12:30',
                'v': '0.8',
                'type': 'L'
            }
        ],
        'current_predictions': [
            {
                'Time': '2024-06-15 09:00',
                'Speed': '1.2',
                'Direction': 'N',
                'Type': 'flood'
            }
        ]
    }


@pytest.fixture
def mock_openweather_api_response():
    """Mock OpenWeatherMap API response"""
    return {
        'weather': {
            'main': {
                'temp': 20.5,
                'feels_like': 19.2,
                'humidity': 65,
                'pressure': 1013
            },
            'wind': {
                'speed': 5.2,
                'deg': 180,
                'gust': 7.1
            },
            'weather': [
                {
                    'main': 'Clouds',
                    'description': 'partly cloudy',
                    'icon': '02d'
                }
            ],
            'visibility': 10000,
            'dt': 1640995200
        },
        'forecast': {
            'list': [
                {
                    'dt': 1640995200,
                    'main': {
                        'temp': 22.1,
                        'humidity': 60
                    },
                    'wind': {
                        'speed': 4.8,
                        'deg': 170
                    },
                    'weather': [
                        {
                            'description': 'sunny'
                        }
                    ],
                    'rain': {}
                }
            ]
        }
    }


@pytest.fixture
def environmental_variables():
    """Mock environment variables for testing"""
    env_vars = {
        'DISCORD_TOKEN': 'test_discord_token',
        'OPENWEATHER_API_KEY': 'test_weather_api_key',
        'DB_PATH': '/tmp/test_kayak.db',
        'LOG_PATH': '/tmp/logs',
        'LOG_LEVEL': 'INFO',
        'HUDSON_ALERT_CHANNEL_ID': '123456789012345678',
        'NOAA_TIDES_URL': 'https://api.tidesandcurrents.noaa.gov/api/prod/datagetter',
        'WEATHER_BASE_URL': 'https://api.openweathermap.org/data/2.5'
    }

    with patch.dict(os.environ, env_vars):
        yield env_vars


@pytest.fixture
def freeze_time():
    """Fixture to freeze time for testing time-dependent functionality"""
    from freezegun import freeze_time as _freeze_time
    return _freeze_time


@pytest.fixture(autouse=True)
def reset_singletons():
    """Reset any singleton instances between tests"""
    # Clear any module-level caches or singletons
    yield
    # Cleanup code would go here if needed


@pytest.fixture
def mock_discord_embed():
    """Create a mock Discord embed for testing"""
    embed = MagicMock(spec=discord.Embed)
    embed.title = "Test Embed"
    embed.description = "Test Description"
    embed.color = 0x00FF00
    embed.fields = []
    embed.footer = MagicMock()
    embed.timestamp = datetime.now()

    # Mock the add_field method
    def mock_add_field(name, value, inline=True):
        field = MagicMock()
        field.name = name
        field.value = value
        field.inline = inline
        embed.fields.append(field)

    embed.add_field = mock_add_field
    embed.set_footer = MagicMock()

    return embed


@pytest.fixture
def database_with_sample_data(temp_db, ice_contact_data):
    """Database fixture with pre-populated sample data"""
    # Add sample trip
    trip_id = temp_db.add_trip(
        user_id=987654321098765432,
        location="Boston Harbor",
        trip_date="2024-06-15",
        start_time="09:00",
        duration=4,
        participants="TestUser",
        emergency_contact="Emergency Contact - 555-123-4567"
    )

    # Add sample ICE contact
    temp_db.add_ice_contact(
        user_id=987654321098765432,
        name=ice_contact_data['name'],
        phone=ice_contact_data['phone'],
        relationship=ice_contact_data['relationship'],
        is_primary=ice_contact_data['is_primary']
    )

    # Store the created IDs for test access
    temp_db.sample_trip_id = trip_id
    temp_db.sample_user_id = 987654321098765432

    return temp_db


# @pytest.fixture
# def async_context_manager():
#     """Helper fixture for creating async context managers in tests"""
#     def _create_async_context_manager(return_value=None, exception=None):

#         class AsyncContextManager:
#             def __init__(self):
#                 self.return_value = return_value
#                 self.exception = exception

#             async def __aenter__(self):
#                 if self.exception:
#                     raise self.exception
#                 return self.return_value

#             async def __aexit__(self, exc_type, exc_val, exc_tb):
#                 return False

#         return AsyncContextManager()

#     return _create_async_context_manager


# Pytest configuration for async tests
pytest_plugins = ['pytest_asyncio']
