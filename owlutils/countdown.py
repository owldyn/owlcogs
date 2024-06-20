import logging
import time
from datetime import datetime
from types import SimpleNamespace
from typing import Dict, TypedDict, Union

import discord
import pandas as pd
from discord.ext import tasks
from redbot.core import Config, app_commands, commands
from redbot.core.bot import Red


class Countdown(commands.Cog):
    def __init__(self, bot: Red):
        self.bot = bot
        self.conf = Config.get_conf(self, identifier=4007)
        self.conf.register_global(**{"timestamp": []})
        self.log = logging.getLogger("owlutlis.Countdown")
        self.update.start()

    async def cog_unload(self):
        self.update.cancel()

    @commands.is_owner()
    @commands.command()
    async def set_countdown_timestamp(
        self, ctx: commands.Context, timestamp: int, name: str
    ):
        """Set the timestamp and name for a countdown"""
        async with self.conf.timestamp() as timestamp_:
            timestamp_.append((timestamp, name))
        self.update.restart()
        await ctx.react_quietly(":thumbsup:")

    @tasks.loop(minutes=1)
    async def update(self):
        async with self.conf.timestamp() as data:
            if len(data) > 0:
                timestamp, name = data[0]
                until = timestamp - datetime.now().timestamp()
                if until < 0:
                    del data[0]
                    if len(data) > 0:
                        timestamp, name = data[0]
                        until = timestamp - datetime.now().timestamp()
                    else:
                        return

                if until < 3600:
                    until_string = f"{int(until/60)} minutes until {name}!"
                else:
                    until_string = f"{int(until/3600)} hours until {name}."
                await self.bot.change_presence(
                    activity=discord.CustomActivity(name=until_string)
                )
