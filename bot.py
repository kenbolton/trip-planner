# bot.py
import discord
from discord.ext import commands
import asyncio
import logging
import os
from datetime import datetime, timedelta
from database import Database
from trip_planner import TripPlanner
from ice_system import ICESystem
from config import *


# Setup logging
def setup_logging():
    log_dir = LOG_PATH
    os.makedirs(log_dir, exist_ok=True)

    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(f'{log_dir}/kayak_bot.log'),
            logging.StreamHandler()
        ]
    )

    # Discord logging
    discord.utils.setup_logging(level=logging.INFO)


setup_logging()
logger = logging.getLogger(__name__)

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!kayak ', intents=intents)

# Initialize services
try:
    # Ensure data directory exists
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

    db = Database(DB_PATH)
    trip_planner = TripPlanner(db)
    ice_system = ICESystem(bot, db)
    logger.info("Services initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize services: {e}")
    raise


@bot.event
async def on_ready():
    logger.info(f'{bot.user} has launched and is ready for kayak adventures!')
    print(f'🛶 {bot.user} is online and ready!')

    # Set bot status
    activity = discord.Activity(
        type=discord.ActivityType.watching,
        name="the tides and weather"
    )
    await bot.change_presence(activity=activity)


@bot.event
async def on_command_error(ctx, error):
    """Global error handler"""
    logger.error(f"Command error in {ctx.command}: {error}")

    if isinstance(error, commands.CommandNotFound):
        await ctx.send(
            "❌ Command not found. Use `!kayak help` for available commands.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❌ Missing required argument: {error.param}")
    else:
        await ctx.send(f"❌ An error occurred: {str(error)}")


@bot.command(name='status')
async def bot_status(ctx):
    """Check bot status and health"""
    try:
        # Database check
        db_status = "✅ Connected" if os.path.exists(
            DB_PATH) else "❌ Not found"

        # API status (simplified)
        api_status = "✅ Available" if WEATHER_API_KEY else "❌ Not configured"

        embed = discord.Embed(
            title="🤖 Bot Status",
            color=0x00FF00
        )
        embed.add_field(name="Database", value=db_status, inline=True)
        embed.add_field(name="Weather API", value=api_status, inline=True)
        embed.add_field(
            name="Active Trips",
            value=f"{len(ice_system.active_trips)} monitored",
            inline=True
        )
        embed.add_field(
            name="Uptime",
            value=f"Since {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            inline=False
        )

        await ctx.send(embed=embed)
        logger.info(f"Status check requested by {ctx.author}")

    except Exception as e:
        logger.error(f"Status check failed: {e}")
        await ctx.send("❌ Status check failed")


@bot.command(name='plan')
async def plan_trip(ctx, location, date_str, time_str, duration: int):
    """Plan a kayak trip: !kayak plan "Boston Harbor" 2024-06-15 09:00 4"""
    try:
        # Parse date and time
        trip_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        trip_time = datetime.strptime(time_str, '%H:%M').time()

        # Plan the trip
        trip_plan, error = await trip_planner.plan_trip(
            location, trip_date, trip_time, duration)

        if error:
            await ctx.send(f"❌ Error: {error}")
            return

        # Create and send embed
        embed = trip_planner.create_trip_embed(trip_plan)
        message = await ctx.send(embed=embed)

        # Add reaction buttons
        await message.add_reaction("📅")  # Save trip
        await message.add_reaction("🚨")  # Start ICE monitoring

        # Store temp trip data
        bot.temp_trips = getattr(bot, 'temp_trips', {})
        bot.temp_trips[message.id] = trip_plan

    except ValueError as e:
        await ctx.send(
            "❌ Invalid date/time format. Use YYYY-MM-DD for date and HH:MM for "
            "time.")
    except Exception as e:
        await ctx.send(f"❌ Error planning trip: {str(e)}")


@bot.command(name='ice')
async def manage_ice(ctx, action, *args):
    """
    Manage ICE contacts: !kayak ice add "John Doe" "555-1234" "Spouse" primary
    """
    if action == 'add':
        if len(args) < 3:
            await ctx.send(
                "❌ Usage: !kayak ice add \"Name\" \"Phone\" \"Relationship\" [primary]")
            return

        name, phone, relationship = args[:3]
        is_primary = len(args) > 3 and args[3].lower() == 'primary'

        db.add_ice_contact(ctx.author.id, name, phone, relationship, is_primary)

        embed = discord.Embed(
            title="✅ ICE Contact Added",
            description=f"Added {name} as {'primary ' if is_primary else ''}emergency contact",
            color=0x00FF00
        )
        await ctx.send(embed=embed)

    elif action == 'list':
        contacts = db.get_ice_contacts(ctx.author.id)

        if not contacts:
            await ctx.send("No ICE contacts found. Add one with `!kayak ice add`")
            return

        embed = discord.Embed(
            title="🚨 Your ICE Contacts",
            color=0x3498DB
        )

        for contact in contacts:
            status = "🟢 PRIMARY" if contact[5] else "🔵 Secondary"
            embed.add_field(
                name=f"{contact[2]} ({contact[4]})",
                value=f"{contact[3]}\n{status}",
                inline=True
            )

        await ctx.send(embed=embed)


@bot.command(name='start')
async def start_trip(ctx, trip_id: int = None):
    """Start trip monitoring: !kayak start [trip_id]"""
    if not hasattr(bot, 'temp_trips') or not bot.temp_trips:
        await ctx.send(
            "❌ No planned trips found. Plan a trip first with `!kayak plan`")
        return

    # For demo, use the most recent trip plan
    trip_plan = list(bot.temp_trips.values())[-1]

    # Save trip to database
    saved_trip_id = db.add_trip(
        ctx.author.id,
        trip_plan['location'],
        trip_plan['date'].strftime('%Y-%m-%d'),
        trip_plan['time'].strftime('%H:%M'),
        trip_plan['duration'],
        str(ctx.author.id),  # participants
        "Auto-ICE"  # emergency contact
    )

    # Start ICE monitoring
    asyncio.create_task(
        ice_system.start_trip_monitoring(
            saved_trip_id,
            ctx.author.id,
            trip_plan['duration'],
            ctx.channel
        )
    )

    embed = discord.Embed(
        title="🛶 Trip Started!",
        description=f"ICE monitoring activated for {trip_plan['duration']} hours",
        color=0x00FF00
    )
    embed.add_field(
        name="Important",
        value="You'll receive a check-in reminder when your trip duration expires. Make sure to respond!",
        inline=False
    )

    await ctx.send(embed=embed)


@bot.command(name='checkin')
async def manual_checkin(ctx):
    """Manual check-in: !kayak checkin"""
    # Find active trip for user
    user_trips = [trip_id for trip_id, trip in ice_system.active_trips.items()
                  if trip['user_id'] == ctx.author.id]

    if not user_trips:
        await ctx.send("❌ No active trips found for check-in")
        return

    # Check in for the most recent trip
    trip_id = user_trips[0]
    await ice_system._confirm_safe_return(trip_id)

    embed = discord.Embed(
        title="✅ Manual Check-In Successful",
        description="Thanks for checking in! ICE monitoring has been deactivated.",
        color=0x00FF00
    )
    await ctx.send(embed=embed)


bot.remove_command('help')


@bot.command(name='help')
async def help_command(ctx):
    """Display help information"""
    embed = discord.Embed(
        title="🛶 Kayak Trip Planner Bot Commands",
        description="Plan safe kayaking adventures with weather, tides, and emergency monitoring!",
        color=0x3498DB
    )

    embed.add_field(
        name="Trip Planning",
        value=(
            "`!kayak plan \"Location\" YYYY-MM-DD HH:MM hours`\n"
            "Plan a kayak trip with weather and conditions"
        ),
        inline=False
    )

    embed.add_field(
        name="Emergency Contacts",
        value=(
            "`!kayak ice add \"Name\" \"Phone\" \"Relation\" [primary]`\n"
            "`!kayak ice list` - Show your contacts"
        ),
        inline=False
    )

    embed.add_field(
        name="Trip Monitoring",
        value=(
            "`!kayak start` - Begin ICE monitoring\n"
            "`!kayak checkin` - Manual check-in\n"
            "`!kayak status` - Bot health status"
        ),
        inline=False
    )

    await ctx.send(embed=embed)


# Graceful shutdown handler
async def shutdown_handler():
    """Handle graceful shutdown"""
    logger.info("Shutting down bot...")

    # Notify active trips
    for trip_id, trip in ice_system.active_trips.items():
        try:
            user = bot.get_user(trip['user_id'])
            if user:
                await user.send("🤖 Bot is restarting. Your trip monitoring will resume shortly.")
        except:
            pass

    await bot.close()

if __name__ == '__main__':
    try:
        bot.run(DISCORD_TOKEN)
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot crashed: {e}")
        raise
