# current_service.py
import aiohttp
import asyncio
from datetime import datetime, timedelta
from config import NOAA_TIDES_URL

class CurrentService:
    def __init__(self):
        self.base_url = NOAA_TIDES_URL

    async def get_current_data(self, station_id, date):
        """Get current predictions for a specific NOAA station and date"""
        begin_date = date.strftime('%Y%m%d')
        end_date = (date + timedelta(days=1)).strftime('%Y%m%d')

        params = {
            'product': 'currents_predictions',
            'application': 'NOS.COOPS.TAC.CUR',
            'begin_date': begin_date,
            'end_date': end_date,
            'station': station_id,
            'time_zone': 'lst_ldt',
            'units': 'english',
            'format': 'json'
        }

        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(self.base_url, params=params) as response:
                    data = await response.json()
                    return self._format_current_data(data)
            except Exception as e:
                return f"Error fetching current data: {str(e)}"

    def _format_current_data(self, data):
        """Format current data for display"""
        if 'current_predictions' not in data:
            return "No current data available"

        currents = []
        for prediction in data['current_predictions']:
            currents.append({
                'time': prediction['Time'],
                'speed': float(prediction['Speed']),
                'direction': prediction['Direction'],
                'type': prediction['Type']
            })

        return currents
