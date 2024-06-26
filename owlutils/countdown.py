import logging
from datetime import datetime

import discord
from discord.ext import tasks
from redbot.core import Config, commands
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
        timestamp_: list
        async with self.conf.timestamp() as timestamp_:
            timestamp_.append((timestamp, name))
            timestamp_.sort(key=lambda x: x[0])
        self.update.restart()
        await ctx.react_quietly(":thumbsup:")

    @commands.is_owner()
    @commands.command()
    async def delete_first_countdown(self, ctx):
        """Set the timestamp and name for a countdown"""
        async with self.conf.timestamp() as timestamp_:
            if len(timestamp_) > 0:
                del timestamp_[0]
        self.update.restart()
        await ctx.react_quietly(":thumbsup:")

    @tasks.loop(minutes=1)
    async def update(self):
        async with self.conf.timestamp() as data:
            if len(data) > 0:
                timestamp, name = data[0]
                until = timestamp - datetime.now().timestamp()
                if until < 0:
                    if until > -300:
                        await self.bot.change_presence(
                            activity=discord.CustomActivity(name=f"{name} is here!")
                        )
                    del data[0]
                    if len(data) > 0:
                        timestamp, name = data[0]
                        until = timestamp - datetime.now().timestamp()
                    else:
                        await self.bot.change_presence(activity=None)
                        return

                if until < 3600:
                    until_string = f"{int(until/60)} minutes until {name}!"
                else:
                    until_string = f"{round(until/3600,1)} hours until {name}."
                await self.bot.change_presence(
                    activity=discord.CustomActivity(name=until_string)
                )
            else:
                await self.bot.change_presence(activity=None)
                return
