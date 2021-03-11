from redbot.core import Config, checks, commands
import asyncio
import time
import subprocess
import os

class EVGACheck(commands.Cog):
    """My custom cog"""

    default_global_settings = {
        "urls": []
    }

    def __init__(self, bot):
        """set it up"""
        super().__init__()
        self.bot = bot
        self.config = Config.get_conf(self, 89996997)
        self.config.register_global(**self.default_global_settings)
        self.task = self.bot.loop.create_task(self.loop())
        self.time = 60

    @commands.command()
    async def evgacheckstart(self, ctx, url):
        """Starts the watch for given url"""
        author = ctx.message.author
        await ctx.send('Starting watch on ' + url + ' for user ' + str(author.id))
        urlwithauthor = {
            "ID": author.id,
            "URL": url
        }
        async with self.config.urls() as urlss:
            urlss.append(urlwithauthor)

    def cog_unload(self):
        """Clean up when cog shuts down."""
        if self.task:
            self.task.cancel()

    @commands.command()
    async def evgacheckremoveall(self, ctx):
        """Cancels all watches for you"""
        for url in await self.config.urls():
            async with self.config.urls() as urlss:
                author = ctx.message.author.id # self.bot.get_user(url["ID"])
                if author is not None:
                    if url["ID"] == author:
                        urlss.remove(url)
                        await ctx.send("Removed " + url["URL"])
        await ctx.send("removed all urls for you")

    @commands.command()
    async def listURLs(self, ctx):
        """lists all urls"""
        has = False
        for url in await self.config.urls():
            has = True
            await ctx.send(url)
        if not has:
            await ctx.send("No URLs")


    async def loop(self):
        while self.bot.get_cog("EVGACheck") == self:
            for url in await self.config.urls():
                ins = False
                page = url["URL"]
                subprocess.run(['wget', '-O', '/tmp/tmp.aspx', page])
                with open('/tmp/tmp.aspx') as file:
                    filetext = file.readlines()
                for line in filetext:
                    if "ADD TO CART" in line:
                        ins = True
                if ins:
                    author = self.bot.get_user(url["ID"])
                    if author is not None:
                        await author.send("{} has add to cart on the page!".format(url["URL"]))
                os.remove("/tmp/tmp.aspx")
            await asyncio.sleep(self.time)