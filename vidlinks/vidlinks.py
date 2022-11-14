from operator import sub
from typing import DefaultDict
from asyncpraw import reddit
from redbot.core import Config, checks, commands
import asyncio
import time
import subprocess
import os
import io
import discord
import re
import asyncpraw as praw
import requests as req
import youtube_dl
from . import processors

class VidLink(commands.Cog):
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
                file = reddit.process_url(url)
                await ctx.send(content="test!", file=discord.File(file, filename="test.mp4"))
