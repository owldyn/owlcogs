import asyncio
import logging
import re
from tempfile import NamedTemporaryFile

import discord
import requests
from discord.ext import tasks
from redbot.core import Config, app_commands, commands

from .calculate import Calculator
from .list import ListMixin
from .llm_response import LLMMixin

DISCORD_MAX_FILESIZE = 8388119


class OwlUtils(LLMMixin, ListMixin, commands.Cog):
    """Small utils I'm making for myself."""

    CHECK_MARK = "✅"
    default_global_settings = {
        "ai": {
            "enabled": True,
            "name": "Hoobot",
            "model": "ggml-gpt4all-j.bin",
            "url": "",
            "api_key": "",
            "system_message": None,
        },
        "list": {},
        "health_check": {},
    }

    def __init__(self, bot):
        self.bot: discord.Client = bot
        self.conf = Config.get_conf(self, identifier=26400736017)
        self.conf.register_global(**self.default_global_settings)
        self.ai_name = None
        self.ai_model = None
        self.ai_system_message = None
        self.log = logging.getLogger("OwlUtils")
        self.ctx_menu = app_commands.ContextMenu(
            name="Get Tenor Link", callback=self.tenor_context
        )
        self.bot.tree.add_command(self.ctx_menu)
        self.health_check.start()

    async def cog_unload(self):
        """unload"""
        self.health_check.cancel()

    @commands.Cog.listener("on_message_without_command")
    async def calculate(self, message):
        """Calculate math from a given message."""
        if message.author.bot:
            return
        msg_content = message.content.lower()
        split_message = msg_content.split(" ")
        if msg_content and re.match(r"what['s ]?", split_message[0]):
            try:
                ctx: commands.context.Context = await self.bot.get_context(message)
                if "what" in split_message[0] and "is" in split_message[1]:
                    calculate_string = " ".join(split_message[2:])
                else:
                    calculate_string = " ".join(split_message[1:])
                try:
                    total = await asyncio.wait_for(
                        asyncio.get_event_loop().run_in_executor(
                            None, Calculator().calculate, " ".join(calculate_string)
                        ),
                        5,
                    )
                except Exception:
                    await ctx.reply(
                        "I can't do that math :(", mention_author=False
                    )
                    return
                if total is not None:
                    await ctx.reply(total, mention_author=False)

            except IndexError:
                pass

    @commands.Cog.listener("on_message_without_command")
    async def get_file_name(self, message):
        """Returns the file names in the message if the files are videos
        Since discord feels like removing the file names from being visible :)"""
        if message.author.bot:
            return
        if not message.attachments:
            return
        file_names = []
        reply = None
        for file in message.attachments:
            if True in [
                file_ext in file.filename for file_ext in [".mp4", ".mkv", "webm"]
            ]:
                if "SPOILER_" in file.filename:
                    file_names.append(f"||{file.filename}||")
                else:
                    file_names.append(file.filename)
                newline = "\n"
                reply = f'{f"Files are named {newline}:" if len(file_names) > 1 else "File is named: "}{newline.join(file_names)}'
                ctx = await self.bot.get_context(message)
        if reply:
            await ctx.reply(reply, mention_author=False)

    async def get_users(self, ctx: discord.Interaction, current: str):
        """Gets users in the channel for completion"""
        self.log.debug(
            [
                member.mention
                for member in ctx.channel.members
                if current in member.display_name
            ]
        )
        return [
            app_commands.Choice(name=member.display_name, value=member.mention)
            for member in ctx.channel.members
            if not current or current in member.display_name
        ]

    @app_commands.command(
        name="script_all_links",
        description="Make a script to download all links in this channel",
    )
    @app_commands.autocomplete(user=get_users)
    async def script_all_links(self, ctx: discord.Interaction, user: str = None):
        """Grabs all link in the channel (optionally from specified user)."""
        if not ctx.channel:
            await ctx.response.send_message(
                "This can only be sent in a server channel.", ephemeral=True
            )
        await ctx.response.send_message(
            "Grabbing all messages. This will probably take a while.",
            ephemeral=True,
        )
        count = 0
        links = []
        message: discord.Message
        async for message in ctx.channel.history(limit=None):
            if user:
                if message.author.mention != user:
                    continue
            if matches := re.findall(r"https?://[^ ]*", message.content):
                links.extend(matches)
                count += 1
            if message.attachments:
                attachments = [a.proxy_url for a in message.attachments]
                links.extend(attachments)
                count += len(attachments)
        with NamedTemporaryFile("r+") as script:
            for link in links:
                script.write(f'curl "{link}" --remote-name\n')
            script.write("pause")
            script.seek(0)
            file = discord.File(fp=script.file, filename="download_links.bat")
            await ctx.followup.send(
                f"Found {count} messages with links, for a total of {len(links)} links.",
                ephemeral=True,
                file=file,
            )

    async def tenor_context(self, ctx: discord.Interaction, message: discord.Message):
        """Right click to get the gif link from tenor"""
        if "tenor.com" in message.content:
            await ctx.response.send_message(f"<{message.content}>", ephemeral=True)
        else:
            await ctx.response.send_message(
                "No tenor gifs found in that message.", ephemeral=True
            )

    @commands.command()
    async def tenor(self, ctx):
        """Search 3 previous messages for tenor links, and link them without embedding the gif
        you can also reply to a message for the tenor link instead"""
        urls = []
        if ctx.message.reference:
            message = await ctx.channel.fetch_message(ctx.message.reference.message_id)
            if message.content.find("tenor.com") >= 0:
                await ctx.send(f"<{message.content}>")
            else:
                await ctx.send("No tenor gifs found in that message")

        else:
            async for message in ctx.channel.history(limit=4):
                if message.content.find("tenor.com") >= 0:
                    urls.append(message.content)
            if not urls:
                await ctx.send("No tenor gifs found in last 3 messages")
            else:
                urls.reverse()
                for url in urls:
                    await ctx.send("<{}>".format(url))

    @commands.is_owner()
    @commands.command()
    async def send_message(self, ctx, channel_id: str, *, message: str):
        """Send a message in a channel as the bot!"""
        try:
            channel = self.bot.get_channel(int(channel_id))
            if isinstance(
                channel, discord.channel.TextChannel | discord.threads.Thread
            ):
                await channel.send(message)
                await ctx.send("Sent!")
                return
        except Exception:
            pass
        await ctx.send("Failed to send message! Make sure I'm in that channel id!")

    @tasks.loop(minutes=1)
    async def health_check(self):
        self.log.debug("Doing health check...")
        async with self.conf.health_check() as conf:
            health_check_url = conf.get("health_check_url")
        if health_check_url:
            self.log.debug("Sending health check to %s", health_check_url)
            if not (
                response := await asyncio.get_event_loop().run_in_executor(
                    None, requests.get, health_check_url
                )
            ).ok:
                self.log.warning("%s %s", response, response.content)
        else:
            self.log.info("Url not set for health check.")

    @commands.is_owner()
    @commands.command()
    async def set_health_check_url(self, ctx: commands.Context, url: str):
        if url == "empty":
            url = None

        async with self.conf.health_check() as conf:
            conf["health_check_url"] = url

        self.health_check.restart()
        await ctx.react_quietly(self.CHECK_MARK)
