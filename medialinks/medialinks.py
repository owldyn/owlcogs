import asyncio
import io
import os
import re
import subprocess
import time
from operator import sub
from typing import DefaultDict

import asyncpraw as praw
import discord
import requests as req
import youtube_dl
from asyncpraw import reddit
from redbot.core import Config, checks, commands

from . import processors


class MediaLinks(commands.Cog):
    """v.redd.it downloader"""
    default_global_settings = {"channels_ignored": [],
                               "guilds_ignored": [], "users_ignored": []}
    supported_processors = [processors.reddit.RedditProcessor]

    def __init__(self, bot):
        """set it up"""
        super().__init__()
        self.bot = bot
        self.reddit = praw.Reddit(
            "Hoobot", user_agent="discord:hoobot:1.0 (by u/owldyn)")
        self.conf = Config.get_conf(self, identifier=26400736)
        self.conf.register_global(**self.default_global_settings)

    @commands.command()
    async def testingvredditnew(self, ctx, url):
        """Downloads the vreddit video and links it to webserver if too large"""
        async with ctx.typing():
            with processors.reddit.RedditProcessor() as reddit:
                message_builder = await reddit.process_url(url, spoiler=True)
                message = message_builder.get('post')
                if isinstance(message, list):
                    for message in message:
                        await ctx.send(**message.send_kwargs)
                else:
                    await ctx.send(**message.send_kwargs)
    
    @commands.guild_only()
    @commands.group(name="ignoremedialink")
    async def automedialinkignore(self, ctx):
        """Change autoredditpost cog ignore settings."""

    @automedialinkignore.command(name="server")
    @checks.admin_or_permissions(manage_guild=True)
    async def _automedialinkignore_server(self, ctx):
        """Ignore/Unignore the current server"""

        guild = ctx.message.guild
        guilds = await self.conf.guilds_ignored()
        if guild.id in guilds:
            guilds.remove(guild.id)
            await ctx.send("I will no longer ignore this server.")
        else:
            guilds.append(guild.id)
            await ctx.send("I will ignore this server. Explicitly use !redditlink to use this feature.")
        await self.conf.guilds_ignored.set(guilds)

    @automedialinkignore.command(name="channel")
    @checks.admin_or_permissions(manage_guild=True)
    async def _automedialinkignore_channel(self, ctx):
        """Ignore/Unignore the current channel"""

        chan = ctx.message.channel
        chans = await self.conf.channels_ignored()
        if chan.id in chans:
            chans.remove(chan.id)
            await ctx.send("I will no longer ignore this channel.")
        else:
            chans.append(chan.id)
            await ctx.send("I will ignore this channel. Explicitly use !redditlink to use this feature.")
        await self.conf.channels_ignored.set(chans)

    @automedialinkignore.command(name="self")
    async def _automedialinkignore_user(self, ctx):
        """Ignore/Unignore the current user"""

        user = ctx.message.author
        users = await self.conf.users_ignored()
        if user.id in users:
            users.remove(user.id)
            await ctx.send("I will no longer ignore your links.")
        else:
            users.append(user.id)
            await ctx.send("I will ignore your links. Explicitly use !redditlink to use this feature.")
        await self.conf.users_ignored.set(users)

    @commands.Cog.listener("on_message_without_command")
    async def automedialink(self, message):
        """Checks each message sent in the server for a compatible link, then sends it"""
        checks = [
            bool(message.author.bot),
            bool(message.guild) and bool(message.guild.id in await self.conf.guilds_ignored()),
            bool(message.channel) and bool(message.channel.id in await self.conf.channels_ignored()),
            bool(message.author) and bool(message.author.id in await self.conf.users_ignored()),
        ]

        if True in checks:
            return
        msg_content = message.content.lower()
        if "http" in msg_content:
            ctx = await self.bot.get_context(message)
            for processor in self.supported_processors:
                for check in processor.regex_checks:
                    matches = check.findall(msg_content)
                    if matches:
                        spoiler = False
                        if 'as spoiler' in msg_content:
                            spoiler = True
                        matches = ["".join(list(match)) for match in matches] # findall returns the groups separated.
                        await self.process_link(processor, matches, ctx, spoiler)
                        break

    @commands.command()
    async def medialink(self, ctx, url, spoiler=False):
        for processor in self.supported_processors:
            for check in processor.regex_checks:
                matches = check.findall(url)
                if matches:
                    matches = ["".join(list(match)) for match in matches] # findall returns the groups separated.
                    return await self.process_link(processor, [url], ctx, spoiler)
        await ctx.send("Url did not match any recognized urls!")

    async def process_link(self, processor: processors.base.AbstractProcessor, matches: list, ctx, spoiler: bool = False):
        async with ctx.typing():
            for match in matches:
                with processor() as proc:
                    message_dict = await proc.process_url(match, spoiler=spoiler)
                    messages = message_dict.get('post')
                    comment = message_dict.get('comments', None)
                    messages_to_send = []
                    if isinstance(messages, list):
                        for message_builder in messages:
                            messages_to_send.append(message_builder)
                    else:
                        messages_to_send.append(messages)
                    if comment:
                        messages_to_send.append(comment)

                    sender = ctx.reply # only want to reply with one message
                    for index, message in enumerate(messages_to_send):
                        if index > 0:
                            sender = ctx.send
                        if spoiler and message.type == message.MessageTypes.IMAGE_EMBED:
                            if not message.image_url: # Can't do the hack here
                                await sender(**message.send_kwargs)
                            else:
                                spoiler_setup = await sender(f'||{message.image_url}||', mention_author=False)
                                await spoiler_setup.edit(**message.send_kwargs)
                        else:
                            file = None
                            if message.send_kwargs.get('file') and message.send_kwargs.get('embed'):
                                file = message.send_kwargs.pop('file')
                            await sender(**message.send_kwargs, mention_author=False)
                            if file:
                                await sender(file=file)
                    await ctx.message.edit(suppress=True)
