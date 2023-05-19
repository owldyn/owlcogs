import re
from tempfile import NamedTemporaryFile

import discord
from redbot.core import commands
from redbot.core.commands import Context

from .calculate import Calculator

DISCORD_MAX_FILESIZE = 8388119


class OwlUtils(commands.Cog):

    """Small utils I'm making for myself."""

    def __init__(self, bot):
        self.bot = bot

    @commands.is_owner()
    @commands.command()
    async def portainer(self, ctx, hostname, port):
        """create portainer labels for traefik"""
        config = f"""```      networks:
      - proxy
      - default
    labels:
        - "traefik.enable=true"
        # Remove below for external only
        - "traefik.http.routers.{hostname}.entrypoints=http"
        - "traefik.http.routers.{hostname}.service={hostname}"
        - "traefik.http.routers.{hostname}.rule=Host(`{hostname}.local.owldyn.net`)"
        - "traefik.http.middlewares.{hostname}-https-redirect.redirectscheme.scheme=https"
        - "traefik.http.routers.{hostname}.middlewares={hostname}-https-redirect"
        - "traefik.http.routers.{hostname}-secure.entrypoints=https"
        - "traefik.http.routers.{hostname}-secure.rule=Host(`{hostname}.local.owldyn.net`)"
        - "traefik.http.routers.{hostname}-secure.tls=true"
        - "traefik.http.routers.{hostname}-secure.service={hostname}"
        - "traefik.http.services.{hostname}.loadbalancer.server.port={port}"
        - "traefik.http.routers.{hostname}-secure.middlewares=secured@file" #, authelia@docker" # Uncomment for authelia"
        - "traefik.docker.network=proxy"
        ```"""
        config2 = f"""```
        # Remove below for local only
        - "traefik.http.routers.{hostname}-external.entrypoints=http"
        - "traefik.http.routers.{hostname}-external.service={hostname}-external"
        - "traefik.http.routers.{hostname}-external.rule=Host(`{hostname}.owldyn.net`)"
        - "traefik.http.middlewares.{hostname}-external-https-redirect.redirectscheme.scheme=https"
        - "traefik.http.routers.{hostname}-external.middlewares={hostname}-https-redirect"
        - "traefik.http.routers.{hostname}-external-secure.entrypoints=https"
        - "traefik.http.routers.{hostname}-external-secure.rule=Host(`{hostname}.owldyn.net`)"
        - "traefik.http.routers.{hostname}-external-secure.tls=true"
        - "traefik.http.routers.{hostname}-external-secure.service={hostname}-external"
        - "traefik.http.services.{hostname}-external.loadbalancer.server.port={port}"
        #- "traefik.http.routers.{hostname}-external-secure.middlewares=authelia@docker" # Uncomment for authelia
```
```networks:
  proxy:
    external: true```
        """
        await ctx.send(config)
        await ctx.send(config2)

    @commands.Cog.listener("on_message_without_command")
    async def calculate(self, message):
        if message.author.bot:
            return
        msg_content = message.content.lower()
        split_message = msg_content.split(" ")
        if msg_content and re.match(r"what['s ]?", split_message[0]):
            try:
                ctx = await self.bot.get_context(message)
                if "what" in split_message[0] and "is" in split_message[1]:
                    calculate_string = " ".join(split_message[2:])
                else:
                    calculate_string = " ".join(split_message[1:])
                total = Calculator().calculate(" ".join(calculate_string))
                if total is not None:
                    await ctx.send(total)
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

    @commands.command()
    async def script_all_links(self, ctx: Context, user=None):
        """Grabs all link in the channel (optionally from specified user)."""
        if not ctx.channel:
            await ctx.reply(
                "This can only be sent in a server channel.", mention_author=False
            )
        edit: discord.Message = await ctx.reply(
            "Grabbing all messages. This will probably take a while.",
            mention_author=False,
        )
        async with ctx.typing():
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
            with NamedTemporaryFile("r+") as script:
                for link in links:
                    script.write(f'curl "{link}" --remote-name\n')
                script.write('pause')
                script.seek(0)
                file = discord.File(fp=script.file, filename="download_links.bat")
                await edit.delete()
                await ctx.reply(
                    f"Found {count} messages with links, for a total of {len(links)} links.",
                    mention_author=False,
                    file=file,
                )

    @commands.command()
    async def tenor(self, ctx):
        """Search 3 previous messages for tenor links, and link them without embedding the gif
        you can also reply to a message for the tenor link instead"""
        urls = []
        if ctx.message.reference:
            message = await ctx.channel.fetch_message(ctx.message.reference.message_id)
            if message.content.find("tenor.com") >= 0:
                await ctx.send(f"<{message.content}")
            else:
                await ctx.send("No tenor gifs found in that message")

        else:
            async for message in messages:
                if message.content.find("tenor.com") >= 0:
                    urls.append(message.content)
            if not urls:
                await ctx.send("No tenor gifs found in last 3 messages")
            else:
                urls.reverse()
                for url in urls:
                    await ctx.send("<{}>".format(url))
