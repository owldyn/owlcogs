import re
import discord

from redbot.core import checks, Config, commands


class Yw(commands.Cog):

    """Say you're welcome when thanked"""

    default_global_settings = {"channels_ignored": [], "guilds_ignored": []}

    def __init__(self, bot):
        self.bot = bot
        self.conf = Config.get_conf(self, identifier=25400735)
        self.conf.register_global(**self.default_global_settings)

    async def red_delete_data_for_user(self, **kwargs):
        """Nothing to delete."""
        return

    @commands.guild_only()
    @commands.group(name="ywignore")
    @checks.admin_or_permissions(manage_guild=True)
    async def ywignore(self, ctx):
        """Change yw cog ignore settings."""

    @ywignore.command(name="server")
    @checks.admin_or_permissions(manage_guild=True)
    async def _ywignore_server(self, ctx):
        """Ignore/Unignore the current server"""

        guild = ctx.message.guild
        guilds = await self.conf.guilds_ignored()
        if guild.id in guilds:
            guilds.remove(guild.id)
            await ctx.send("I will no longer ignore this server.")
        else:
            guilds.append(guild.id)
            await ctx.send("I will ignore this server.")
        await self.conf.guilds_ignored.set(guilds)

    @ywignore.command(name="channel")
    @checks.admin_or_permissions(manage_guild=True)
    async def _ywignore_channel(self, ctx):
        """Ignore/Unignore the current channel"""

        chan = ctx.message.channel
        chans = await self.conf.channels_ignored()
        if chan.id in chans:
            chans.remove(chan.id)
            await ctx.send("I will no longer ignore this channel.")
        else:
            chans.append(chan.id)
            await ctx.send("I will ignore this channel.")
        await self.conf.channels_ignored.set(chans)

    @commands.Cog.listener("on_message_without_command")
    async def yw(self, message):
        if message.author.bot:
            return
        if message.guild.id in await self.conf.guilds_ignored():
            return
        if message.channel.id in await self.conf.channels_ignored():
            return
        msg_content = message.content.lower()
        msg_content.replace("!","")
        PATTERN_THANK = re.compile(r"thank[s]?[ ]?[y]?[o]?[u]?", re.IGNORECASE)
        if ("hoobot" in msg_content and
            PATTERN_THANK.match(msg_content) and
            len(msg_content) <= 23):
            msg = "You're welcome!"
            await message.channel.send(msg, allowed_mentions=discord.AllowedMentions(users=False))
