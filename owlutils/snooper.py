import contextlib
import logging
import time
from datetime import datetime, timedelta
from io import BytesIO
from tempfile import NamedTemporaryFile
from typing import Dict, Union

import discord
import pandas as pd
import plotly.express as pex
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
        self.ctx_menu = app_commands.ContextMenu(
            name="Last Online", callback=self.last_online
        )
        self.bot.tree.add_command(self.ctx_menu)

    @commands.Cog.listener("on_presence_update")
    async def update_status(self, before: discord.Member, after: discord.Member):
        """Save a status update"""
        async with self.conf.users() as users:
            user_id = str(after.id)
            current_data: Dict[str, Union[list, dict]] = users.get(user_id, {})
            self._init_user(current_data)
            timestamp = int(time.time())
            if before.status != after.status:
                self.log.debug(
                    "%s changed from %s to %s!", after.name, before.status, after.status
                )
                current_data["status"].append(
                    {
                        "before": before.raw_status,
                        "after": after.raw_status,
                        "timestamp": timestamp,
                    }
                )
                current_data["most_recent"][before.raw_status] = timestamp

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
                        "timestamp": timestamp,
                    }
                )
            users[user_id] = current_data

    def _init_user(self, current_data):
        if not current_data.get("most_recent"):
            current_data["most_recent"] = {}
        if not current_data.get("status"):
            current_data["status"] = []
        if not current_data.get("activity"):
            current_data["activity"] = []

    def _get_message(
        self,
        recent: dict,
        currently_online: bool,
        currently_offline: bool,
        member: discord.Member,
    ):
        try:
            if currently_online:
                last = recent["offline"]
                return f"{member.display_name} has been online since <t:{last}:R>."
            if currently_offline:
                last = recent["online"]
                return f"{member.display_name} was last online <t:{last}:R>."

            return (
                f"{member.display_name} has been {member.status} since <t:{recent['online']}:R>.\n"
                f"They have been online since <t:{recent['offline']}:R>."
            )
        except KeyError as k_e:
            return f"{member.display_name} has never been {k_e.args[0]} in my history."

    @contextlib.contextmanager
    def generate_image(self, times: list[dict]):
        last_day = int((datetime.now() - timedelta(days=1)).timestamp())

        self.log.info("Parsing through %s entries in user status history..", len(times))
        status_changes = [s for s in times if s["timestamp"] >= last_day]
        if not status_changes:
            yield None
            return
        self.log.info("Parsed down to %s entries for the graph.", len(status_changes))
        last = last_day
        steps = []
        for s in status_changes:
            steps.append(
                {
                    "": "",
                    "start": str(
                        datetime.fromtimestamp(last).isoformat(" ", "seconds")
                    ),
                    "finish": str(
                        datetime.fromtimestamp(s["timestamp"]).isoformat(" ", "seconds")
                    ),
                    "status": str(s["before"]),
                }
            )
            last = s["timestamp"]
        steps.append(
            {
                "": "",
                "start": str(datetime.fromtimestamp(last).isoformat(" ", "seconds")),
                "finish": str(
                    datetime.fromtimestamp(datetime.now().timestamp()).isoformat(
                        " ", "seconds"
                    )
                ),
                "status": str(s["after"]),
            }
        )
        df = pd.DataFrame(steps, dtype=str)
        timeline = pex.timeline(
            df,
            x_start="start",
            x_end="finish",
            y="",
            color="status",
            height=250,
            color_discrete_map={
                "online": "green",
                "idle": "orange",
                "dnd": "red",
                "offline": "gray",
            },
        )
        timeline.update_traces(marker_line_width=0)
        with NamedTemporaryFile() as tmpf:
            timeline.write_image(tmpf)
            tmpf.seek(0)
            yield tmpf

    @app_commands.guild_only()
    async def last_online(
        self, ctx: discord.Interaction, member: Union[discord.Member, discord.User]
    ):
        """Sends when the user was last online or offline."""
        await ctx.response.defer(ephemeral=True)
        try:
            # Have to fetch the member manually from the guild
            # Because for some reason it passed it with it always offline on app interaction.
            member = next((m for m in ctx.guild.members if m.id == member.id), member)
            currently_online = member.status == discord.Status.online
            currently_offline = member.status in [
                discord.Status.offline,
                discord.Status.invisible,
            ]
            async with self.conf.users() as users:
                recent = users[str(member.id)]["most_recent"]

                with self.generate_image(users[str(member.id)]["status"]) as image:
                    kwargs = {
                        "content": self._get_message(
                            recent, currently_online, currently_offline, member
                        ),
                        "ephemeral": True,
                    }
                    if image:
                        kwargs["file"] = discord.File(
                            BytesIO(image.read()), filename="plot.png"
                        )
                    await ctx.followup.send(**kwargs)

        except (AttributeError, IndexError, KeyError):
            await ctx.followup.send(
                "I don't have any history on that user.", ephemeral=True
            )
            return

    @commands.command("last_online")
    @commands.is_owner()
    async def last_online_old(self, ctx: commands.Context, user_id: str):
        """! command for last_online for testing"""
        try:
            member = next(
                (m for m in self.bot.get_all_members() if str(m.id) == user_id), None
            )
            if not member:
                await ctx.reply("That user doesn't exist.", mention_author=False)
                return
            currently_online = member.status == discord.Status.online
            currently_offline = member.status in [
                discord.Status.offline,
                discord.Status.invisible,
            ]
            async with self.conf.users() as users:
                recent = users[str(member.id)]["most_recent"]
        except (AttributeError, IndexError, KeyError):
            await ctx.reply(
                "I don't have any history on that user.", mention_author=False
            )
            return
        message = self._get_message(recent, currently_online, currently_offline, member)

        await ctx.reply(
            message,
            mention_author=False,
        )
