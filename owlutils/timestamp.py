import logging
import re
from datetime import datetime
from typing import cast

import discord
import zoneinfo
from dateutil.parser import parse
from dateutil.tz import UTC
from redbot.core import Config, app_commands, commands
from redbot.core.bot import Red
from zoneinfo import ZoneInfo


class Timestamp(commands.Cog):
    def __init__(self, bot: Red):
        self.bot = bot
        self.conf = Config.get_conf(self, identifier=4007)
        self.log = logging.getLogger("owlutils.timestamp")

    timestamps = app_commands.Group(
        name="timestamps",
        description="Automatic timestamps!",
    )

    async def get_timezones(self, interaction, current):
        selections = sorted(
            (
                app_commands.Choice(name=z, value=z)
                for z in zoneinfo.available_timezones()
                if current.lower() in z.lower()
            ),
            key=lambda x: x.value,
        )
        return selections[:25]

    @timestamps.command(name="set_timezone")
    @app_commands.autocomplete(timezone=get_timezones)
    async def set_timezone(self, ctx: discord.Interaction, timezone: str):
        try:
            tz = ZoneInfo(timezone)
        except Exception:
            await ctx.response.send_message("That timezone doesn't exist!")
            return
        await self.conf.user(ctx.user).set({"timezone": timezone})
        tz = ZoneInfo(await self.conf.user(ctx.user).get_raw("timezone"))
        await ctx.response.send_message(
            f"Done! Your current time should be {datetime.now(tz).strftime(r'%Y-%m-%d %H:%M:%S')}"
        )

    @commands.Cog.listener("on_message_without_command")
    async def print_timezone(self, message: discord.Message):
        if "<" in message.content and ">" in message.content:
            match = re.search(r"\<([^\>]*)\>", message.content)
            if match:
                try:
                    parsed_time = parse(match.group(1)).replace(tzinfo=UTC)

                    ctx: commands.Context = await self.bot.get_context(message)
                    try:
                        timezone = cast(
                            str,
                            await self.conf.user(message.author).get_raw("timezone"),
                        )
                    except Exception:
                        await ctx.reply(
                            "You haven't set up your timezone yet! Do that with /timestamps set_timezone."
                        )
                        return
                    offset = parsed_time.astimezone(ZoneInfo(timezone)).utcoffset()

                    time = int(
                        parsed_time.timestamp()
                        - (offset.total_seconds() if offset else 0)
                    )
                    await ctx.reply(f"<t:{time}:f>", mention_author=False)

                except Exception as e:
                    return
