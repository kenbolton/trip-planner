# ice_system.py
import discord
import asyncio
from datetime import datetime, timedelta
from database import Database

class ICESystem:
    def __init__(self, bot, db):
        self.bot = bot
        self.db = db
        self.active_trips = {}

    async def start_trip_monitoring(self, trip_id, user_id, duration_hours, channel):
        """Start monitoring a trip for ICE purposes"""
        self.active_trips[trip_id] = {
            'user_id': user_id,
            'start_time': datetime.now(),
            'duration': duration_hours,
            'channel': channel,
            'check_in_required': datetime.now() + timedelta(hours=duration_hours + 1)
        }

        # Schedule check-in reminder
        await asyncio.sleep(duration_hours * 3600)
        await self._send_check_in_reminder(trip_id)

    async def _send_check_in_reminder(self, trip_id):
        """Send check-in reminder to user"""
        if trip_id not in self.active_trips:
            return

        trip = self.active_trips[trip_id]
        user = self.bot.get_user(trip['user_id'])

        if user:
            embed = discord.Embed(
                title="🚨 Trip Check-In Required",
                description="Please confirm you've returned safely from your kayak trip.",
                color=0xFF6B35
            )
            embed.add_field(
                name="Actions",
                value="React with ✅ to confirm safe return\nReact with 🆘 if you need help",
                inline=False
            )

            message = await user.send(embed=embed)
            await message.add_reaction("✅")
            await message.add_reaction("🆘")

            # Wait for reaction or timeout
            try:
                reaction, _ = await self.bot.wait_for(
                    'reaction_add',
                    timeout=3600,  # 1 hour timeout
                    check=lambda r, u: u.id == trip['user_id'] and str(r.emoji) in ['✅', '🆘']
                )

                if str(reaction.emoji) == '✅':
                    await self._confirm_safe_return(trip_id)
                else:
                    await self._trigger_emergency_response(trip_id)

            except asyncio.TimeoutError:
                await self._trigger_emergency_response(trip_id)

    async def _confirm_safe_return(self, trip_id):
        """Confirm user has returned safely"""
        if trip_id in self.active_trips:
            trip = self.active_trips[trip_id]
            user = self.bot.get_user(trip['user_id'])

            if user:
                embed = discord.Embed(
                    title="✅ Safe Return Confirmed",
                    description="Glad to hear you're back safely!",
                    color=0x00FF00
                )
                await user.send(embed=embed)

            # Clean up
            del self.active_trips[trip_id]

    async def _trigger_emergency_response(self, trip_id):
        """Trigger emergency response protocol"""
        if trip_id not in self.active_trips:
            return

        trip = self.active_trips[trip_id]
        ice_contacts = self.db.get_ice_contacts(trip['user_id'])
        user = self.bot.get_user(trip['user_id'])

        # Send emergency notification to ICE channel
        ice_channel = self.bot.get_channel(trip['channel'].guild.id)

        embed = discord.Embed(
            title="🚨 EMERGENCY - OVERDUE KAYAKER",
            description=f"User {user.mention if user else 'Unknown'} has not checked in from their kayak trip.",
            color=0xFF0000
        )
        embed.add_field(
            name="Trip Start Time",
            value=trip['start_time'].strftime('%Y-%m-%d %H:%M'),
            inline=True
        )
        embed.add_field(
            name="Expected Duration",
            value=f"{trip['duration']} hours",
            inline=True
        )
        embed.add_field(
            name="Overdue Since",
            value=trip['check_in_required'].strftime('%Y-%m-%d %H:%M'),
            inline=True
        )

        if ice_contacts:
            contact_info = "\n".join([
                f"**{contact[2]}** ({contact[4]}): {contact[3]}"
                for contact in ice_contacts
            ])
            embed.add_field(
                name="Emergency Contacts",
                value=contact_info,
                inline=False
            )

        await ice_channel.send("@everyone", embed=embed)

        # Notify emergency contacts if available
        for contact in ice_contacts:
            if contact[5]:  # is_primary
                try:
                    # In a real implementation, you'd integrate with SMS/phone services
                    print(f"EMERGENCY: Contact {contact[2]} at {contact[3]} - Kayaker overdue!")
                except:
                    pass
