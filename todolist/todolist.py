from redbot.core import Config, checks, commands
import asyncio
import time
import subprocess
import os
import io
import discord

class ToDoList(commands.Cog):
    """Todo List"""

    def __init__(self, bot):
        """set it up"""
        super().__init__()
        self.bot = bot

        
    @commands.command()
    async def create(self, ctx, url):
        """Creates a list"""
        

        

