# trip_planner.py
import discord
from datetime import datetime
from geopy.geocoders import Nominatim
from weather_service import WeatherService
from tide_service import TideService
from current_service import CurrentService


class TripPlanner:
    def __init__(self, db):
        self.db = db
        self.weather_service = WeatherService()
        self.tide_service = TideService()
        self.current_service = CurrentService()
        self.geolocator = Nominatim(user_agent="kayak_trip_planner")

    def _celsius_to_fahrenheit(self, celsius):
        """Convert Celsius to Fahrenheit"""
        return (celsius * 9/5) + 32

    def _ms_to_mph(self, ms):
        """Convert m/s to mph"""
        return ms * 2.237

    def _format_temperature(self, celsius):
        """Format temperature as imperial first, then metric"""
        fahrenheit = self._celsius_to_fahrenheit(celsius)
        return f"{fahrenheit:.1f}°F ({celsius:.1f}°C)"

    def _format_wind_speed(self, ms):
        """Format wind speed as imperial first, then metric"""
        mph = self._ms_to_mph(ms)
        return f"{mph:.1f} mph ({ms:.1f} m/s)"

    async def plan_trip(self, location, date, time, duration, trip_name=None):
        """Plan a comprehensive kayak trip"""
        try:
            # Geocode location
            geo_location = self.geolocator.geocode(location)
            if not geo_location:
                return None, "Location not found"

            lat, lon = geo_location.latitude, geo_location.longitude

            # Get weather data
            weather_data = await self.weather_service.get_weather_forecast(lat, lon, date)

            # Get tide data (using a default station - in real app, find nearest)
            tide_data = await self.tide_service.get_tide_data("8518750", date)  # Boston Harbor

            # Get current data
            current_data = await self.current_service.get_current_data("PCT0301", date)  # Example station

            # Analyze conditions
            safety_assessment = self._assess_safety(weather_data, tide_data, current_data)

            trip_plan = {
                'trip_name': trip_name,
                'location': location,
                'coordinates': (lat, lon),
                'date': date,
                'time': time,
                'duration': duration,
                'weather': weather_data,
                'tides': tide_data,
                'currents': current_data,
                'safety': safety_assessment
            }

            return trip_plan, None

        except Exception as e:
            return None, f"Error planning trip: {str(e)}"

    def _assess_safety(self, weather, tides, currents):
        """Assess safety conditions for the trip"""
        safety_score = 100
        warnings = []

        if isinstance(weather, dict):
            # Check wind conditions
            if weather['current']['wind_speed'] > 15:  # knots
                safety_score -= 30
                warnings.append("High wind speeds expected")

            # Check for precipitation
            for forecast in weather.get('forecast', []):
                if forecast.get('precipitation', 0) > 0:
                    safety_score -= 20
                    warnings.append("Precipitation expected")
                    break

        # Assess overall safety level
        if safety_score >= 80:
            level = "GOOD"
            color = 0x00FF00
        elif safety_score >= 60:
            level = "FAIR"
            color = 0xFFFF00
        elif safety_score >= 40:
            level = "POOR"
            color = 0xFF6B35
        else:
            level = "DANGEROUS"
            color = 0xFF0000

        return {
            'score': safety_score,
            'level': level,
            'color': color,
            'warnings': warnings
        }

    def create_trip_embed(self, trip_plan):
        """Create Discord embed for trip plan"""
        title = f"🛶 Kayak Trip Plan"
        if trip_plan.get('trip_name'):
            title += f": {trip_plan['trip_name']}"
        title += f" - {trip_plan['location']}"
        
        embed = discord.Embed(
            title=title,
            description=f"**Date:** {trip_plan['date'].strftime('%Y-%m-%d')}\n**Time:** {trip_plan['time']}\n**Duration:** {trip_plan['duration']} hours",
            color=trip_plan['safety']['color']
        )

        # Weather section
        if isinstance(trip_plan['weather'], dict):
            weather = trip_plan['weather']['current']
            embed.add_field(
                name="🌤️ Current Weather",
                value=f"**Temp:** {self._format_temperature(weather['temp'])}\n**Wind:** {self._format_wind_speed(weather['wind_speed'])}\n**Conditions:** {weather['description'].title()}",
                inline=True
            )

        # Tides section
        if isinstance(trip_plan['tides'], list) and trip_plan['tides']:
            tide_info = "\n".join([
                f"{tide['time']}: {tide['height']:.1f}ft ({tide['type']})"
                for tide in trip_plan['tides'][:4]
            ])
            embed.add_field(
                name="🌊 Tides",
                value=tide_info,
                inline=True
            )

        # Currents section
        if isinstance(trip_plan['currents'], list) and trip_plan['currents']:
            current_info = "\n".join([
                f"{current['time']}: {current['speed']:.1f} knots {current['direction']} ({current['type']})"
                for current in trip_plan['currents'][:4]
            ])
            embed.add_field(
                name="🌊 Currents",
                value=current_info,
                inline=True
            )

        # Safety assessment
        safety = trip_plan['safety']
        safety_text = f"**Level:** {safety['level']}\n**Score:** {safety['score']}/100"
        if safety['warnings']:
            safety_text += f"\n**Warnings:**\n" + "\n".join([f"⚠️ {w}" for w in safety['warnings']])

        embed.add_field(
            name="🛡️ Safety Assessment",
            value=safety_text,
            inline=False
        )

        return embed
