import logging
import time
from types import SimpleNamespace
from typing import Dict, Union

import discord
from redbot.core import Config, app_commands, commands
from redbot.core.bot import Red


class StatusSnooper(commands.Cog):
    """Snoops statuses and allows users to see last online time"""

    default_global_settings = {"users": {}}

    def __init__(self, bot: Red):
        self.bot = bot
        self.conf = Config.get_conf(self, identifier=4007)
        self.conf.register_global(**self.default_global_settings)
        self.log = logging.getLogger("StatusSnooper")
        self.ctx_menu = app_commands.ContextMenu(name="Last Online", callback=self.last_online)
        self.bot.tree.add_command(self.ctx_menu)

    @commands.Cog.listener("on_presence_update")
    async def update_status(self, before: discord.Member, after: discord.Member):
        """Save a status update"""
        async with self.conf.users() as users:
            user_id = str(after.id)
            current_data: Dict[str, list] = users.get(user_id, {})
            self._init_user(current_data)
            if before.status != after.status:
                self.log.debug(
                    "%s changed from %s to %s!", after.name, before.status, after.status
                )
                current_data["status"].append(
                    {
                        "before": before.raw_status,
                        "after": after.raw_status,
                        "timestamp": int(time.time()),
                    }
                )

            if before.activity != after.activity:
                self.log.debug(
                    "%s's activity changed from %s to %s!",
                    after.name,
                    str(before.activity),
                    str(after.activity),
                )
                current_data["activity"].append(
                    {
                        "before": str(before.activity),
                        "after": str(after.activity),
                        "timestamp": int(time.time()),
                    }
                )
            users[user_id] = current_data

    def _init_user(self, current_data):
        if not current_data.get("status"):
            current_data["status"] = []
        if not current_data.get("activity"):
            current_data["activity"] = []

    async def _get_last(self, guild, member):
        user_id = member.id
        async with self.conf.users() as users:
            info = users.get(str(user_id))
        # Need to get the user from the guild because for some reason
        # The member passed to the function shows as offline?
        member = next((m for m in guild.members if m.id == user_id), member)
        currently_online = member.status == discord.Status.online
        current = -1
        statuses = info.get("status")
        last = statuses[current]

        def while_logic(last_status):
            online_options = ["online", "idle", "dnd"]
            offline_options = ["offline", "invisible"]
            if currently_online:
                return (
                    last_status.get("before") not in offline_options
                    and last_status.get("after") not in offline_options
                )
            return (
                last_status.get("before") not in online_options
                and last_status.get("after") not in online_options
            )

        while while_logic(last):
            try:
                current -= 1
                last = statuses[current]
            except IndexError:
                last = None
                break
        return currently_online, last

    @app_commands.guild_only()
    async def last_online(
        self, ctx: discord.Interaction, member: Union[discord.Member, discord.User]
    ):
        """Sends when the user was last online or offline."""

        try:
            currently_online, last = await self._get_last(ctx.guild, member)
        except (AttributeError, IndexError):
            await ctx.response.send_message(
                "I don't have any history on that user.", ephemeral=True
            )
            return
        if not last:
            await ctx.response.send_message(
                f"That user has never been {'online' if not currently_online else 'offline'} in my history!",
                ephemeral=True,
            )
            return
        if member.status == discord.Status.online:
            await ctx.response.send_message(
                f"{member.display_name} has been online since <t:{last.get('timestamp')}:R>.",
                ephemeral=True,
            )
            return
        await ctx.response.send_message(
            f"{member.display_name} was last online <t:{last.get('timestamp')}:R>.",
            ephemeral=True,
        )

    @commands.command("last_online")
    @commands.is_owner()
    async def last_online_old(self, ctx: commands.Context, user_id: str):
        """! command for last_online for testing"""
        try:
            member = next((m for m in self.bot.get_all_members() if str(m.id) == user_id), None)
            if not member:
                await ctx.reply("That user doesn't exist.", mention_author=False)
                return
            currently_online, last = await self._get_last(ctx.guild, member)
        except (AttributeError, IndexError):
            await ctx.reply("I don't have any history on that user.", mention_author=False)
            return
        if not last:
            await ctx.reply(
                f"That user has never been {'online' if not currently_online else 'offline'} in my history!",
                mention_author=False,
            )
            return
        if member.status == discord.Status.online:
            await ctx.reply(
                f"{member.display_name} has been online since <t:{last.get('timestamp')}:R>.",
                mention_author=False,
            )
            return
        await ctx.reply(
            f"{member.display_name} was last online at <t:{last.get('timestamp')}:R>.",
            mention_author=False,
        )
