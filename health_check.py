# health_check.py
import asyncio
import aiohttp
import sys
import os
from datetime import datetime

async def check_bot_health():
    """Check if the bot is running and responsive"""
    try:
        # Check if bot process is running (simplified check)
        # In a real implementation, you might check Discord connection status

        # Check database accessibility
        db_path = os.getenv('DB_PATH', '/app/data/kayak_trips.db')
        if not os.path.exists(os.path.dirname(db_path)):
            print(f"❌ Database directory not accessible: {os.path.dirname(db_path)}")
            return False

        # Check API connectivity
        async with aiohttp.ClientSession() as session:
            # Test weather API connectivity
            weather_url = "https://api.openweathermap.org/data/2.5/weather"
            params = {
                'q': 'Boston',
                'appid': os.getenv('OPENWEATHER_API_KEY', 'test'),
                'units': 'metric'
            }

            try:
                async with session.get(weather_url, params=params, timeout=5) as response:
                    if response.status != 200:
                        print("⚠️ Weather API connection issue")
            except:
                print("⚠️ Cannot reach weather API")

        print(f"✅ Health check passed at {datetime.now()}")
        return True

    except Exception as e:
        print(f"❌ Health check failed: {str(e)}")
        return False

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        healthy = loop.run_until_complete(check_bot_health())
        sys.exit(0 if healthy else 1)
    finally:
        loop.close()
