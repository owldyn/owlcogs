import logging
import re
from datetime import datetime

import discord
from discord.ext import tasks
from redbot.core import Config, commands
from redbot.core.bot import Red

log = logging.getLogger("owlcogs.submarine_reminder")


class SubmarineReminder(commands.Cog):
    default_global_settings = {"times_and_names": []}

    def __init__(self, bot):
        """set it up"""
        super().__init__()
        self.bot: Red = bot
        self.config = Config.get_conf(self, 4007)
        self.config.register_global(**self.default_global_settings)
        self.notify.start()

    async def cog_unload(self):
        self.notify.stop()

    @commands.Cog.listener("on_message_without_command")
    async def get_submarine_time(self, message: discord.Message):
        if message.embeds and (
            match := message.embeds[0].description
            and re.match(r"Returns \<t\:(\d+)\:R\>", message.embeds[0].description)
        ):
            channel = message.channel
            time = match.group(1)
            async with self.config.times_and_names() as conf:
                conf.append((time, message.embeds[0].title, channel.id))
            await channel.send(f"Reminding <t:{time}:R>")

    @tasks.loop(minutes=1)
    async def notify(self):
        log.debug("Checking for reminders.")
        async with self.config.times_and_names() as conf:
            if not conf:
                log.debug("no reminders")
            for reminder in conf:
                time, name, chan = reminder
                time = int(time)
                log.debug("reminder at %s", datetime.fromtimestamp(time).isoformat())
                if datetime.now().timestamp() > time:
                    channel = self.bot.get_channel(chan)
                    if not channel:
                        conf.remove(reminder)
                        continue
                    roles = channel.guild.roles if hasattr(channel, "guild") else []  # type: ignore
                    for r in roles:
                        if r.name == "Subs":
                            mention = r.mention
                            break
                    else:
                        mention = "@everyone"

                    await channel.send(
                        f"{mention} {name} has returned!",
                        allowed_mentions=discord.AllowedMentions(roles=True),
                    )
                    conf.remove(reminder)

    @commands.command()
    async def calculate_split(self, ctx: commands.Context, before: int, after: int):
        gain = after - before
        first = gain // 10
        even = (gain // 100) * 45
        await ctx.reply(
            f"""Maddo       : {first}
Jenno       : {even}
Put in chest: {first + even}""",
            mention_author=False,
        )
