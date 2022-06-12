from redbot.core import Config, checks, commands
import asyncio
import time
import yt_dlp
import subprocess
import os
import io
import discord
import re
import shutil

class Genericdl(commands.Cog):
    """generic youtube-dl downloader"""

    def __init__(self, bot):
        """set it up"""
        super().__init__()
        self.bot = bot
        self.web_folder_name = "/mnt/NAS/webshare/gimmemp3/"
        self.web_server_name = "https://owldyn.net/share/gimmemp3/"

    @commands.command()
    async def vidlink(self, ctx, url):
        """Downloads the linked video"""
        async with ctx.typing():
            if url[0] == '<':
                url = url[1:len(url)-1]

            fname = '/tmp/{}.webm'.format(ctx.message.id)

            if url.find(".") >= 0:
                try:
                    subprocess.run(['yt-dlp', url, '-o', fname, '--merge-output-format', 'webm'])
                    titleraw = subprocess.run(['yt-dlp', '--get-title', url], capture_output=True)
                    title = titleraw.stdout.decode("utf-8")[0:len(titleraw.stdout)-1]

                    fs = os.stat(fname).st_size
                    if fs < 8388119:
                        with io.open(fname, "rb") as stream:
                            await ctx.send(content="Title: {}".format(title), file=discord.File(stream, filename="{}.webm".format(title)))
                        os.remove(fname)
                    else:
                        await self.move_to_webserver(ctx, fname, '.webm')
                except Exception as e:
                    await ctx.send("Hoot! Error occured. Perhaps youtube-dl is broke with this website?")
                    await ctx.send(f'Error is: {str(e)}')
                    pass
                    
            else:
                await ctx.send("{} is not a valid link.".format(url))

    @commands.command() #TODO CHANGE THIS TO USE NATIVE YT-DLP
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
                    subprocess.run(['yt-dlp', url, '--extract-audio', '--audio-format', 'mp3', '--output', '{}\%(ext)s'.format(blandfname)])
                    titleraw = subprocess.run(['yt-dlp', '--get-title', url], capture_output=True)
                    title = titleraw.stdout.decode("utf-8")[0:len(titleraw.stdout)-1]

                    fs = os.stat(mp3fname).st_size
                    if fs < 8388119:
                        with io.open(mp3fname, "rb") as stream:
                            await ctx.send(content="Title: {}".format(title), file=discord.File(stream, filename="{}.mp3".format(title)))
                        os.remove(mp3fname)
                    else:
                        await self.move_to_webserver(ctx, mp3fname, '.mp3')
                except Exception as e:
                    await ctx.send("Hoot! Error occured. Perhaps youtube-dl is broke with this website?")
                    await ctx.send(f'Error is: {str(e)}') 
            else:
                await ctx.send("{} is not a valid link.".format(url))
    async def move_to_webserver(self, ctx, fname, ext):
        shutil.move(fname, f'{self.web_folder_name}{ctx.message.id}.{ext}')
        webfilename = f'{self.web_server_name}{ctx.message.id}.{ext}'
        await ctx.send(f'File too large for discord.\nFile uploaded to {webfilename}.') 

    async def calc_bitrate(self, duration, filesize, audio_size):
        """Returns the bitrate ( in kilobits ) for a given string containing the duration, and the given max filesize (in bytes)
        Duration string should contain the duration with "Duration: 00:00:00.00"
        Will lower bitrate by audio_size + 22 * 1024 to account for variation and audio."""
        audio_size = (int(audio_size) + 22) * 1024 # Round up a little to account for variation
        filesize = int(filesize) * 8
        bitrate = int((filesize / int(duration)) - audio_size)
        return int(bitrate / 1024)

    async def calc_bitrate2(self, file_string, filesize):
        """Returns the bitrate ( in kilobits ) for a given string containing the duration, and the given max filesize (in bytes)
        Duration string should contain the duration with "Duration: 00:00:00.00"
        Will lower bitrate by 150Kb to account for variation and audio."""
        audio_size = 150 * 1024 # Rounded up a little to account for variation
        raw_duration_regex = re.search(r'Duration: \d\d:\d\d:\d\d.\d\d', file_string)
        raw_duration_regex = re.search(r'\d\d:\d\d:\d\d', raw_duration_regex.group(0))
        duration_array = raw_duration_regex.group(0).split(":")
        duration = int(duration_array[0]) * 60 * 60
        duration += int(duration_array[1]) * 60
        duration += int(duration_array[2])
        filesize = filesize * 8
        bitrate = int((filesize / duration) - audio_size)
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