from redbot.core import Config, checks, commands
import asyncio
import time
import subprocess
import os
import io
import discord
import re

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
        """Downloads the linked audio"""
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
    
    async def calc_bitrate(self, duration, filesize, audio_size):
        audio_size = (int(audio_size) + 32) * 1024 # Round up a little to account for variation
        filesize = int(filesize) * 8
        bitrate = int((filesize / int(duration)) - audio_size)
        return int(bitrate / 1024)

    @commands.command()
    async def clipbitrate(self, ctx, length, filesize="8M", audiobitrate="128k"):
        """Calculates the VIDEO bitrate to use for a clip uploaded to discord. Enter duration in seconds, may change max filesize and audio bitrate optionally.
        Usage: !clipbitrate <duration in seconds> <max filesize {8MB, 50MB, or 100MB}> <audiobitrate>"""
        if "k" in audiobitrate:
            audiobitrate = audiobitrate.replace("k","")
        fallbacksize = False
        if (filesize.lower() == "8m" or filesize.lower() == "8mb" or filesize == 8):
            filesize = 8388119
        elif (filesize.lower() == "50m" or filesize.lower() == "50mb" or filesize==50):
            filesize = 52428311
        elif (filesize.lower() == "100m" or filesize.lower() == "100mb" or filesize == 100):
            filesize = 104808700
        else:
            filesize = 8388119
            fallbacksize = True
        bitrate = await self.calc_bitrate(length, filesize, audiobitrate)
        message = f'Bitrate: {bitrate}k'
        if fallbacksize == True:
            message = message + "\nHoobot note: Did not understand filesize string, defaulting to 8MB."
        await ctx.send(content=message)

            
