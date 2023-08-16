import logging
from datetime import datetime, time

import discord
from discord.ext import tasks
from epicstore_api import EpicGamesStoreAPI
from redbot.core import Config, app_commands, commands
from redbot.core.bot import Red

from .dataclasses import GameInfo


class EpicGamesChecker(commands.Cog):

    """Check epic games every hour and alert if there is a new game."""

    CHECK_MARK = "✅"
    default_global_settings = {
        "channels": [],
        "history": {
            "last_check": {},
            "historical": {},
        },
    }

    def __init__(self, bot):
        self.log = logging.getLogger(self.__class__.__name__)
        self.bot: Red = bot
        self.conf = Config.get_conf(self, identifier=26400736017)
        self.conf.register_global(**self.default_global_settings)
        self.epic_fail_count = 0
        self.check.start()

    async def cog_unload(self):
        """unload"""
        self.check.cancel()

    free_epic = app_commands.Group(
        name="free_epic",
        description="Free Epic Game Notifier",
    )

    @free_epic.command(
        name="add_channel",
        description="Add this channel to the list to notify.",
    )
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_channels=True)
    async def add_channel(self, ctx: discord.Interaction):
        """Add this channel to the alert channels"""
        async with self.conf.channels() as channels:
            channels.append(ctx.channel.id)
            channels = list(set(channels))

        await ctx.response.send_message("Done!")

    @free_epic.command(
        name="remove_channel",
        description="Remove this channel from the list to notify.",
    )
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_channels=True)
    async def remove_channel(self, ctx: discord.Interaction):
        """Remove this channel from the alert channels"""
        async with self.conf.channels() as channels, self.conf.history() as history:
            try:
                channels.remove(ctx.channel.id)
                channels = list(set(channels))
                history["last_check"].pop(str(ctx.channel.id), None)
            except Exception:  # pylint: disable=broad-except
                pass
        await ctx.response.send_message("Done!")

    @free_epic.command()
    @commands.is_owner()
    async def run_now(self, ctx: discord.Interaction, force: str = ""):
        force = bool(force)  # fix the type of force for the check
        await self.check(force)
        await ctx.response.send_message("Done!", ephemeral=True)

    async def _handle_fails(self):
        """Handles epic failing"""
        self.epic_fail_count += 1
        self.log.warning("Error getting epic games!", exc_info=1)
        if self.epic_fail_count >= 2:
            await self.bot.send_to_owners(
                f"Error getting epic games! Times errored: {self.epic_fail_count}"
            )

    # Want this to run 5 minutes past the hour every hour
    @tasks.loop(time=[time(t, 5) for t in range(24)])
    async def check(self, force: bool = False):
        """Check epic for new games."""
        self.log.debug("Checking Epic for free games!")
        try:
            epic = EpicGamesStoreAPI()
            games = GameInfo.make_from_response(epic.get_free_games())
            current_ids = [game.game_id for game in games]
            async with self.conf.history() as history, self.conf.channels() as channels:
                for channel_id in channels:
                    for game in games:
                        # Update the history and make sure it wasn't already sent.
                        history["historical"][game.game_id] = {
                            "last_seen": datetime.today().isoformat()
                        }
                        if (
                            game.game_id in history.get("last_check", {}).get(str(channel_id), [])
                            and not force
                        ):
                            continue
                        # If not found, send to the channel
                        channel = self.bot.get_channel(channel_id)
                        if not channel:
                            self.log.info("Channel %s did not exist, removing it.", channel_id)
                            channels.remove(channel_id)
                        await channel.send(embed=game.embed())
                    history["last_check"][str(channel_id)] = current_ids
            self.epic_fail_count = 0
        except Exception:  # pylint: disable=broad-except
            await self._handle_fails()
        self.log.debug("Finished checking Epic for free games!")
