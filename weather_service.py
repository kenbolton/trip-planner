# weather_service.py
import math
from datetime import datetime

import aiohttp

from config import WEATHER_API_KEY, WEATHER_BASE_URL


class WeatherService:
    def __init__(self):
        self.api_key = WEATHER_API_KEY
        self.base_url = WEATHER_BASE_URL

    async def get_weather_forecast(self, lat, lon, target_date):
        """Get weather forecast for specific coordinates and date"""
        async with aiohttp.ClientSession() as session:
            # Current weather
            current_url = f"{self.base_url}/weather"
            current_params = {
                'lat': lat,
                'lon': lon,
                'appid': self.api_key,
                'units': 'metric'
            }

            # 5-day forecast
            forecast_url = f"{self.base_url}/forecast"
            forecast_params = {
                'lat': lat,
                'lon': lon,
                'appid': self.api_key,
                'units': 'metric'
            }

            try:
                async with session.get(current_url, params=current_params) as current_resp:
                    current_data = await current_resp.json()

                async with session.get(forecast_url, params=forecast_params) as forecast_resp:
                    forecast_data = await forecast_resp.json()

                return self._format_weather_data(current_data, forecast_data, target_date)

            except Exception as e:
                return f"Error fetching weather data: {str(e)}"

    def _format_weather_data(self, current, forecast, target_date):
        """Format weather data for Discord embed"""
        weather_info = {
            'current': {
                'temp': current['main']['temp'],
                'feels_like': current['main']['feels_like'],
                'humidity': current['main']['humidity'],
                'wind_speed': current['wind']['speed'],
                'wind_direction': current['wind'].get('deg', 0),
                'description': current['weather'][0]['description'],
                'visibility': current.get('visibility', 'N/A')
            },
            'forecast': []
        }

        # Extract relevant forecast data for the target date
        for item in forecast['list']:
            forecast_date = datetime.fromtimestamp(item['dt']).date()
            if forecast_date == target_date:
                weather_info['forecast'].append({
                    'time': datetime.fromtimestamp(item['dt']).strftime('%H:%M'),
                    'temp': item['main']['temp'],
                    'wind_speed': item['wind']['speed'],
                    'wind_direction': item['wind'].get('deg', 0),
                    'description': item['weather'][0]['description'],
                    'precipitation': item.get('rain', {}).get('3h', 0)
                })

        return weather_info

    def get_wind_direction_text(self, degrees):
        """Convert wind direction degrees to text"""
        directions = [
            'N', 'NNE', 'NE', 'ENE',
            'E', 'ESE', 'SE', 'SSE',
            'S', 'SSW', 'SW', 'WSW',
            'W', 'WNW', 'NW', 'NNW',
        ]

        # Calculate index (16 directions, 360/16 = 22.5 degrees per direction)
        index = round(degrees / 22.5) % 16
        return directions[index]

    def convert_wind_speed(self, speed_ms, target_unit='knots'):
        """Convert wind speed from m/s to other units"""
        conversions = {
            'knots': speed_ms * 1.944,
            'mph': speed_ms * 2.237,
            'kmh': speed_ms * 3.6,
            'beaufort': self._ms_to_beaufort(speed_ms)
        }
        return round(conversions.get(target_unit, speed_ms), 1)

    def _ms_to_beaufort(self, speed_ms):
        """Convert m/s to Beaufort scale"""
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
        elif speed_ms < 13.9:
            return 6
        elif speed_ms < 17.2:
            return 7
        elif speed_ms < 20.8:
            return 8
        elif speed_ms < 24.5:
            return 9
        elif speed_ms < 28.5:
            return 10
        elif speed_ms < 32.7:
            return 11
        else:
            return 12

    def get_uv_index_description(self, uv_index):
        """Get UV index description and safety recommendations"""
        if uv_index <= 2:
            return {"level": "Low", "color": 0x00FF00, "advice": "No protection needed"}
        elif uv_index <= 5:
            return {"level": "Moderate", "color": 0xFFFF00, "advice": "Some protection needed"}
        elif uv_index <= 7:
            return {"level": "High", "color": 0xFF8C00, "advice": "Protection essential"}
        elif uv_index <= 10:
            return {"level": "Very High", "color": 0xFF0000, "advice": "Extra protection required"}
        else:
            return {"level": "Extreme", "color": 0x8B008B, "advice": "Avoid sun exposure"}

    def assess_kayaking_conditions(self, weather_data):
        """Assess weather conditions specifically for kayaking safety"""
        conditions = weather_data['current']
        safety_factors = {
            'wind_safety': self._assess_wind_safety(conditions['wind_speed']),
            'visibility_safety': self._assess_visibility_safety(conditions.get('visibility', 10000)),
            'precipitation_safety': self._assess_precipitation_safety(weather_data.get('forecast', [])),
            'temperature_safety': self._assess_temperature_safety(conditions['temp'])
        }

        # Calculate overall safety score
        total_score = sum(factor['score'] for factor in safety_factors.values())
        avg_score = total_score / len(safety_factors)

        return {
            'overall_score': avg_score,
            'factors': safety_factors,
            'recommendation': self._get_kayaking_recommendation(avg_score),
            'warnings': self._get_weather_warnings(safety_factors)
        }

    def _assess_wind_safety(self, wind_speed_ms):
        """Assess wind safety for kayaking"""
        wind_knots = self.convert_wind_speed(wind_speed_ms, 'knots')

        if wind_knots <= 10:
            return {"score": 100, "level": "Excellent", "description": "Calm conditions"}
        elif wind_knots <= 15:
            return {"score": 80, "level": "Good", "description": "Light winds"}
        elif wind_knots <= 20:
            return {"score": 60, "level": "Moderate", "description": "Moderate winds - experienced paddlers"}
        elif wind_knots <= 25:
            return {"score": 40, "level": "Challenging", "description": "Strong winds - advanced only"}
        else:
            return {"score": 20, "level": "Dangerous", "description": "Very strong winds - not recommended"}

    def _assess_visibility_safety(self, visibility_m):
        """Assess visibility safety for kayaking"""
        if visibility_m >= 5000:
            return {"score": 100, "level": "Excellent", "description": "Clear visibility"}
        elif visibility_m >= 2000:
            return {"score": 80, "level": "Good", "description": "Good visibility"}
        elif visibility_m >= 1000:
            return {"score": 60, "level": "Moderate", "description": "Reduced visibility"}
        elif visibility_m >= 500:
            return {"score": 40, "level": "Poor", "description": "Poor visibility"}
        else:
            return {"score": 20, "level": "Dangerous", "description": "Very poor visibility"}

    def _assess_precipitation_safety(self, forecast_data):
        """Assess precipitation safety for kayaking"""
        max_precipitation = 0

        for forecast in forecast_data:
            precip = forecast.get('precipitation', 0)
            if precip > max_precipitation:
                max_precipitation = precip

        if max_precipitation == 0:
            return {"score": 100, "level": "Excellent", "description": "No precipitation"}
        elif max_precipitation <= 2:
            return {"score": 80, "level": "Good", "description": "Light precipitation"}
        elif max_precipitation <= 5:
            return {"score": 60, "level": "Moderate", "description": "Moderate precipitation"}
        elif max_precipitation <= 10:
            return {"score": 40, "level": "Heavy", "description": "Heavy precipitation"}
        else:
            return {"score": 20, "level": "Severe", "description": "Severe precipitation"}

    def _assess_temperature_safety(self, temp_celsius):
        """Assess temperature safety for kayaking (hypothermia risk)"""
        if temp_celsius >= 20:
            return {"score": 100, "level": "Comfortable", "description": "Warm conditions"}
        elif temp_celsius >= 15:
            return {"score": 90, "level": "Good", "description": "Mild conditions"}
        elif temp_celsius >= 10:
            return {"score": 70, "level": "Cool", "description": "Cool - dress appropriately"}
        elif temp_celsius >= 5:
            return {"score": 50, "level": "Cold", "description": "Cold - warm gear essential"}
        elif temp_celsius >= 0:
            return {"score": 30, "level": "Very Cold", "description": "Very cold - hypothermia risk"}
        else:
            return {"score": 10, "level": "Freezing", "description": "Freezing - extreme hypothermia risk"}

    def _get_kayaking_recommendation(self, score):
        """Get kayaking recommendation based on safety score"""
        if score >= 85:
            return {"level": "GO", "color": 0x00FF00, "message": "Excellent conditions for kayaking"}
        elif score >= 70:
            return {"level": "CAUTION", "color": 0xFFFF00, "message": "Good conditions with minor concerns"}
        elif score >= 50:
            return {"level": "ADVISORY", "color": 0xFF8C00, "message": "Challenging conditions - experienced paddlers only"}
        elif score >= 30:
            return {"level": "WARNING", "color": 0xFF4500, "message": "Dangerous conditions - not recommended"}
        else:
            return {"level": "DANGER", "color": 0xFF0000, "message": "Severe conditions - do not kayak"}

    def _get_weather_warnings(self, safety_factors):
        """Generate specific weather warnings for kayakers"""
        warnings = []

        for factor_name, factor_data in safety_factors.items():
            if factor_data['score'] < 60:
                if factor_name == 'wind_safety':
                    warnings.append("⚠️ High wind speeds - consider postponing trip")
                elif factor_name == 'visibility_safety':
                    warnings.append("⚠️ Reduced visibility - stay close to shore")
                elif factor_name == 'precipitation_safety':
                    warnings.append("⚠️ Precipitation expected - waterproof gear essential")
                elif factor_name == 'temperature_safety':
                    warnings.append("⚠️ Cold conditions - hypothermia risk, wear appropriate gear")

        return warnings

    async def get_marine_weather(self, lat, lon):
        """Get marine-specific weather data including wave height and sea conditions"""
        # Note: This would require a marine weather API like NOAA Marine Weather
        # For now, we'll use standard weather data with marine interpretations
        async with aiohttp.ClientSession() as session:
            marine_url = f"{self.base_url}/weather"
            params = {
                'lat': lat,
                'lon': lon,
                'appid': self.api_key,
                'units': 'metric'
            }

            try:
                async with session.get(marine_url, params=params) as response:
                    data = await response.json()
                    return self._format_marine_data(data)
            except Exception as e:
                return f"Error fetching marine weather: {str(e)}"

    def _format_marine_data(self, weather_data):
        """Format weather data with marine-specific interpretations"""
        marine_info = {
            'sea_state': self._estimate_sea_state(weather_data['wind']['speed']),
            'water_temp_estimate': self._estimate_water_temp(weather_data['main']['temp']),
            'kayak_comfort': self._assess_kayak_comfort(weather_data),
            'marine_warnings': self._get_marine_warnings(weather_data)
        }

        return marine_info

    def _estimate_sea_state(self, wind_speed_ms):
        """Estimate sea state based on wind speed (Douglas Sea Scale approximation)"""
        wind_knots = self.convert_wind_speed(wind_speed_ms, 'knots')

        if wind_knots < 1:
            return {"state": 0, "description": "Calm (glassy)", "wave_height": "0m"}
        elif wind_knots < 4:
            return {"state": 1, "description": "Calm (ripples)", "wave_height": "0-0.1m"}
        elif wind_knots < 7:
            return {"state": 2, "description": "Smooth (wavelets)", "wave_height": "0.1-0.5m"}
        elif wind_knots < 11:
            return {"state": 3, "description": "Slight", "wave_height": "0.5-1.25m"}
        elif wind_knots < 17:
            return {"state": 4, "description": "Moderate", "wave_height": "1.25-2.5m"}
        elif wind_knots < 22:
            return {"state": 5, "description": "Rough", "wave_height": "2.5-4m"}
        else:
            return {"state": 6, "description": "Very rough", "wave_height": "4m+"}

    def _estimate_water_temp(self, air_temp):
        """Estimate water temperature based on air temperature (rough approximation)"""
        # Water is typically 5-10°C cooler than air in most conditions
        estimated_water_temp = air_temp - 7

        if estimated_water_temp < 10:
            risk_level = "High hypothermia risk"
        elif estimated_water_temp < 15:
            risk_level = "Moderate hypothermia risk"
        elif estimated_water_temp < 20:
            risk_level = "Low hypothermia risk"
        else:
            risk_level = "Comfortable"

        return {
            "estimated_temp": estimated_water_temp,
            "risk_level": risk_level,
            "recommendation": "Wear appropriate thermal protection" if estimated_water_temp < 15 else "Standard gear sufficient"
        }

    def _assess_kayak_comfort(self, weather_data):
        """Assess overall comfort for kayaking"""
        temp = weather_data['main']['temp']
        humidity = weather_data['main']['humidity']
        wind = weather_data['wind']['speed']

        # Simple comfort index calculation
        comfort_score = 100

        # Temperature comfort (optimal 15-25°C)
        if temp < 10 or temp > 30:
            comfort_score -= 30
        elif temp < 15 or temp > 25:
            comfort_score -= 15

        # Humidity impact
        if humidity > 80:
            comfort_score -= 10
        elif humidity < 30:
            comfort_score -= 5

        # Wind impact
        wind_knots = self.convert_wind_speed(wind, 'knots')
        if wind_knots > 15:
            comfort_score -= 20
        elif wind_knots > 10:
            comfort_score -= 10

        if comfort_score >= 80:
            return {"level": "Excellent", "score": comfort_score}
        elif comfort_score >= 60:
            return {"level": "Good", "score": comfort_score}
        elif comfort_score >= 40:
            return {"level": "Fair", "score": comfort_score}
        else:
            return {"level": "Poor", "score": comfort_score}

    def _get_marine_warnings(self, weather_data):
        """Generate marine-specific warnings"""
        warnings = []
        wind_speed = weather_data['wind']['speed']
        visibility = weather_data.get('visibility', 10000)

        wind_knots = self.convert_wind_speed(wind_speed, 'knots')

        if wind_knots > 20:
            warnings.append("🌊 Small craft advisory - high winds")

        if visibility < 1000:
            warnings.append("🌫️ Reduced visibility - navigation hazard")

        if 'rain' in weather_data or 'snow' in weather_data:
            warnings.append("🌧️ Precipitation - reduced visibility and comfort")

        return warnings

    def check_wind_current_interaction(self, wind_direction, wind_speed_ms, current_direction, current_speed_knots):
        """Check for favorable wind-current interaction for sea kayaking adventures"""
        wind_knots = self.convert_wind_speed(wind_speed_ms, 'knots')

        # Sea kayakers love wind - check for exciting conditions at 8+ knots
        if wind_knots < 8:
            return None

        # Calculate direction difference
        direction_diff = abs(wind_direction - current_direction)

        # Handle circular nature of compass directions (0° = 360°)
        if direction_diff > 180:
            direction_diff = 360 - direction_diff

        # Check for different wind-current relationships
        is_opposing = 150 <= direction_diff <= 210  # Opposing (challenging/exciting)
        is_following = direction_diff <= 30 or direction_diff >= 330  # Following (fast rides)
        is_beam = 60 <= direction_diff <= 120 or 240 <= direction_diff <= 300  # Beam (surf opportunities)

        if wind_knots >= 8 and (is_opposing or is_following or is_beam):
            # Determine sea kayaking conditions quality
            sea_conditions = self._assess_sea_kayaking_conditions(
                wind_knots, current_speed_knots, direction_diff, is_opposing, is_following, is_beam
            )

            return {
                'alert_type': 'SEA_KAYAK_CONDITIONS',
                'wind_speed_knots': wind_knots,
                'current_speed_knots': current_speed_knots,
                'direction_difference': direction_diff,
                'wind_direction_text': self.get_wind_direction_text(wind_direction),
                'current_direction_text': self.get_wind_direction_text(current_direction),
                'interaction_type': self._get_interaction_type(is_opposing, is_following, is_beam),
                'conditions': sea_conditions,
                'message': self._generate_sea_kayak_alert_message(sea_conditions, wind_knots, current_speed_knots)
            }

        return None

    def _get_interaction_type(self, is_opposing, is_following, is_beam):
        """Determine the type of wind-current interaction"""
        if is_opposing:
            return {
                'type': 'OPPOSING',
                'emoji': '🌊',
                'description': 'Wind against current - steep waves and challenging conditions'
            }
        elif is_following:
            return {
                'type': 'FOLLOWING',
                'emoji': '🏄‍♂️',
                'description': 'Wind with current - fast downwind runs and surfing'
            }
        elif is_beam:
            return {
                'type': 'BEAM',
                'emoji': '🌪️',
                'description': 'Wind across current - side surfing and ferry opportunities'
            }
        else:
            return {
                'type': 'MIXED',
                'emoji': '🌀',
                'description': 'Complex wind-current interaction'
            }

    def _assess_sea_kayaking_conditions(self, wind_knots, current_knots, direction_diff, is_opposing, is_following, is_beam):
        """Assess the quality of wind-current conditions for sea kayaking"""
        base_score = 0
        skill_level = "BEGINNER"
        excitement_level = "MODERATE"

        # Wind speed scoring for sea kayaking (more wind = more fun, but also more challenging)
        if 8 <= wind_knots <= 12:
            base_score += 30
            skill_level = "BEGINNER"
            excitement_level = "MODERATE"
        elif 12 < wind_knots <= 18:
            base_score += 45
            skill_level = "INTERMEDIATE"
            excitement_level = "HIGH"
        elif 18 < wind_knots <= 25:
            base_score += 50  # Sweet spot for experienced paddlers
            skill_level = "ADVANCED"
            excitement_level = "VERY_HIGH"
        elif 25 < wind_knots <= 30:
            base_score += 40
            skill_level = "EXPERT"
            excitement_level = "EXTREME"
        else:
            base_score += 25  # Getting dangerous
            skill_level = "EXPERT_ONLY"
            excitement_level = "EXTREME"

        # Current speed impact
        if 0.5 <= current_knots <= 1.5:
            base_score += 20  # Gentle current
        elif 1.5 < current_knots <= 3:
            base_score += 35  # Good current for interaction
        elif 3 < current_knots <= 5:
            base_score += 30  # Strong current - exciting but challenging
        else:
            base_score += 15  # Very strong current - dangerous

        # Interaction type bonuses
        if is_opposing:
            base_score += 20  # Challenging waves, great for skill building
            if wind_knots > 15:
                excitement_level = "VERY_HIGH"
        elif is_following:
            base_score += 25  # Downwind surfing opportunities
            excitement_level = "HIGH"
        elif is_beam:
            base_score += 15  # Side surfing and ferry practice

        # Direction precision bonus (more precise angles are more interesting)
        precision_bonus = min(10, (180 - abs(180 - direction_diff)) / 18)
        base_score += precision_bonus

        # Determine overall quality
        if base_score >= 80:
            quality_level = 'EPIC'
            color = 0x9932CC  # Purple
            emoji = '🤩'
            description = 'Epic sea kayaking conditions!'
        elif base_score >= 65:
            quality_level = 'EXCELLENT'
            color = 0x00FF00  # Green
            emoji = '🎉'
            description = 'Excellent conditions for adventure!'
        elif base_score >= 50:
            quality_level = 'VERY_GOOD'
            color = 0xFFD700  # Gold
            emoji = '😃'
            description = 'Very good conditions!'
        elif base_score >= 35:
            quality_level = 'GOOD'
            color = 0xFFA500  # Orange
            emoji = '🙂'
            description = 'Good conditions for experienced paddlers'
        else:
            quality_level = 'CHALLENGING'
            color = 0xFF4500  # Red-orange
            emoji = '😬'
            description = 'Challenging conditions - experts only'

        return {
            'level': quality_level,
            'color': color,
            'emoji': emoji,
            'description': description,
            'skill_level': skill_level,
            'excitement_level': excitement_level,
            'score': base_score
        }

    def _generate_sea_kayak_alert_message(self, conditions, wind_knots, current_knots):
        """Generate the sea kayaking conditions alert message"""
        interaction_type = self._get_interaction_type(True, False, False)  # This would be passed in

        base_message = (
            f"{conditions['emoji']} *SEA KAYAK ALERT!* {conditions['emoji']}\n\n"
            f"Perfect conditions for sea kayaking adventure!\n"
            f"**Wind:** {wind_knots:.1f} knots\n"
            f"**Current:** {current_knots:.1f} knots\n"
            f"**Interaction:** {interaction_type['description']}\n"
            f"**Quality:** {conditions['level']} - {conditions['description']}\n"
            f"**Skill Level:** {conditions['skill_level']}\n"
            f"**Excitement:** {conditions['excitement_level']}"
        )

        # Add specific sea kayaking opportunities
        opportunities = self._get_sea_kayak_opportunities(wind_knots, current_knots, conditions)
        if opportunities:
            base_message += "\n\n**Opportunities:**\n" + "\n".join([f"🌊 {opp}" for opp in opportunities])

        # Add safety considerations for sea kayaking
        safety_notes = self._get_sea_kayak_safety_notes(wind_knots, current_knots, conditions)
        if safety_notes:
            base_message += "\n\n**Safety Notes:**\n" + "\n".join([f"⚠️ {note}" for note in safety_notes])

        # Add gear recommendations
        gear_tips = self._get_sea_kayak_gear_tips(wind_knots, conditions)
        if gear_tips:
            base_message += "\n\n**Gear Recommendations:**\n" + "\n".join([f"🎒 {tip}" for tip in gear_tips])

        return base_message

    def _get_sea_kayak_opportunities(self, wind_knots, current_knots, conditions):
        """Get specific opportunities for sea kayaking in these conditions"""
        opportunities = []

        if wind_knots >= 12:
            opportunities.append("Downwind surfing on wind waves")
            opportunities.append("Practice advanced bracing techniques")

        if wind_knots >= 15:
            opportunities.append("Rough water boat handling practice")
            opportunities.append("Wave piercing and climbing skills")

        if current_knots >= 2:
            opportunities.append("Current ferry practice")
            opportunities.append("Eddy line surfing")

        if wind_knots >= 18 and current_knots >= 2:
            opportunities.append("Advanced rough water navigation")
            opportunities.append("Storm paddling technique practice")

        if conditions['excitement_level'] in ['HIGH', 'VERY_HIGH']:
            opportunities.append("Photography of dramatic seascapes")
            opportunities.append("Testing new gear in real conditions")

        return opportunities

    def _get_sea_kayak_safety_notes(self, wind_knots, current_knots, conditions):
        """Get safety considerations specific to sea kayaking"""
        safety_notes = []

        if wind_knots > 20:
            safety_notes.append("Strong winds - ensure solid roll and rescue skills")
            safety_notes.append("Stay close to safe landing areas")

        if current_knots > 3:
            safety_notes.append("Strong currents - watch for tidal races and overfalls")
            safety_notes.append("Plan routes accounting for current set and drift")

        if conditions['skill_level'] in ['ADVANCED', 'EXPERT', 'EXPERT_ONLY']:
            safety_notes.append("Advanced conditions - paddle with experienced partners")
            safety_notes.append("File detailed float plan with emergency contacts")

        if wind_knots > 15 and current_knots > 2:
            safety_notes.append("Complex conditions - be prepared for rapid changes")
            safety_notes.append("Consider shorter routes with multiple bail-out options")

        safety_notes.append("Monitor weather for changes throughout the day")
        safety_notes.append("Ensure all safety gear is accessible and functional")

        return safety_notes

    def _get_sea_kayak_gear_tips(self, wind_knots, conditions):
        """Get gear recommendations for these sea kayaking conditions"""
        gear_tips = []

        if wind_knots >= 15:
            gear_tips.append("Low-profile deck rigging to reduce windage")
            gear_tips.append("Spare paddle secured on deck")
            gear_tips.append("VHF radio in waterproof case")

        if conditions['skill_level'] in ['ADVANCED', 'EXPERT', 'EXPERT_ONLY']:
            gear_tips.append("Storm paddle for backup")
            gear_tips.append("GPS with waypoints for navigation in rough conditions")
            gear_tips.append("Flares and signaling devices")

        if wind_knots >= 20:
            gear_tips.append("Full immersion gear (drysuit recommended)")
            gear_tips.append("Helmet for rough water protection")

        gear_tips.append("High-visibility colors for safety")
        gear_tips.append("Emergency bivvy and extra warm layers")
        gear_tips.append("Extra food and water for extended conditions")

        return gear_tips

    def analyze_sea_kayak_potential(self, weather_data, tide_data, current_data):
        """Analyze overall sea kayaking potential for the session"""
        kayak_alerts = []

        if not current_data or not isinstance(current_data, list):
            # Even without current data, check for good wind conditions
            wind_speed = weather_data['current']['wind_speed']
            wind_knots = self.convert_wind_speed(wind_speed, 'knots')

            if wind_knots >= 12:
                return [{
                    'alert_type': 'WIND_ONLY_CONDITIONS',
                    'wind_speed_knots': wind_knots,
                    'message': f"🌊 Great wind conditions for sea kayaking! {wind_knots:.1f} knots"
                }]
            return []

        wind_speed = weather_data['current']['wind_speed']
        wind_direction = weather_data['current']['wind_direction']

        # Check each current prediction
        for current in current_data:
            if isinstance(current, dict):
                current_direction = self._parse_current_direction(current.get('direction', ''))
                current_speed = current.get('speed', 0)

                if current_direction is not None:
                    interaction = self.check_wind_current_interaction(
                        wind_direction, wind_speed, current_direction, current_speed
                    )

                    if interaction:
                        interaction['time'] = current.get('time', 'Unknown')
                        kayak_alerts.append(interaction)

        return kayak_alerts

    def _parse_current_direction(self, direction_str):
        """Parse current direction from various formats"""
        if not direction_str:
            return None

        # Handle different direction formats
        direction_str = str(direction_str).upper().strip()

        # If it's already a number, return it
        try:
            return float(direction_str)
        except ValueError:
            pass

        # Direction text to degrees mapping
        direction_map = {
            'N': 0, 'NNE': 22.5, 'NE': 45, 'ENE': 67.5,
            'E': 90, 'ESE': 112.5, 'SE': 135, 'SSE': 157.5,
            'S': 180, 'SSW': 202.5, 'SW': 225, 'WSW': 247.5,
            'W': 270, 'WNW': 292.5, 'NW': 315, 'NNW': 337.5
        }

        # Check if the direction is in the map
        if direction_str in direction_map:
            return direction_map[direction_str]

        # Try partial matches for common abbreviations
        for direction, degrees in direction_map.items():
            if direction in direction_str:
                return degrees

        # Try to parse as a degree value with various formats
        try:
            # Remove common suffixes and characters
            clean_str = direction_str.replace('°', '').replace('DEG', '').replace('DEGREES', '')
            return float(clean_str)
        except ValueError:
            return None

    def get_sea_state_description(self, wind_speed_ms):
        """Get detailed sea state description for sea kayakers"""
        wind_knots = self.convert_wind_speed(wind_speed_ms, 'knots')

        if wind_knots < 1:
            return {
                'state': 'Glass Off',
                'description': 'Mirror-like water surface',
                'kayak_impact': 'Perfect for beginners and photography',
                'wave_height': '0m',
                'color': 0x87CEEB
            }
        elif wind_knots < 4:
            return {
                'state': 'Light Air',
                'description': 'Small ripples, very slight waves',
                'kayak_impact': 'Easy paddling, great for skill practice',
                'wave_height': '0-0.1m',
                'color': 0x87CEEB
            }
        elif wind_knots < 7:
            return {
                'state': 'Light Breeze',
                'description': 'Small wavelets, crests do not break',
                'kayak_impact': 'Pleasant conditions, slight resistance',
                'wave_height': '0.1-0.5m',
                'color': 0x00CED1
            }
        elif wind_knots < 11:
            return {
                'state': 'Gentle Breeze',
                'description': 'Large wavelets, some crests begin to break',
                'kayak_impact': 'Good conditions for intermediate paddlers',
                'wave_height': '0.5-1m',
                'color': 0x32CD32
            }
        elif wind_knots < 16:
            return {
                'state': 'Moderate Breeze',
                'description': 'Small waves, fairly frequent white horses',
                'kayak_impact': 'Exciting conditions, bracing skills needed',
                'wave_height': '1-1.5m',
                'color': 0xFFD700
            }
        elif wind_knots < 22:
            return {
                'state': 'Fresh Breeze',
                'description': 'Moderate waves, many white horses, some spray',
                'kayak_impact': 'Challenging conditions for experienced paddlers',
                'wave_height': '1.5-2.5m',
                'color': 0xFF8C00
            }
        elif wind_knots < 28:
            return {
                'state': 'Strong Breeze',
                'description': 'Large waves, white foam crests, spray',
                'kayak_impact': 'Advanced skills required, rough water expertise',
                'wave_height': '2.5-4m',
                'color': 0xFF4500
            }
        elif wind_knots < 34:
            return {
                'state': 'Near Gale',
                'description': 'Sea heaps up, foam blown in streaks',
                'kayak_impact': 'Expert only conditions, storm paddling',
                'wave_height': '4-5.5m',
                'color': 0xFF0000
            }
        else:
            return {
                'state': 'Gale+',
                'description': 'High waves, dense foam, poor visibility',
                'kayak_impact': 'Dangerous conditions - stay off the water',
                'wave_height': '5.5m+',
                'color': 0x8B0000
            }

    def calculate_apparent_wind(self, true_wind_speed, true_wind_direction, kayak_speed, kayak_heading):
        """Calculate apparent wind for sea kayakers (useful for sail assistance or wind awareness)"""

        # Convert to radians for calculation
        true_wind_rad = math.radians(true_wind_direction)
        kayak_heading_rad = math.radians(kayak_heading)

        # Calculate wind components
        true_wind_x = true_wind_speed * math.sin(true_wind_rad)
        true_wind_y = true_wind_speed * math.cos(true_wind_rad)

        # Calculate kayak velocity components
        kayak_x = kayak_speed * math.sin(kayak_heading_rad)
        kayak_y = kayak_speed * math.cos(kayak_heading_rad)

        # Calculate apparent wind components
        apparent_wind_x = true_wind_x - kayak_x
        apparent_wind_y = true_wind_y - kayak_y

        # Calculate apparent wind speed and direction
        apparent_wind_speed = math.sqrt(apparent_wind_x**2 + apparent_wind_y**2)
        apparent_wind_direction = math.degrees(math.atan2(apparent_wind_x, apparent_wind_y))

        # Normalize direction to 0-360
        if apparent_wind_direction < 0:
            apparent_wind_direction += 360

        return {
            'speed_knots': apparent_wind_speed,
            'direction_degrees': apparent_wind_direction,
            'direction_text': self.get_wind_direction_text(apparent_wind_direction),
            'relative_to_kayak': self._get_relative_wind_description(apparent_wind_direction, kayak_heading)
        }

    def _get_relative_wind_description(self, wind_direction, kayak_heading):
        """Get wind direction relative to kayak heading"""
        relative_angle = (wind_direction - kayak_heading) % 360

        if relative_angle <= 22.5 or relative_angle >= 337.5:
            return "Head wind"
        elif 22.5 < relative_angle <= 67.5:
            return "Port bow"
        elif 67.5 < relative_angle <= 112.5:
            return "Port beam"
        elif 112.5 < relative_angle <= 157.5:
            return "Port quarter"
        elif 157.5 < relative_angle <= 202.5:
            return "Following wind"
        elif 202.5 < relative_angle <= 247.5:
            return "Starboard quarter"
        elif 247.5 < relative_angle <= 292.5:
            return "Starboard beam"
        else:
            return "Starboard bow"

    def get_wind_comfort_index(self, weather_data):
        """Calculate comfort index specifically for sea kayakers"""
        temp = weather_data['current']['temp']
        wind_speed = weather_data['current']['wind_speed']
        humidity = weather_data['current']['humidity']

        wind_knots = self.convert_wind_speed(wind_speed, 'knots')

        # Base comfort from temperature (optimal 12-22°C for sea kayaking)
        if 12 <= temp <= 22:
            temp_comfort = 100
        elif 8 <= temp < 12 or 22 < temp <= 26:
            temp_comfort = 80
        elif 4 <= temp < 8 or 26 < temp <= 30:
            temp_comfort = 60
        elif 0 <= temp < 4 or 30 < temp <= 35:
            temp_comfort = 40
        else:
            temp_comfort = 20

        # Wind comfort for sea kayakers (they love wind!)
        if 8 <= wind_knots <= 15:
            wind_comfort = 100  # Perfect for sea kayaking
        elif 15 < wind_knots <= 20:
            wind_comfort = 90   # Exciting conditions
        elif 4 <= wind_knots < 8:
            wind_comfort = 70   # Light conditions
        elif 20 < wind_knots <= 25:
            wind_comfort = 80   # Challenging but fun
        elif wind_knots < 4:
            wind_comfort = 50   # Too calm for excitement
        else:
            wind_comfort = 30   # Getting dangerous

        # Humidity impact (less important on water)
        if 40 <= humidity <= 70:
            humidity_comfort = 100
        elif 30 <= humidity < 40 or 70 < humidity <= 80:
            humidity_comfort = 90
        else:
            humidity_comfort = 80

        # Weighted average (wind is more important for sea kayakers)
        overall_comfort = (temp_comfort * 0.4 + wind_comfort * 0.5 + humidity_comfort * 0.1)

        return {
            'overall_score': round(overall_comfort),
            'temperature_score': temp_comfort,
            'wind_score': wind_comfort,
            'humidity_score': humidity_comfort,
            'description': self._get_comfort_description(overall_comfort),
            'recommendations': self._get_comfort_recommendations(temp_comfort, wind_comfort, temp, wind_knots)
        }

    def _get_comfort_description(self, score):
        """Get comfort description based on score"""
        if score >= 90:
            return {"level": "Excellent", "emoji": "🤩", "color": 0x00FF00}
        elif score >= 75:
            return {"level": "Very Good", "emoji": "😄", "color": 0x32CD32}
        elif score >= 60:
            return {"level": "Good", "emoji": "🙂", "color": 0xFFD700}
        elif score >= 45:
            return {"level": "Fair", "emoji": "😐", "color": 0xFFA500}
        elif score >= 30:
            return {"level": "Poor", "emoji": "😕", "color": 0xFF8C00}
        else:
            return {"level": "Very Poor", "emoji": "😤", "color": 0xFF0000}

    def _get_comfort_recommendations(self, temp_score, wind_score, temp, wind_knots):
        """Get specific recommendations based on comfort scores"""
        recommendations = []

        if temp_score < 60:
            if temp < 10:
                recommendations.append("Cold conditions - consider drysuit or thick wetsuit")
                recommendations.append("Bring extra warm layers and hot drinks")
            elif temp > 25:
                recommendations.append("Warm conditions - ensure adequate sun protection")
                recommendations.append("Bring extra water and electrolyte replacement")

        if wind_score < 50:
            if wind_knots < 4:
                recommendations.append("Light winds - perfect for beginners or relaxed paddling")
                recommendations.append("Consider exploring sheltered areas or photography")
            elif wind_knots > 25:
                recommendations.append("Strong winds - only for expert sea kayakers")
                recommendations.append("Ensure advanced rescue skills and safety equipment")

        if wind_score >= 80:
            recommendations.append("Great wind conditions for adventure!")
            recommendations.append("Perfect for practicing advanced techniques")

        return recommendations
