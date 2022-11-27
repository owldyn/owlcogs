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

    def __init__(self, bot):
        """set it up"""
        super().__init__()
        self.bot = bot
        self.reddit = praw.Reddit(
            "Hoobot", user_agent="discord:hoobot:1.0 (by u/owldyn)")
        self.conf = Config.get_conf(self, identifier=26400735)
        self.conf.register_global(**self.default_global_settings)

    @commands.command()
    async def testingvredditnew(self, ctx, url):
        """Downloads the vreddit video and links it to webserver if too large"""
        async with ctx.typing():
            with processors.reddit.RedditProcessor() as reddit:
                message_builder = reddit.process_url(url).get('post')
                if isinstance(message_builder, list):
                    for message in message_builder:
                        await ctx.send(**message.send_kwargs)
                else:
                    await ctx.send(**message_builder.send_kwargs)
