from redbot.core import Config, checks, commands
import asyncio
import time
import subprocess
import os
import io
import discord

class ToDoList(commands.Cog):
    """Todo List"""
    #default_global_settings = {
    #    "lists": {
    #        "USERIDHERE": {
    #            "LISTNAMEHERE": {
    #                "listoptionhere": "y/n"
    #                
    #            }
    #        }
    #    }
    #}
    default_global_settings = {
        "lists": {}
    }
    def __init__(self, bot):
        """set it up"""
        super().__init__()
        self.bot = bot
        self.config = Config.get_conf(self, 8996998)
        self.config.register_global(**self.default_global_settings)                
            
    @commands.group()
    async def todolist(self, ctx):
        """General list command. Used to check off, delete, and append to lists. """

    @todolist.command(aliases=["createlist"])
    async def create(self, ctx, *, list_name: str):
        """Creates a list. Usage: [p]todolist create My List"""
        author = ctx.message.author
        async with self.config.lists() as listss:
            try:
                tmp = listss[f'{author.id}']
                await ctx.send(f'a')
            except:
                listss[f'{author.id}'] = {}
                await ctx.send('Looks like you\'re a new user! Adding your ID to the list.')
            
            try:
                tmp = listss[f'{author.id}'][list_name]
                await ctx.send(f'You already have a list named {list_name}!')
            except:
                listss[f'{author.id}'][list_name] = {}
                await ctx.send(f'Created list {list_name}!')
               

