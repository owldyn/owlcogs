from redbot.core import Config, checks, commands
import asyncio
import time
import subprocess
import os
import io
import discord

class Genericdl(commands.Cog):
    """generic youtube-dl downloader"""

    def __init__(self, bot):
        """set it up"""
        super().__init__()
        self.bot = bot

        
    @commands.command()
    async def vidlink(self, ctx, url):
        """Downloads the linked video"""
        async with ctx.typing():
            if url[0] == '<':
                url = url[1:len(url)-1]

            fname = '/tmp/{}.mp4'.format(ctx.message.id)

            if url.find(".") >= 0:
                try:
                    subprocess.run(['youtube-dl', url, '-o', fname])
                    titleraw = subprocess.run(['youtube-dl', '--get-title', url], capture_output=True)
                    title = titleraw.stdout.decode("utf-8")[0:len(titleraw.stdout)-1]

                    fs = os.stat(fname).st_size
                    if fs < 8388119:
                        stream=io.open(fname, "rb")
                        await ctx.send(content="Title: {}".format(title), file=discord.File(stream, filename="{}.mp4".format(title)))
                        os.remove(fname)
                    else:
                        await ctx.send("File too large. Use link to watch.")
                except:
                    await ctx.send("Hoot! Error occured. Perhaps youtube-dl is broke with this website?")
                    pass
                    
            else:
                await ctx.send("{} is not a valid link.".format(url))

    @commands.command()
    async def gimmemp3(self, ctx, url):
        """Downloads the linked video"""
        async with ctx.typing():
            if url[0] == '<':
                url = url[1:len(url)-1]
            blandfname = '/tmp/{}.'.format(ctx.message.id)
            fname = '/tmp/{}.webm'.format(ctx.message.id)
            mp3fname = '/tmp/{}.mp3'.format(ctx.message.id)
            if url.find(".") >= 0:
                try:
                    subprocess.run(['youtube-dl', url, '--extract-audio', '--audio-format', 'mp3', '--output', '{}\%(ext)s'.format(blandfname)])
                    titleraw = subprocess.run(['youtube-dl', '--get-title', url], capture_output=True)
                    title = titleraw.stdout.decode("utf-8")[0:len(titleraw.stdout)-1]

                    fs = os.stat(mp3fname).st_size
                    if fs < 8388119:
                        stream=io.open(mp3fname, "rb")
                        await ctx.send(content="Title: {}".format(title), file=discord.File(stream, filename="{}.mp3".format(title)))
                        os.remove(mp3fname)
                    else:
                        await ctx.send("File too large.")
                except:
                    await ctx.send("Hoot! Error occured. Perhaps youtube-dl is broke with this website?")
                    pass
                    
            else:
                await ctx.send("{} is not a valid link.".format(url))
        

