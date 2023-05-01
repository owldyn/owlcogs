import io
import os
import re
import subprocess

import discord
import requests as req
import youtube_dl
from redbot.core import commands


class twitter_DL(commands.Cog):
    MAX_FS = 8388119

    def __init__(self, bot):
        """set it up"""
        super().__init__()
        self.bot = bot


    def get_tweet_id(self, url):
        """Returns a twitter post's ID from the url"""
        if url[len(url)-1] != '/':
            url = url + '/'
        return re.search(r'(http.?:\/\/.?.?.?.?twitter.com\/[^\/]*?\/[^\/]*\/)([0-9]*)(.*)', url).group(2)

    def convert_from_tco(self, url):
        return req.get(url).url

    @commands.command(aliases=["twitterlink"])
    async def twittervid(self, ctx, url, force_gif = "no", audio = "yes"):
        """Downloads and sends a twitter video, will shrink if necessary"""
        async with ctx.typing():
            if url == '^':
                if ctx.message.reference:
                    message = await ctx.channel.fetch_message(ctx.message.reference.message_id)
                    args = message.content.split(' ')
                    await self.twittervid(ctx, *args)
                    return
                async for message in ctx.channel.history(limit=5):
                    if "https://t.co" in message.content or 'twitter.com' in message.content:
                        if '!twittervid' not in message.content:
                            args = message.content.split(' ')
                            await self.twittervid(ctx, *args)
                return
            if("https://t.co" in url):
                url = self.convert_from_tco(url)
            if("twitter.com" not in url):
                await ctx.send("URL is not a valid twitter URL")
                return

            ydl_opts = {
                'format':'best',
                'outtmpl': f'/tmp/{ctx.message.id}.%(ext)s'
            }
            try:
                with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                    dl = ydl.extract_info(url, download=True)
                    filename = ydl.prepare_filename(dl)
            except youtube_dl.DownloadError:
                await ctx.send("Twitter link did not have a video, or youtubedl is broken.")
                return

            if dl['duration'] is None:
                duration = await self.get_duration(filename)
            else:
                duration = dl['duration']

            if (force_gif == "yes") or (duration < 5):
                await self.make_and_send_gif(ctx, filename)
            else:
                await self.check_audio_and_send(ctx, filename, audio)


    async def check_audio_and_send(self, ctx, filename, audio):
        tmpfname = f'{filename}_tmp.mp4'
        if audio == "yes":
            audiocheckraw = subprocess.run(['ffmpeg', '-hide_banner', '-i', filename, '-af', 'volumedetect', '-vn', '-f', 'null', '-', '2>&1'], capture_output=True)
            audiocheck = audiocheckraw.stderr.decode("utf-8")[0:len(audiocheckraw.stderr)-1]
            if "does not contain any stream" in audiocheck and "mean_volume:" not in audiocheck:
                await self.ffmpeg(['ffmpeg', '-i', tmpfname, '-f', 'lavfi', '-i',
                                   'anullsrc=channel_layout=stereo:sample_rate=44100', 
                                   '-c:v', 'copy', '-c:a', 'aac', '-map', '0:v', '-map', 
                                   '1:a', '-shortest', filename], filename, tmpfname)
        else:
            await self.ffmpeg(['ffmpeg', '-i', tmpfname, '-f', 'lavfi', '-i', 
                               'anullsrc=channel_layout=stereo:sample_rate=44100',
                               '-c:v', 'copy', '-c:a', 'aac', '-map', '0:v', '-map',
                               '1:a', '-shortest', filename], filename, tmpfname)
        fs = await self.file_size(filename)
        if fs < self.MAX_FS:
            with io.open(filename, "rb") as stream:
                await ctx.send(file=discord.File(stream, filename=filename))
            os.remove(filename)
        else:
            shrink: discord.Message = await ctx.send("File is more than 8mb... attempting to shrink.")
            await self.ffmpeg(['ffmpeg', '-i', tmpfname, '-crf', '24', '-vf', 'scale=ceil(iw/4)*2:ceil(ih/4)*2', '-c:a', 'copy', filename], filename, tmpfname)
            fs = await self.file_size(filename)
            if fs < self.MAX_FS:
                with io.open(filename, "rb") as stream:
                    await ctx.send(file=discord.File(stream, filename=filename))
                os.remove(filename)
                await shrink.delete()
            else:
                await shrink.edit(content="File is still bigger than 8mb.. attempting extra shrinkage. (quality may be very bad on long videos)")
                bitrate = await self.calc_bitrate(audiocheck, self.MAX_FS)
                if bitrate < 0:
                    await ctx.send(content="Video was too long, could not shrink enough.")
                    os.remove(filename)
                    await shrink.delete()
                else:
                    await self.ffmpeg(['ffmpeg', '-y', '-i', tmpfname, '-b:v',  f'{bitrate}k', '-maxrate', f'{bitrate}k', '-b:a', '128k', filename],filename,tmpfname)
                    with io.open(filename, "rb") as stream:
                        await ctx.send(content=f'(Hoobot note: Quality may be (very) bad. click link if needed)', file=discord.File(stream, filename=filename))
                    os.remove(filename)
                    await shrink.delete()
    
    async def make_and_send_gif(self, ctx, mp4_filename, i=0):
        tmpfname = f'{mp4_filename}_tmp.mp4'
        filename = f'{mp4_filename}.gif'
        subprocess.run(['ffmpeg', '-i', mp4_filename, '-filter_complex',
                        "[0:v] split [a][b];[b]fifo[bb];[a] palettegen [p];[bb][p] paletteuse", filename])
        fs = await self.file_size(filename)
        if fs < self.MAX_FS:
            if i == 0:
                message = 'Hoobot note: File was converted to gif, quality may be bad'
            elif i == 1:
                message = f'Hoobot note: File was converted to gif, and shrunk {i} time, quality may be bad'
            else: 
                message = f'Hoobot note: File was converted to gif, and shrunk {i} times, quality may be bad'
            with io.open(filename, "rb") as stream:
                await ctx.send(content=message, file=discord.File(stream, filename=filename))
            os.remove(filename)
            os.remove(mp4_filename)
        else:
            await self.ffmpeg(['ffmpeg', '-i', tmpfname, '-crf', '24', '-vf', 'scale=ceil(iw/4)*2:ceil(ih/4)*2', '-c:a', 'copy', mp4_filename], mp4_filename, tmpfname)
            os.remove(filename)
            await self.make_and_send_gif(ctx, mp4_filename, i=i+1)

    async def get_duration(self, filename):
        result = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', filename], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        return float(result.stdout)
    
    async def ffmpeg(self, args, filename, tmpfname):
        os.rename(filename, tmpfname)
        subprocess.run(args)
        os.remove(tmpfname)

    async def file_size(self, fname):
        """check filesize"""
        statinfo = os.stat(fname)
        return statinfo.st_size

    async def calc_bitrate(self, file_string, filesize):
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
