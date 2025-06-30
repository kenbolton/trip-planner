# config.py
import os
from dotenv import load_dotenv

load_dotenv()

# Discord Bot Token
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')

# API Keys
WEATHER_API_KEY = os.getenv('OPENWEATHER_API_KEY')
NOAA_API_KEY = os.getenv('NOAA_API_KEY')

# Emergency Contacts Channel
ICE_CHANNEL_ID = int(os.getenv('ICE_CHANNEL_ID', 0))

# Database (use volume mount in Docker)
DB_PATH = os.getenv('DB_PATH', '/app/data/kayak_trips.db')

# Logging
LOG_PATH = os.getenv('LOG_PATH', '/app/logs')
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

# API Endpoints
WEATHER_BASE_URL = 'https://api.openweathermap.org/data/2.5'
NOAA_TIDES_URL = 'https://api.tidesandcurrents.noaa.gov/api/prod/datagetter'

# Health check port
HEALTH_CHECK_PORT = int(os.getenv('HEALTH_CHECK_PORT', 8080))
