import re

import requests
from redbot.core import Config, checks, commands
from .calculate import Calculator

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
        - "traefik.http.routers.{hostname}.rule=Host(`{hostname}.local.owldyn.net`)"
        - "traefik.http.middlewares.{hostname}-https-redirect.redirectscheme.scheme=https"
        - "traefik.http.routers.{hostname}.middlewares={hostname}-https-redirect"
        - "traefik.http.routers.{hostname}-secure.entrypoints=https"
        - "traefik.http.routers.{hostname}-secure.rule=Host(`{hostname}.local.owldyn.net`)"
        - "traefik.http.routers.{hostname}-secure.tls=true"
        - "traefik.http.routers.{hostname}-secure.service={hostname}"
        - "traefik.http.services.{hostname}.loadbalancer.server.port={port}"
        - "traefik.http.routers.{hostname}-secure.middlewares=secured@file"
        - "traefik.docker.network=proxy"
        #- "traefik.http.routers.{hostname}-secure.middlewares=authelia@docker" # Uncomment for authelia
        # Remove below for local only
        - "traefik.http.routers.{hostname}-external.entrypoints=http"
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

    @commands.Cog.listener("on_message_without_command")
    async def calculate(self, message):
        if message.author.bot:
            return
        msg_content = message.content.lower()
        split_message = msg_content.split(' ')
        if (re.match(r"what['s ]?(s|is)", split_message[0])
            and split_message[1].isdigit()
            and msg_content):
            ctx = await self.bot.get_context(message)
            total = Calculator().calculate(' '.join(split_message[1:]))
            if total is not None:
                await ctx.send(total)
