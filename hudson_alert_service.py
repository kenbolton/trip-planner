# hudson_alert_service.py
import logging
from datetime import datetime
from typing import Optional, Dict, List

import discord
from discord.ext import tasks

from weather_service import WeatherService
from current_service import CurrentService
from config import HUDSON_ALERT_CHANNEL_ID, HUDSON_STATIONS

logger = logging.getLogger(__name__)


class HudsonValleyAlertService:
    def __init__(self, bot, weather_service: WeatherService, current_service: CurrentService):
        self.bot = bot
        self.weather_service = weather_service
        self.current_service = current_service

        # Hudson Valley coordinates (Beacon-Cold Spring area)
        self.locations = {
            'beacon': {'lat': 41.5048, 'lon': -73.9692, 'name': 'Beacon'},
            'cold_spring': {'lat': 41.4201, 'lon': -73.9551, 'name': 'Cold Spring'},
            'peekskill': {'lat': 41.2901, 'lon': -73.9209, 'name': 'Peekskill'},
            'poughkeepsie': {'lat': 41.7004, 'lon': -73.9209, 'name': 'Poughkeepsie'}
        }

        # NOAA current stations in the area
        self.current_stations = {
            'hudson_river_beacon': '8518750',  # Example station ID
            'hudson_river_poughkeepsie': '8518760'  # Example station ID
        }

        # Alert criteria
        self.min_wind_speed_mph = 10
        self.target_current_speed_knots = 1.0
        self.alert_sent_today = False

    async def start_monitoring(self):
        """Start the daily monitoring task"""
        self.daily_check.start()
        logger.info("Hudson Valley downwind alert monitoring started")

    def stop_monitoring(self):
        """Stop the monitoring task"""
        self.daily_check.cancel()
        logger.info("Hudson Valley downwind alert monitoring stopped")

    @tasks.loop(hours=2)  # Check every 2 hours
    async def daily_check(self):
        """Check conditions every 2 hours and send daily alert if criteria met"""
        try:
            now = datetime.now()

            # Reset daily flag at midnight
            if now.hour == 0 and self.alert_sent_today:
                self.alert_sent_today = False
                logger.info("Reset daily alert flag")

            # Skip if already sent alert today
            if self.alert_sent_today:
                return

            # Check conditions for next 24 hours
            conditions = await self.check_downwind_conditions()

            if conditions and conditions['quality_score'] >= 75:
                await self.send_downwind_alert(conditions)
                self.alert_sent_today = True
                logger.info("Downwind alert sent for Hudson Valley")

        except Exception as e:
            logger.error(f"Error in daily Hudson Valley check: {e}")

    @daily_check.before_loop
    async def before_daily_check(self):
        """Wait for bot to be ready before starting checks"""
        await self.bot.wait_until_ready()

    async def check_downwind_conditions(self) -> Optional[Dict]:
        """Check current weather and water conditions for downwind opportunities"""
        # Get weather data for Beacon area (center of target zone)
        beacon_coords = self.locations['beacon']
        weather_data = await self.weather_service.get_weather_forecast(
            beacon_coords['lat'],
            beacon_coords['lon'],
            datetime.now().date()
        )

        if isinstance(weather_data, str):  # Error occurred
            logger.error(f"Weather data error: {weather_data}")
            return None

        # Get current data for Hudson River stations
        current_conditions = []
        for station_name, station_id in self.current_stations.items():
            current_data = await self.current_service.get_current_data(
                station_id,
                datetime.now().date()
            )

            if isinstance(current_data, list):
                current_conditions.extend(current_data)

        # Analyze conditions for downwind potential
        return self.analyze_downwind_potential(weather_data, current_conditions)

    def analyze_downwind_potential(self, weather_data: Dict, current_data: List) -> Optional[Dict]:
        """Analyze weather and current data for optimal downwind conditions"""
        if not weather_data or not current_data:
            return None

        current_wind = weather_data.get('current', {})
        forecast = weather_data.get('forecast', [])

        # Current conditions
        wind_speed_ms = current_wind.get('wind_speed', 0)
        wind_direction = current_wind.get('wind_direction', 0)
        wind_speed_mph = self.weather_service.convert_wind_speed(wind_speed_ms, 'mph')

        best_conditions = {
            'time': datetime.now().strftime('%H:%M'),
            'wind_speed_mph': wind_speed_mph,
            'wind_direction': wind_direction,
            'wind_direction_text': self.weather_service.get_wind_direction_text(wind_direction),
            'current_speed_knots': 0,
            'current_direction': 0,
            'opposition_angle': 0,
            'quality_score': 0,
            'opportunities': []
        }

        # Check forecast for better conditions in next 24 hours
        all_conditions = [current_wind] + forecast

        for condition_time, condition in enumerate(all_conditions):
            if condition_time == 0:
                time_str = "Now"
            else:
                time_str = condition.get('time', f"T+{condition_time}h")

            wind_ms = condition.get('wind_speed', 0)
            wind_dir = condition.get('wind_direction', 0)
            wind_mph = self.weather_service.convert_wind_speed(wind_ms, 'mph')

            # Skip if wind doesn't meet minimum criteria
            if wind_mph < self.min_wind_speed_mph:
                continue

            # Check current interactions
            for current in current_data:
                current_speed = current.get('speed', 0)
                current_dir_str = current.get('direction', '')
                current_dir = self.weather_service._parse_current_direction(current_dir_str)

                if current_dir is None or current_speed < self.target_current_speed_knots:
                    continue

                # Calculate opposition angle
                opposition_angle = abs(wind_dir - current_dir)
                if opposition_angle > 180:
                    opposition_angle = 360 - opposition_angle

                # Good opposition is 120-240 degrees (opposing directions)
                if 120 <= opposition_angle <= 240:
                    quality_score = self.calculate_downwind_quality(
                        wind_mph, current_speed, opposition_angle
                    )

                    if quality_score > best_conditions['quality_score']:
                        best_conditions.update({
                            'time': time_str,
                            'wind_speed_mph': wind_mph,
                            'wind_direction': wind_dir,
                            'wind_direction_text': self.weather_service.get_wind_direction_text(wind_dir),
                            'current_speed_knots': current_speed,
                            'current_direction': current_dir,
                            'current_direction_text': self.weather_service.get_wind_direction_text(current_dir),
                            'opposition_angle': opposition_angle,
                            'quality_score': quality_score,
                            'current_time': current.get('time', 'Unknown')
                        })

        # Only return if we found good conditions
        if best_conditions['quality_score'] >= 50:
            best_conditions['opportunities'] = self.get_hudson_opportunities(best_conditions)
            return best_conditions

        return None

    def calculate_downwind_quality(self, wind_mph: float, current_knots: float, opposition_angle: float) -> float:
        """Calculate quality score for downwind conditions (0-100)"""
        score = 0

        # Wind speed scoring (10-25 mph is optimal)
        if 10 <= wind_mph <= 15:
            score += 35
        elif 15 < wind_mph <= 20:
            score += 40  # Sweet spot
        elif 20 < wind_mph <= 25:
            score += 35
        elif 25 < wind_mph <= 30:
            score += 25
        else:
            score += 10

        # Current speed scoring (1-3 knots optimal)
        if 1.0 <= current_knots <= 2.0:
            score += 30
        elif 2.0 < current_knots <= 3.0:
            score += 25
        elif 0.5 <= current_knots < 1.0:
            score += 20
        else:
            score += 10

        # Opposition angle scoring (180° is perfect opposition)
        angle_quality = 100 - abs(180 - opposition_angle) * 2
        score += max(0, angle_quality * 0.35)

        return min(100, score)

    def get_hudson_opportunities(self, conditions: Dict) -> List[str]:
        """Get specific opportunities for Hudson Valley downwind runs"""
        opportunities = []

        wind_mph = conditions['wind_speed_mph']
        current_knots = conditions['current_speed_knots']
        quality = conditions['quality_score']

        # Location-specific opportunities
        if quality >= 80:
            opportunities.append("🌊 Epic downwind run from Beacon to Cold Spring")
            opportunities.append("📸 Perfect conditions for downwind photography")

        if quality >= 70:
            opportunities.append("🚀 Fast runs with current assistance")
            opportunities.append("🏄‍♂️ Surfing wind waves on the Hudson")

        if wind_mph >= 15:
            opportunities.append("🌪️ Practice advanced downwind techniques")
            opportunities.append("⚡ High-speed runs with good control")

        if current_knots >= 1.5:
            opportunities.append("🌊 Strong current push for effortless speed")
            opportunities.append("🎯 Navigation practice in moving water")

        # Route suggestions
        if conditions['wind_direction_text'] in ['N', 'NE', 'NW']:
            opportunities.append("📍 Launch from Beacon, ride south to Cold Spring")
        elif conditions['wind_direction_text'] in ['S', 'SE', 'SW']:
            opportunities.append("📍 Launch from Cold Spring, ride north to Beacon")

        return opportunities

    async def send_downwind_alert(self, conditions: Dict):
        """Send downwind alert to Discord channel"""
        try:
            channel = self.bot.get_channel(HUDSON_ALERT_CHANNEL_ID)
            if not channel:
                logger.error(f"Could not find Hudson alert channel: {HUDSON_ALERT_CHANNEL_ID}")
                return

            embed = self.create_downwind_embed(conditions)
            message = await channel.send(embed=embed)

            # Add reaction for interest
            await message.add_reaction("🛶")
            await message.add_reaction("🌊")
            await message.add_reaction("🎯")

            logger.info("Hudson Valley downwind alert sent successfully")

        except Exception as e:
            logger.error(f"Failed to send Hudson Valley alert: {e}")

    def create_downwind_embed(self, conditions: Dict) -> discord.Embed:
        """Create Discord embed for downwind alert"""
        quality_score = conditions['quality_score']

        # Determine embed color based on quality
        if quality_score >= 90:
            color = 0x9932CC  # Purple - Epic
            title_emoji = "🤩"
            quality_text = "EPIC"
        elif quality_score >= 80:
            color = 0x00FF00  # Green - Excellent
            title_emoji = "🎉"
            quality_text = "EXCELLENT"
        elif quality_score >= 70:
            color = 0xFFD700  # Gold - Very Good
            title_emoji = "😃"
            quality_text = "VERY GOOD"
        else:
            color = 0xFFA500  # Orange - Good
            title_emoji = "🙂"
            quality_text = "GOOD"

        embed = discord.Embed(
            title=f"{title_emoji} Hudson Valley Downwind Alert! {title_emoji}",
            description=f"**{quality_text}** conditions detected for downwind runs between Beacon & Cold Spring",
            color=color,
            timestamp=datetime.now()
        )

        # Conditions summary
        embed.add_field(
            name="🌬️ Wind Conditions",
            value=(
                f"**Speed:** {conditions['wind_speed_mph']:.1f} mph\n"
                f"**Direction:** {conditions['wind_direction_text']} ({conditions['wind_direction']}°)\n"
                f"**Time:** {conditions['time']}"
            ),
            inline=True
        )

        embed.add_field(
            name="🌊 Current Conditions",
            value=(
                f"**Speed:** {conditions['current_speed_knots']:.1f} knots\n"
                f"**Direction:** {conditions.get('current_direction_text', 'N/A')}\n"
                f"**Opposition:** {conditions['opposition_angle']:.0f}°"
            ),
            inline=True
        )

        embed.add_field(
            name="📊 Quality Score",
            value=f"**{quality_score:.0f}/100**\n{self.get_quality_description(quality_score)}",
            inline=True
        )

        # Opportunities
        if conditions.get('opportunities'):
            opportunities_text = "\n".join(conditions['opportunities'][:5])  # Limit to 5
            embed.add_field(
                name="🎯 Opportunities",
                value=opportunities_text,
                inline=False
            )

        # Safety and recommendations
        safety_notes = self.get_safety_recommendations(conditions)
        if safety_notes:
            embed.add_field(
                name="⚠️ Safety Notes",
                value="\n".join(safety_notes[:3]),
                inline=False
            )

        # Location info
        embed.add_field(
            name="📍 Area",
            value="Mid-Hudson Valley\nBeacon ↔ Cold Spring\nPeekskill ↔ Poughkeepsie",
            inline=False
        )

        embed.set_footer(text="Daily Hudson Valley Downwind Alert • Check conditions before launching")

        return embed

    def get_quality_description(self, score: float) -> str:
        """Get quality description for the score"""
        if score >= 90:
            return "Outstanding conditions!"
        elif score >= 80:
            return "Excellent for downwind runs"
        elif score >= 70:
            return "Very good conditions"
        elif score >= 60:
            return "Good conditions"
        else:
            return "Moderate conditions"

    def get_safety_recommendations(self, conditions: Dict) -> List[str]:
        """Get safety recommendations based on conditions"""
        recommendations = []

        wind_mph = conditions['wind_speed_mph']
        current_knots = conditions['current_speed_knots']

        if wind_mph > 20:
            recommendations.append("⚠️ Strong winds - advanced paddlers only")

        if current_knots > 2:
            recommendations.append("⚠️ Strong current - plan shuttle carefully")

        if conditions['quality_score'] >= 80:
            recommendations.append("📱 Share your location with emergency contacts")

        recommendations.append("🧭 Monitor weather changes throughout the day")
        recommendations.append("🚗 Arrange shuttle or car spot for one-way trips")

        return recommendations

    async def manual_check(self, ctx):
        """Manual check command for testing"""
        conditions = await self.check_downwind_conditions()

        if conditions:
            embed = self.create_downwind_embed(conditions)
            await ctx.send("🔍 **Manual Hudson Valley Check:**", embed=embed)
        else:
            await ctx.send("❌ No significant downwind conditions detected for Hudson Valley area")
