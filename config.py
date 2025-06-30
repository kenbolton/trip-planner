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

# Hudson Valley Alert Channel ID (replace with your channel ID)
HUDSON_ALERT_CHANNEL_ID = 1222166227036930060  # Replace with actual channel ID

# NOAA Current Stations for Hudson River
HUDSON_STATIONS = {
    'beacon': 'HUR0506',
    'cold_spring': 'ACT3726_1',
    'poughkeepsie': 'HUR0507',
    'port_albany': 'HUR0618',
    'west_point': 'ACT3726_1',
    'peekskill': 'HUR0508',
    'athens': 'HUR0614',
    'hudson': 'HUR0618',
    'troy': 'HUR0615',
    'catskill': 'HUR0616',
    'kingston': 'HUR0617',
    'newburgh': 'HUR0506',
    'new_york_city': 'HUR0619',
    'yonkers': 'HUR0620',
    'ossining': 'HUR0621',
    'tarrytown': 'HUR0622',
    'sleepy_hollow': 'HUR0623',
    'hastings': 'HUR0624',
    'dobbs_ferry': 'HUR0625',
}

# Alert criteria
HUDSON_WIND_THRESHOLD_MPH = 10
HUDSON_CURRENT_THRESHOLD_KNOTS = 1.0
