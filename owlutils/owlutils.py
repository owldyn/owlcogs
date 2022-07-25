import discord
import requests
from redbot.core import Config, checks, commands


class OwlUtils(commands.Cog):

    """Small utils I'm making for myself."""

    def __init__(self, bot):
        self.bot = bot
    @commands.is_owner()
    @commands.command()
    async def portainer(self, ctx, hostname, port):
        """create portainer labels for traefik"""
        config = f"""```        networks:
          - proxy
        labels:
            - "traefik.enable=true"
            - "traefik.http.routers.{hostname}.entrypoints=http"
            - "traefik.http.routers.{hostname}.rule=Host(`{hostname}.local.owldyn.net`)"
            - "traefik.http.middlewares.{hostname}-https-redirect.redirectscheme.scheme=https"
            - "traefik.http.routers.{hostname}.middlewares={hostname}-https-redirect"
            - "traefik.http.routers.{hostname}-secure.entrypoints=https"
            - "traefik.http.routers.{hostname}-secure.rule=Host(`{hostname}.local.owldyn.net`)"
            - "traefik.http.routers.{hostname}-secure.tls=true"
            - "traefik.http.routers.{hostname}-secure.service={hostname}"
            - "traefik.http.services.{hostname}.loadbalancer.server.port={port}"
            - "traefik.docker.network=proxy"
```
```networks:
  proxy:
    external: true```
        """
        await ctx.send(config)
