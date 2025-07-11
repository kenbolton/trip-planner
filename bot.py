# bot.py
import asyncio
import logging
import os
from datetime import datetime

import discord
from discord.ext import commands

from config import (
    DISCORD_TOKEN, DB_PATH, LOG_PATH, LOG_LEVEL, WEATHER_API_KEY,
    # CURRENT_API_KEY,
)

from current_service import CurrentService
from database import Database
from hudson_alert_service import HudsonValleyAlertService
from ice_system import ICESystem
from trip_planner import TripPlanner
from weather_service import WeatherService


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
intents.reactions = True  # Enable reaction events
bot = commands.Bot(command_prefix='!kayak ', intents=intents)


# Initialize services
try:
    # Ensure data directory exists
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

    db = Database(DB_PATH)
    db.add_trip_name_column()  # Add trip_name column for existing databases
    trip_planner = TripPlanner(db)
    ice_system = ICESystem(bot, db)
    logger.info("Services initialized successfully")

    # Initialize Hudson Valley alert service
    weather_service = WeatherService()
    current_service = CurrentService()
    hudson_alerts = HudsonValleyAlertService(
        bot, weather_service, current_service)
    logger.info("Hudson Valley alert service initialized")

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
        name="Hudson Valley conditions"
    )
    await bot.change_presence(activity=activity)

    # Start Hudson Valley monitoring
    await hudson_alerts.start_monitoring()


# Add a simple test event handler to debug reactions
@bot.event
async def on_raw_reaction_add(payload):
    """Raw reaction event for debugging and handling reactions"""
    logger.info(f"=== RAW REACTION EVENT ===")
    logger.info(f"Emoji: {payload.emoji}")
    logger.info(f"User ID: {payload.user_id}")
    logger.info(f"Message ID: {payload.message_id}")
    logger.info(f"Channel ID: {payload.channel_id}")
    logger.info(f"Guild ID: {payload.guild_id}")
    logger.info(f"=== END RAW REACTION EVENT ===")
    
    # Skip bot's own reactions
    if bot.user and payload.user_id == bot.user.id:
        logger.info(f"Ignoring reaction from bot itself")
        return
    
    # Get the channel and message
    try:
        if payload.guild_id:
            guild = bot.get_guild(payload.guild_id)
            if guild:
                channel = guild.get_channel(payload.channel_id)
            else:
                return
        else:
            channel = bot.get_channel(payload.channel_id)
        
        if not channel:
            logger.warning(f"Could not find channel {payload.channel_id}")
            return
            
        # Use the correct method to fetch message based on channel type
        if hasattr(channel, 'fetch_message'):
            message = await channel.fetch_message(payload.message_id)
        else:
            logger.warning(f"Channel {payload.channel_id} does not support fetch_message")
            return
            
        user = bot.get_user(payload.user_id)
        
        if not user:
            logger.warning(f"Could not find user {payload.user_id}")
            return
            
        logger.info(f"PROCESSING user reaction {payload.emoji} from {user.name}")
        
        # Call the original reaction handler logic
        await handle_reaction_logic(message, user, str(payload.emoji))
        
    except Exception as e:
        logger.error(f"Error in raw reaction handler: {e}")


async def handle_reaction_logic(message, user, emoji_str):
    """Handle the actual reaction logic (extracted from on_reaction_add)"""
    try:
        # Handle trip view reactions
        if hasattr(bot, 'trip_views') and message.id in bot.trip_views:
            trip_info = bot.trip_views[message.id]
            
            if user.id != trip_info['user_id']:
                return  # Only trip owner can interact
            
            if emoji_str == "▶️" and trip_info['can_start']:
                # Start trip
                trip_id = trip_info['trip_id']
                trip = db.get_trip_by_id(trip_id)
                
                if trip:
                    # Start ICE monitoring
                    duration = trip[5]  # duration is at index 5
                    asyncio.create_task(
                        ice_system.start_trip_monitoring(
                            trip_id,
                            user.id,
                            duration,
                            message.channel
                        )
                    )
                    
                    embed = discord.Embed(
                        title="🛶 Trip Started!",
                        description=f"ICE monitoring activated for Trip #{trip_id}",
                        color=0x00FF00
                    )
                    await message.channel.send(embed=embed)
                    
                    # Update the view
                    trip_info['is_active'] = True
                    trip_info['can_start'] = False
            
            elif emoji_str == "⏹️" and trip_info['is_active']:
                # Stop trip
                trip_id = trip_info['trip_id']
                if trip_id in ice_system.active_trips:
                    await ice_system._confirm_safe_return(trip_id)
                    
                    embed = discord.Embed(
                        title="⏹️ Trip Stopped",
                        description=f"ICE monitoring deactivated for Trip #{trip_id}",
                        color=0x00FF00
                    )
                    await message.channel.send(embed=embed)
                    
                    # Update the view
                    trip_info['is_active'] = False
            
            elif emoji_str == "✅" and trip_info['is_active']:
                # Manual check-in
                trip_id = trip_info['trip_id']
                if trip_id in ice_system.active_trips:
                    await ice_system._confirm_safe_return(trip_id)
                    
                    embed = discord.Embed(
                        title="✅ Manual Check-In Successful",
                        description="Thanks for checking in! ICE monitoring has been deactivated.",
                        color=0x00FF00
                    )
                    await message.channel.send(embed=embed)
                    
                    # Update the view
                    trip_info['is_active'] = False

        # Handle plan reactions (existing functionality)
        if hasattr(bot, 'temp_trips') and message.id in bot.temp_trips:
            trip_plan = bot.temp_trips[message.id]
            logger.info(f"Found temp trip for message {message.id}, reaction: {emoji_str}")
            
            if emoji_str == "📅":
                # Save trip
                logger.info(f"Saving trip for user {user.id}")
                saved_trip_id = db.add_trip(
                    user.id,
                    trip_plan['location'],
                    trip_plan['date'].strftime('%Y-%m-%d'),
                    trip_plan['time'].strftime('%H:%M'),
                    trip_plan['duration'],
                    str(user.id),  # participants
                    "Auto-ICE",  # emergency contact
                    trip_plan.get('trip_name')
                )
                logger.info(f"Trip saved with ID: {saved_trip_id}")
                
                embed = discord.Embed(
                    title="📅 Trip Saved!",
                    description=f"Trip saved as #{saved_trip_id}. Use `!kayak view {saved_trip_id}` to start when ready.",
                    color=0x00FF00
                )
                await message.channel.send(embed=embed)
                
            elif emoji_str == "🚨":
                # Quick start trip
                saved_trip_id = db.add_trip(
                    user.id,
                    trip_plan['location'],
                    trip_plan['date'].strftime('%Y-%m-%d'),
                    trip_plan['time'].strftime('%H:%M'),
                    trip_plan['duration'],
                    str(user.id),  # participants
                    "Auto-ICE",  # emergency contact
                    trip_plan.get('trip_name')
                )
                
                # Start ICE monitoring
                asyncio.create_task(
                    ice_system.start_trip_monitoring(
                        saved_trip_id,
                        user.id,
                        trip_plan['duration'],
                        message.channel
                    )
                )
                
                embed = discord.Embed(
                    title="🛶 Trip Started!",
                    description=f"Trip saved as #{saved_trip_id} and ICE monitoring activated!",
                    color=0x00FF00
                )
                await message.channel.send(embed=embed)
                
    except Exception as e:
        logger.error(f"Error in reaction logic handler: {e}")


@bot.command(name='hudson')
async def check_hudson(ctx):
    """Check current Hudson Valley downwind conditions"""
    await hudson_alerts.manual_check(ctx)


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
async def plan_trip(ctx, location, date_str, time_str, duration: int, *, trip_name=None):
    """Plan a kayak trip: !kayak plan "Boston Harbor" 2024-06-15 09:00 4 "Morning Harbor Paddle" """
    try:
        # Parse date and time
        trip_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        trip_time = datetime.strptime(time_str, '%H:%M').time()

        # Plan the trip
        trip_plan, error = await trip_planner.plan_trip(
            location, trip_date, trip_time, duration, trip_name)

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


@bot.command(name='list')
async def list_trips(ctx, limit: int = 10):
    """List your planned trips: !kayak list [limit]"""
    try:
        trips = db.get_user_trips(ctx.author.id, limit)
        
        if not trips:
            await ctx.send("❌ No trips found. Plan your first trip with `!kayak plan`")
            return

        embed = discord.Embed(
            title="🛶 Your Planned Trips",
            description=f"Showing {len(trips)} most recent trips",
            color=0x3498DB
        )

        for trip in trips:
            # trip format: (id, user_id, location, trip_date, start_time, duration, participants, emergency_contact, trip_name, created_at)
            trip_id, _, location, trip_date, start_time, duration, _, _, trip_name, created_at = trip
            
            trip_title = f"Trip #{trip_id}"
            if trip_name:
                trip_title += f": {trip_name}"
            
            trip_info = f"**Location:** {location}\n**Date:** {trip_date}\n**Time:** {start_time}\n**Duration:** {duration}h"
            
            # Check if trip is today
            from datetime import datetime, date
            today = date.today()
            trip_date_obj = datetime.strptime(trip_date, '%Y-%m-%d').date()
            
            if trip_date_obj == today:
                trip_info += "\n🟢 **Available for start today**"
            elif trip_date_obj < today:
                trip_info += "\n🔴 **Past trip**"
            else:
                trip_info += f"\n🟡 **Future trip**"
            
            embed.add_field(
                name=trip_title,
                value=trip_info,
                inline=False
            )

        embed.set_footer(text="Use `!kayak view <trip_id>` to see details and start a trip")
        await ctx.send(embed=embed)

    except Exception as e:
        await ctx.send(f"❌ Error listing trips: {str(e)}")


@bot.command(name='view')
async def view_trip(ctx, trip_id: int):
    """View trip details with start/stop options: !kayak view <trip_id>"""
    try:
        trip = db.get_trip_by_id(trip_id, ctx.author.id)
        
        if not trip:
            await ctx.send(f"❌ Trip #{trip_id} not found or you don't have permission to view it")
            return

        # trip format: (id, user_id, location, trip_date, start_time, duration, participants, emergency_contact, trip_name, created_at)
        trip_id, _, location, trip_date, start_time, duration, participants, emergency_contact, trip_name, created_at = trip
        
        title = f"🛶 Trip #{trip_id}"
        if trip_name:
            title += f": {trip_name}"
        
        embed = discord.Embed(
            title=title,
            color=0x3498DB
        )

        embed.add_field(name="📍 Location", value=location, inline=True)
        embed.add_field(name="📅 Date", value=trip_date, inline=True)
        embed.add_field(name="🕐 Time", value=start_time, inline=True)
        embed.add_field(name="⏱️ Duration", value=f"{duration} hours", inline=True)
        embed.add_field(name="👥 Participants", value=participants or "Not specified", inline=True)
        embed.add_field(name="🚨 Emergency Contact", value=emergency_contact or "Not specified", inline=True)
        
        # Check trip status
        from datetime import datetime, date
        today = date.today()
        trip_date_obj = datetime.strptime(trip_date, '%Y-%m-%d').date()
        
        # Check if trip is currently active
        is_active = trip_id in ice_system.active_trips
        
        if is_active:
            embed.add_field(
                name="🟢 Trip Status", 
                value="**ACTIVE** - ICE monitoring in progress", 
                inline=False
            )
        elif trip_date_obj == today:
            embed.add_field(
                name="🟡 Trip Status", 
                value="**Ready to start** - Click ▶️ to begin ICE monitoring", 
                inline=False
            )
        elif trip_date_obj < today:
            embed.add_field(
                name="🔴 Trip Status", 
                value="**Past trip** - Cannot start monitoring", 
                inline=False
            )
        else:
            embed.add_field(
                name="🟡 Trip Status", 
                value=f"**Future trip** - Can start on {trip_date}", 
                inline=False
            )

        message = await ctx.send(embed=embed)
        
        # Add reaction buttons based on trip status
        if is_active:
            await message.add_reaction("⏹️")  # Stop trip
            await message.add_reaction("✅")  # Manual check-in
        elif trip_date_obj == today:
            await message.add_reaction("▶️")  # Start trip
        
        # Store trip info for reaction handling
        if not hasattr(bot, 'trip_views'):
            bot.trip_views = {}
        bot.trip_views[message.id] = {
            'trip_id': trip_id,
            'user_id': ctx.author.id,
            'is_active': is_active,
            'can_start': trip_date_obj == today
        }

    except Exception as e:
        await ctx.send(f"❌ Error viewing trip: {str(e)}")


# Handle reaction events for trip view
@bot.event
async def on_reaction_add(reaction, user):
    """Handle reactions on trip view messages"""
    try:
        message = reaction.message
        logger.info(f"=== REACTION EVENT DETECTED ===")
        logger.info(f"Emoji: {reaction.emoji}")
        logger.info(f"User: {user.name} (ID: {user.id})")
        logger.info(f"Is Bot: {user.bot}")
        logger.info(f"Message ID: {message.id}")
        logger.info(f"Message Author: {message.author}")
        logger.info(f"Bot User: {bot.user.name if bot.user else 'None'} (ID: {bot.user.id if bot.user else 'None'})")
        
        # Check if this is the bot's own reaction
        if user.bot:
            logger.info(f"Ignoring reaction from bot user: {user.name} (bot={user.bot})")
            return
        
        logger.info(f"PROCESSING user reaction {reaction.emoji} from {user.name}")
    except Exception as e:
        logger.error(f"Error in reaction event handler: {e}")
        return
    
    # Handle trip view reactions
    if hasattr(bot, 'trip_views') and message.id in bot.trip_views:
        trip_info = bot.trip_views[message.id]
        
        if user.id != trip_info['user_id']:
            return  # Only trip owner can interact
        
        if str(reaction.emoji) == "▶️" and trip_info['can_start']:
            # Start trip
            trip_id = trip_info['trip_id']
            trip = db.get_trip_by_id(trip_id)
            
            if trip:
                # Start ICE monitoring
                duration = trip[5]  # duration is at index 5
                asyncio.create_task(
                    ice_system.start_trip_monitoring(
                        trip_id,
                        user.id,
                        duration,
                        message.channel
                    )
                )
                
                embed = discord.Embed(
                    title="🛶 Trip Started!",
                    description=f"ICE monitoring activated for Trip #{trip_id}",
                    color=0x00FF00
                )
                await message.channel.send(embed=embed)
                
                # Update the view
                trip_info['is_active'] = True
                trip_info['can_start'] = False
        
        elif str(reaction.emoji) == "⏹️" and trip_info['is_active']:
            # Stop trip
            trip_id = trip_info['trip_id']
            if trip_id in ice_system.active_trips:
                await ice_system._confirm_safe_return(trip_id)
                
                embed = discord.Embed(
                    title="⏹️ Trip Stopped",
                    description=f"ICE monitoring deactivated for Trip #{trip_id}",
                    color=0x00FF00
                )
                await message.channel.send(embed=embed)
                
                # Update the view
                trip_info['is_active'] = False
        
        elif str(reaction.emoji) == "✅" and trip_info['is_active']:
            # Manual check-in
            trip_id = trip_info['trip_id']
            if trip_id in ice_system.active_trips:
                await ice_system._confirm_safe_return(trip_id)
                
                embed = discord.Embed(
                    title="✅ Manual Check-In Successful",
                    description="Thanks for checking in! ICE monitoring has been deactivated.",
                    color=0x00FF00
                )
                await message.channel.send(embed=embed)
                
                # Update the view
                trip_info['is_active'] = False

    # Handle plan reactions (existing functionality)
    if hasattr(bot, 'temp_trips') and message.id in bot.temp_trips:
        trip_plan = bot.temp_trips[message.id]
        logger.info(f"Found temp trip for message {message.id}, reaction: {reaction.emoji}")
        
        if str(reaction.emoji) == "📅":
            # Save trip
            logger.info(f"Saving trip for user {user.id}")
            saved_trip_id = db.add_trip(
                user.id,
                trip_plan['location'],
                trip_plan['date'].strftime('%Y-%m-%d'),
                trip_plan['time'].strftime('%H:%M'),
                trip_plan['duration'],
                str(user.id),  # participants
                "Auto-ICE",  # emergency contact
                trip_plan.get('trip_name')
            )
            logger.info(f"Trip saved with ID: {saved_trip_id}")
            
            embed = discord.Embed(
                title="📅 Trip Saved!",
                description=f"Trip saved as #{saved_trip_id}. Use `!kayak view {saved_trip_id}` to start when ready.",
                color=0x00FF00
            )
            await message.channel.send(embed=embed)
            
        elif str(reaction.emoji) == "🚨":
            # Quick start trip
            saved_trip_id = db.add_trip(
                user.id,
                trip_plan['location'],
                trip_plan['date'].strftime('%Y-%m-%d'),
                trip_plan['time'].strftime('%H:%M'),
                trip_plan['duration'],
                str(user.id),  # participants
                "Auto-ICE",  # emergency contact
                trip_plan.get('trip_name')
            )
            
            # Start ICE monitoring
            asyncio.create_task(
                ice_system.start_trip_monitoring(
                    saved_trip_id,
                    user.id,
                    trip_plan['duration'],
                    message.channel
                )
            )
            
            embed = discord.Embed(
                title="🛶 Trip Started!",
                description=f"Trip saved as #{saved_trip_id} and ICE monitoring activated!",
                color=0x00FF00
            )
            await message.channel.send(embed=embed)


@bot.command(name='start')
async def start_trip(ctx, trip_id: int):
    """Start trip monitoring: !kayak start <trip_id>"""
    try:
        trip = db.get_trip_by_id(trip_id, ctx.author.id)
        
        if not trip:
            await ctx.send(f"❌ Trip #{trip_id} not found or you don't have permission to start it")
            return
        
        # Check if trip is today
        from datetime import datetime, date
        today = date.today()
        trip_date = trip[3]  # trip_date is at index 3
        trip_date_obj = datetime.strptime(trip_date, '%Y-%m-%d').date()
        
        if trip_date_obj != today:
            await ctx.send(f"❌ Can only start trips scheduled for today. Trip is scheduled for {trip_date}")
            return
        
        # Check if already active
        if trip_id in ice_system.active_trips:
            await ctx.send(f"❌ Trip #{trip_id} is already active")
            return
        
        # Start ICE monitoring
        duration = trip[5]  # duration is at index 5
        asyncio.create_task(
            ice_system.start_trip_monitoring(
                trip_id,
                ctx.author.id,
                duration,
                ctx.channel
            )
        )

        embed = discord.Embed(
            title="🛶 Trip Started!",
            description=f"ICE monitoring activated for Trip #{trip_id} ({duration} hours)",
            color=0x00FF00
        )
        embed.add_field(
            name="Important",
            value="You'll receive a check-in reminder when your trip duration expires. Make sure to respond!",
            inline=False
        )

        await ctx.send(embed=embed)

    except Exception as e:
        await ctx.send(f"❌ Error starting trip: {str(e)}")


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
        name="Hudson Valley Conditions",
        value=(
            "`!kayak hudson`\n"
            "Check current downwind conditions in the Hudson Valley"
        ),
        inline=False
    )

    embed.add_field(
        name="Trip Planning",
        value=(
            "`!kayak plan \"Location\" YYYY-MM-DD HH:MM hours \"Trip Name\"`\n"
            "Plan a kayak trip with weather and conditions\n"
            "(Trip name is optional)\n"
            "In the trip view, you can start ICE monitoring with reactions.\n"
            "Use the `!kayak start <trip_id>` command to start monitoring for a saved trip.\n"
            "📅 (Calendar): Saves the trip to database and shows a confirmation message with the trip ID\n"
            "🚨 (Emergency): Saves the trip AND immediately starts ICE monitoring"
        ),
        inline=False
    )

    embed.add_field(
        name="Trip Management",
        value=(
            "`!kayak list [limit]` - List your planned trips\n"
            "`!kayak view <trip_id>` - View trip details with start/stop options\n"
            "`!kayak start <trip_id>` - Start ICE monitoring for a trip"
        ),
        inline=False
    )

    embed.add_field(
        name="Trip Management",
        value=(
            "`!kayak list [limit]` - List your planned trips\n"
            "`!kayak view <trip_id>` - View trip details with start/stop options\n"
            "`!kayak start <trip_id>` - Start ICE monitoring for a trip"
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
