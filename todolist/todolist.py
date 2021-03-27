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
    CHECK_MARK = "✅"
    X_MARK = "❌"
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
        """General list command."""

    async def check_exists(self, authid, list_name):
        async with self.config.lists() as listss:
            try:
                tmp = listss[str(authid)][str(list_name)]
                return True
            except:
                return False

    @todolist.command(aliases=["createlist"])
    async def create(self, ctx, list_name: str):
        """Creates a list. List name must be one word."""
        author = ctx.message.author
        async with self.config.lists() as listss:
            try:
                tmp = listss[str(author.id)]
            except:
                listss[str(author.id)] = {}
                await ctx.send('Looks like you\'re a new user! Adding your ID to the list.')
            
            try:
                tmp = listss[str(author.id)][list_name]
                await ctx.send(f'You already have a list named {list_name}!')
            except:
                listss[str(author.id)][list_name] = {}
                #await ctx.send(f'Created list {list_name}!')
                await ctx.message.add_reaction(self.CHECK_MARK)
               
    @todolist.command()
    async def list(self, ctx):
        """Prints out all of your lists"""
        author = ctx.message.author
        lists = ""
        async with self.config.lists() as listss:
            try:
                for key, value in listss[str(author.id)].items():
                    lists = lists + '\n' + key
                e = discord.Embed(title = author.name, description = lists)
                await ctx.send(embed=e)
            except:
                await ctx.send(f'Error. Do you have any lists?')

    @todolist.command()
    async def additem(self, ctx, list_name: str, *, item_name: str):
        """Adds an item to a list"""
        author = ctx.message.author
        if (await self.check_exists(author.id, list_name)):
            async with self.config.lists() as listss:
                listss[str(author.id)][list_name][item_name] = False
            #await ctx.send(f'Created item {item_name} in list {list_name}.')
            await ctx.message.add_reaction(self.CHECK_MARK)
        else:
            await ctx.send(f'List {list_name} doesn\'t exist!')

    async def _create_list_embed(self, ctx, list_name, listss):
        author = ctx.message.author
        lists = ""
        for key, value in listss[str(author.id)][list_name].items():
            lists = lists + '\n'
            if value is False:
                lists = lists + self.X_MARK
            else:
                lists = lists + self.CHECK_MARK
            lists = lists + " " + key
        return discord.Embed(title = list_name, description = lists)
        

    @todolist.command()
    async def listitems(self, ctx, list_name: str):
        """Prints out all of the items in one of your lists"""
        author = ctx.message.author
        lists = ""
        async with self.config.lists() as listss:
            try:
                e = await self._create_list_embed(ctx, list_name, listss)
                await ctx.send(embed=e)
            except:
                await ctx.send(f'Error. Does that list have any items?')  

    @todolist.command()
    async def checkitem(self, ctx, list_name, *, item_name):
        """Checks off an item in a list"""
        author = ctx.message.author
        async with self.config.lists() as listss:
            if self.check_exists(author.id, list_name):
                try:
                    tmp = listss[str(author.id)][list_name][item_name]
                    listss[str(author.id)][list_name][item_name] = True
                except:
                    await ctx.send("Error. Check that you spelled the item correctly.")
                try:
                    e = await self._create_list_embed(ctx, list_name, listss)
                    await ctx.send(embed=e)
                except:
                    await ctx.send(f'Error. Does that list have any items?')  
            else:
                await ctx.send(f'Error. Does that list exist?')
                
    @todolist.command()
    async def uncheckitem(self, ctx, list_name, *, item_name):
        """Unchecks an item in a list"""
        author = ctx.message.author
        async with self.config.lists() as listss:
            if self.check_exists(author.id, list_name):
                try:
                    tmp = listss[str(author.id)][list_name][item_name]
                    listss[str(author.id)][list_name][item_name] = False
                except:
                    await ctx.send("Error. Check that you spelled the item correctly.")
                try:
                    e = await self._create_list_embed(ctx, list_name, listss)
                    await ctx.send(embed=e)
                except:
                    await ctx.send(f'Error. Does that list have any items?')  
            else:
                await ctx.send(f'Error. Does that list exist?')
    
    @todolist.command(aliases=["removeitem"])
    async def deleteitem(self, ctx, list_name, *, item_name):
        """Deletes an item from a list. Removeitem also works."""
        author = ctx.message.author
        async with self.config.lists() as listss:
            if self.check_exists(author.id, list_name):
                try:
                    tmp = listss[str(author.id)][list_name][item_name]
                    del(listss[str(author.id)][list_name][item_name])
                except:
                    await ctx.send("Error. Check that you spelled the item correctly.")
                try:
                    e = await self._create_list_embed(ctx, list_name, listss)
                    await ctx.send(embed=e)
                except:
                    await ctx.send(f'Error. Does that list have any items?')
            else:
                await ctx.send(f'Error. Does that list exist?')
    
    @todolist.command()
    async def massadd(self, ctx, list_name, *, item_name):
        """Adds many items to a list. Use | between items, 'item1 | item2'"""
        item_split = item_name.split('|')
        author = ctx.message.author
        if (await self.check_exists(author.id, list_name)):
            async with self.config.lists() as listss:
                for item in item_split:
                    listss[str(author.id)][list_name][item.strip()] = False
            await ctx.message.add_reaction(self.CHECK_MARK)
        else:
            await ctx.send(f'List {list_name} doesn\'t exist!')

    @todolist.command(aliases=["removelist"])
    async def deletelist(self, ctx, list_name):
        """Deletes  a list. removelist also works."""
        author = ctx.message.author
        async with self.config.lists() as listss:
            if self.check_exists(author.id, list_name):
                try:
                    del(listss[str(author.id)][list_name])
                    await ctx.message.add_reaction(self.CHECK_MARK)
                except:
                    await ctx.send("Error. Check that you spelled the list correctly.")
            else:
                await ctx.send(f'Error. Does that list exist?')
