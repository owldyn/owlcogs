"""

This is supposed to be better than discord's default search system.

I guess we'll see.

"""
import json
from redbot.core import Config, commands
#import re
import requests
import discord
class MessageIndex(commands.Cog):
    """

    Saves discord messages, indexes them. Allows you to search them.

    """
    default_global_settings = {
        "guilds": []
    }
    LEFT = ":arrow_left:"
    RIGHT = ":arrow_right:"
    def __init__(self, bot):
        """set it up"""
        super().__init__()
        self.bot = bot
        self.config = Config.get_conf(self, 4007355432)
        self.config.register_global(**self.default_global_settings)

    @commands.group()
    async def messageindex(self, ctx):
        """General base command."""

    @commands.is_owner()
    @messageindex.command()
    async def reset(self, ctx):
        """Will erase all guilds in the storage"""
        async with self.config.guilds() as guilds:
            del guilds[:]
            await ctx.send(f"reset! {guilds}")

    @commands.admin()
    @messageindex.command()
    async def initguild(self, ctx):
        """Initializes the guild. Makes it where it only works if you want it in that server."""
        async with self.config.guilds() as guilds:
            if ctx.guild.id not in guilds:
                guilds.append(ctx.guild.id)
                await ctx.send(guilds)
            else:
                await ctx.send(f'Guild {ctx.guild.id} already initialized!')
    
    @commands.admin()
    @messageindex.command()
    async def removeguild(self, ctx):
        """Initializes the guild. Makes it where it only works if you want it in that server."""
        async with self.config.guilds() as guilds:
            if ctx.guild.id in guilds:
                guilds.remove(ctx.guild.id)
                await ctx.send(guilds)
            else:
                await ctx.send(f'Guild {ctx.guild.id} isn\'t already initialized!')


    @commands.is_owner()
    @messageindex.command()
    async def search(self, ctx, *, search): #TODO https://stackoverflow.com/questions/65082883/discord-py-detecting-reactions
        """Searches messages, for now only returns the first one."""
        search_terms = "".join(search)
        request = requests.get(f'http://192.168.1.102:9000/api/search/{search_terms}')
        if len(request.json()) < 1:
            await ctx.send("No result.")
        else:
            message = request.json()[0]
            link_to_message = f"https://discord.com/channels/{message['guild_id']}/{message['channel_id']}/{message['message_id']}"
            embed_description = f'[Message by <@!{message["user_id"]}>]({link_to_message})\n{message["message_content"]}'
            embed = discord.Embed(description=embed_description)
            try:
                await ctx.send(embed=embed)
            except:
                return

    @commands.admin()
    @messageindex.command()
    async def grab_last_100(self, ctx):
        """Grabs the last 100 messages. Used for testing."""
        async for message in ctx.channel.history(limit=100):
            message_info = self._create_message(message)
            requests.post('http://192.168.1.102:9000/api/addmessage/',data=json.dumps(message_info))

    @commands.admin()
    @messageindex.command()
    async def grab_all_from_channel(self, ctx):
        """Grabs all the messages in this channel. Used for testing."""
        await ctx.send('Grabbing all messages. THIS WILL PROBABLY TAKE A WHILE.')
        async with ctx.typing():
            count = 0
            async for message in ctx.channel.history(limit=None):
                message_info = self._create_message(message)
                requests.post('http://192.168.1.102:9000/api/addmessage/',
                               data=json.dumps(message_info))
                count += 1
            await ctx.send(f'Processed {count} messages.')

    @staticmethod
    def _create_message(message: commands.context.Context):
        message_info = {}
        message_info['guild_id'] = message.guild.id
        message_info['user_id'] = message.author.id
        message_info['channel_id'] = message.channel.id
        message_info['message_id'] = message.id
        message_info['message_content'] = message.content
        message_info['time_sent'] = str(message.created_at)
        message_info['author_name'] = message.author.name
        if len(message.attachments) != 0:
            message_info['image_link'] = message.attachments[0].url
        else:
            message_info['image_link'] = ""
        return message_info
