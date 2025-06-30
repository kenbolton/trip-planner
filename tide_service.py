# tide_service.py
import aiohttp
import asyncio
from datetime import datetime, timedelta
from config import NOAA_TIDES_URL

class TideService:
    def __init__(self):
        self.base_url = NOAA_TIDES_URL

    async def get_tide_data(self, station_id, date):
        """Get tide predictions for a specific NOAA station and date"""
        begin_date = date.strftime('%Y%m%d')
        end_date = (date + timedelta(days=1)).strftime('%Y%m%d')

        params = {
            'product': 'predictions',
            'application': 'NOS.COOPS.TAC.WL',
            'begin_date': begin_date,
            'end_date': end_date,
            'station': station_id,
            'time_zone': 'lst_ldt',
            'units': 'english',
            'interval': 'hilo',
            'format': 'json'
        }

        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(self.base_url, params=params) as response:
                    data = await response.json()
                    return self._format_tide_data(data)
            except Exception as e:
                return f"Error fetching tide data: {str(e)}"

    def _format_tide_data(self, data):
        """Format tide data for display"""
        if 'predictions' not in data:
            return "No tide data available"

        tides = []
        for prediction in data['predictions']:
            tides.append({
                'time': prediction['t'],
                'height': float(prediction['v']),
                'type': prediction['type']
            })

        return tides
