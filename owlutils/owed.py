
import logging
from datetime import datetime

import discord
from discord.ext import tasks
from redbot.core import Config, app_commands, commands
from redbot.core.bot import Red

OWED = list[list]
class Owed(commands.Cog):
    def __init__(self, bot: Red):
        self.bot = bot
        self.conf = Config.get_conf(self, identifier=4007)
        # List of tuples, ("lender", "lendee", float_amount, "descriptor")
        self.conf.register_global(**{"owed": []})
        self.log = logging.getLogger("owlutlis.Owed")
        self.am = discord.AllowedMentions(users=True)
        
        
    @app_commands.command()
    async def create_owe(self, ctx: discord.Interaction, member: discord.Member, amount: float, descriptor: str):
        async with self.conf.owed() as owed:
            if any(o[1] == member.id and o[3] == descriptor for o in owed):
                await ctx.response.send_message(f"{member.display_name} already owes you {descriptor}, use modify_owe to add to it!")
                return
            owed.append([ctx.user.id, member.id, amount, descriptor])
            await ctx.response.send_message(f"{member.mention}, {ctx.user.mention} says you owe them {amount} {descriptor}.", allowed_mentions=self.am)
    
    @app_commands.command()
    async def list_owes(self, ctx: discord.Interaction):
        owes = []
        async with self.conf.owed() as owed:
            for o in owed:
                if ctx.user.id in o[:2]:
                    owes.append(o)
                    
        rendered = []
        for o in owes:
            other_user = self.bot.get_user(o[0] if ctx.user.id != o[0] else o[1])
            if not other_user:
                continue
            rendered.append(f"You owe {other_user.mention} {o[2]} {o[3]}.")
        
        
        await ctx.response.send_message("\n".join(rendered) if rendered else "You don't have any!")
        
    @app_commands.command()
    async def modify_owe(self, ctx: discord.Interaction, member: discord.Member, descriptor: str, amount: float):
        owed: OWED
        async with self.conf.owed() as owed:
            owes = [o for o in owed if o[0] == ctx.user.id and o[1] == member.id and o[3] == descriptor]
            if not owes:
                await ctx.response.send_message("No matching owe found.", ephemeral=True)
            owe = owes[0]
            index = owed.index(owe)
            owe[2] += amount
            owed[index] = owe
        await ctx.response.send_message(f"{member.mention}, {ctx.user.mention} says you now owe them {owe[2]} {descriptor}.", allowed_mentions=self.am)
            
    @app_commands.command()
    async def delete_owe(self, ctx: discord.Interaction, member: discord.Member, descriptor: str):
        owed: OWED
        async with self.conf.owed() as owed:
            owe = next(o for o in owed if o[0] == ctx.user.id and o[1] == member.id and o[3] == descriptor)
            index = owed.index(owe)
            del owed[index]
        await ctx.response.send_message(f"{member.mention}, {ctx.user.mention} says you no longer owe them any {descriptor}.", allowed_mentions=self.am)
        

