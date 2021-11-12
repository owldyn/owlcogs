# pylint: disable=subprocess-run-check
from operator import sub
from typing import DefaultDict
from redbot.core import Config, checks, commands
import asyncio
import time
import subprocess
import os
import io
import discord
import re
import asyncpraw as praw
import requests as req
import youtube_dl

class VRedditDL(commands.Cog):
    """v.redd.it downloader"""
    default_global_settings = {"channels_ignored": [], "guilds_ignored": [], "users_ignored": []}
    def __init__(self, bot):
        """set it up"""
        super().__init__()
        self.bot = bot
        self.reddit = praw.Reddit("Hoobot", user_agent="discord:hoobot:1.0 (by u/owldyn)")
        self.conf = Config.get_conf(self, identifier=26400735)
        self.conf.register_global(**self.default_global_settings)

    async def file_size(self, fname):
        """check filesize"""
        statinfo = os.stat(fname)
        return statinfo.st_size    
    async def ydl_download(self, filename, url):
        ydl_opts = {
            'outtmpl': filename
        }
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            dl = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(dl)
        return filename

    async def download_and_check_audio(self, ctx, audio, fname, tmpfname, url):
        if audio == "yes":
            await self.ydl_download(fname, url)
            audiocheckraw = subprocess.run(['ffmpeg', '-hide_banner', '-i', fname, '-af', 'volumedetect', '-vn', '-f', 'null', '-', '2>&1'], capture_output=True)
            audiocheck = audiocheckraw.stderr.decode("utf-8")[0:len(audiocheckraw.stderr)-1]
            if "does not contain any stream" in audiocheck and "mean_volume:" not in audiocheck:
                os.rename(fname, tmpfname)
                subprocess.run(['ffmpeg', '-i', tmpfname, '-f', 'lavfi', '-i', 'anullsrc=channel_layout=stereo:sample_rate=44100', '-c:v', 'copy', '-c:a', 'aac', '-map', '0:v', '-map', '1:a', '-shortest', fname])
                os.remove(tmpfname)
        else:
            await self.ydl_download(tmpfname, url)
            subprocess.run(['ffmpeg', '-i', tmpfname, '-f', 'lavfi', '-i', 'anullsrc=channel_layout=stereo:sample_rate=44100', '-c:v', 'copy', '-c:a', 'aac', '-map', '0:v', '-map', '1:a', '-shortest', fname])
            os.remove(tmpfname)

    async def download_and_send(self, ctx, title, audio, url):
        MAX_FS = 8388119
        if title is None or title == "UNSET":
            titlestring = ""
        else:
            titlestring = f'Title: {title}'
        tmpfname = f'/tmp/tmp{ctx.message.id}.mp4'
        fname = '/tmp/{}.mp4'.format(ctx.message.id)
        fname2 = '/tmp/{}2.mp4'.format(ctx.message.id)
        fname3 = '/tmp/{}3.mp4'.format(ctx.message.id)
        await self.download_and_check_audio(ctx, audio, fname, tmpfname, url)
        fs = await self.file_size(fname)
        if fs < MAX_FS:
            with io.open(fname, "rb") as stream:
                await ctx.send(content=titlestring, file=discord.File(stream, filename="{}.mp4".format(title)))
            os.remove(fname)
        else:
            shrink: discord.Message = await ctx.send("File is more than 8mb... attempting to shrink.")
            subprocess.run(['ffmpeg', '-i', fname, '-crf', '24', '-vf', 'scale=ceil(iw/4)*2:ceil(ih/4)*2', '-c:a', 'copy', fname2])                   
            fs2 = os.stat(fname2).st_size
            if fs2 < MAX_FS:
                with io.open(fname2, "rb") as stream:
                    await ctx.send(content=titlestring, file=discord.File(stream, filename="{}.mp4".format(title)))
                os.remove(fname)
                os.remove(fname2)
                await shrink.delete()
            else:
                await shrink.edit(content="File is still bigger than 8mb.. attempting extra shrinkage.")
                subprocess.run(['ffmpeg', '-i', fname2, '-preset', 'veryfast', '-crf', '28', '-c:a', 'copy', fname3])
                fs3 = os.stat(fname3).st_size
                if fs3 < MAX_FS:
                    with io.open(fname3, "rb") as stream:
                        await ctx.send(content=titlestring, file=discord.File(stream, filename="{}.mp4".format(title)))
                    os.remove(fname)
                    os.remove(fname2)
                    os.remove(fname3)
                    await shrink.delete()
                else:
                    await shrink.edit(content="File is still bigger than 8mb.. attempting extra shrinkage. (quality may be very bad on long videos)")
                    file_string_raw = subprocess.run(['ffmpeg', '-hide_banner', '-i', fname], capture_output=True)
                    file_string = file_string_raw.stderr.decode("utf-8")[0:len(file_string_raw.stderr)-1]
                    bitrate = await self.calc_bitrate(file_string, MAX_FS)
                    if bitrate < 0:
                        await ctx.send(content="Video was too long, could not shrink enough.")
                        os.remove(fname)
                        os.remove(fname2)
                        os.remove(fname3)
                        await shrink.delete()
                    else:
                        os.remove(fname3)
                        subprocess.run(['ffmpeg', '-y', '-i', fname2, '-b:v',  f'{bitrate}k', '-maxrate', f'{bitrate}k', '-b:a', '128k', fname3])
                        with io.open(fname3, "rb") as stream:
                            await ctx.send(content=f'{titlestring} (Hoobot note: Quality may be (very) bad. click link if needed)', file=discord.File(stream, filename="{}.mp4".format(title)))
                        os.remove(fname)
                        os.remove(fname2)
                        os.remove(fname3)
                        await shrink.delete()
    
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

    @commands.command()
    async def vredditdl(self, ctx, url):
        """Downloads the vreddit video and links it to webserver if too large"""
        async with ctx.typing():
            if url[0] == '<':
                url = url[1:len(url)-1]
                
            fname = '/tmp/{}.mp4'.format(ctx.message.id)

            if url.find("v.redd.it") >= 0:
                subprocess.run(['youtube-dl', url, '-o', fname])
                #fs = os.stat(fname).st_size
                fs = await self.file_size(fname)
                if fs < 8388119:
                    stream=io.open(fname, "rb")
                    await ctx.send(content="", file=discord.File(stream, filename=f"vid.mp4"))
                    os.remove(fname)
                else:
                    tmp= url.index("t/")
                    fname2 = url[tmp+2:]
                    subprocess.run(['cp', fname, '/mnt/NAS/NAS/webshareredditlinks/{}.mp4'.format(fname2)])
                    await ctx.send("File was too large. Link: https://owldyn.net/share/redditlinks/{}.mp4".format(fname2))
                    os.remove(fname)
            elif url.find("reddit.com") >= 0:
                subprocess.run(['youtube-dl', url, '-o', fname])
                titleraw = subprocess.run(['youtube-dl', '--get-title', url], capture_output=True)
                title = titleraw.stdout.decode("utf-8")[0:len(titleraw.stdout)-1]
                
                #fs = os.stat(fname).st_size
                fs = await self.file_size(fname)
                if fs < 8388119:
                    stream=io.open(fname, "rb")
                    await ctx.send(content="Title: {}".format(title), file=discord.File(stream, filename="{}.mp4".format(title)))
                    os.remove(fname)
                else:
                    subprocess.run(['cp', fname, '/mnt/NAS/NAS/webshareredditlinks/{}.mp4'.format(title)])
                    title = title.replace(' ', '%20')
                    await ctx.send("File was too large. Link: https://owldyn.net/share/redditlinks/{}.mp4".format(title))
                    os.remove(fname)
            else:
                await ctx.send("{} is not a valid v.redd.it link.".format(url))
        
    @commands.command()
    async def vredditlink(self, ctx, url, audio="yes", title="UNSET"):
        """Downloads the v.redd.it video and sends it. If it is too large, attempts to shrink it."""
        async with ctx.typing():
            if url[0] == '<':
                url = url[1:len(url)-1]
            else: 
                try:
                    await ctx.message.edit(suppress=True)
                except:
                    pass
            
            if "v.redd.it" in url:
                url = req.get(url).url
            
            if "reddit.com" in url:
                if title == "UNSET":
                    id = self.get_submission_id(url)
                    title = await self.get_submission_title(id)
                await self.download_and_send(ctx, title, audio, url)
            else:
                await ctx.send("{} is not a valid reddit link.".format(url))
                try:
                    await ctx.message.edit(suppress=True)
                except:
                    pass

    async def genericlink(self, ctx, url, title, audio="yes"):
        """Downloads the video and sends it. If it is too large, attempts to shrink it."""
        async with ctx.typing():
            if url[0] == '<':
                url = url[1:len(url)-1]
            else: 
                try:
                    await ctx.message.edit(suppress=True)
                except:
                    pass

            await self.download_and_send(ctx, title, audio, url)

    async def gfylink(self, ctx, url, redditlink, audio="yes"):
        """Downloads and uploads a gfycat video"""
        async with ctx.typing():
            if url[0] == '<':
                url = url[1:len(url)-1]
            else: 
                try:
                    await ctx.message.edit(suppress=True)
                except:
                    pass
            
            tmpfname = f'/tmp/tmp{ctx.message.id}.mp4'
            fname = '/tmp/{}.mp4'.format(ctx.message.id)
            fname2 = '/tmp/{}2.mp4'.format(ctx.message.id)
            fname3 = '/tmp/{}3.mp4'.format(ctx.message.id)

            if audio == "yes":
                subprocess.run(['youtube-dl', url, '-o', fname])
                audiocheckraw = subprocess.run(['ffmpeg', '-hide_banner', '-i', fname, '-af', 'volumedetect', '-vn', '-f', 'null', '-', '2>&1'], capture_output=True)
                audiocheck = audiocheckraw.stderr.decode("utf-8")[0:len(audiocheckraw.stderr)-1]
                if "does not contain any stream" in audiocheck and "mean_volume:" not in audiocheck:
                    os.rename(fname, tmpfname)
                    subprocess.run(['ffmpeg', '-i', tmpfname, '-f', 'lavfi', '-i', 'anullsrc=channel_layout=stereo:sample_rate=44100', '-c:v', 'copy', '-c:a', 'aac', '-map', '0:v', '-map', '1:a', '-shortest', fname]) 
                    os.remove(tmpfname)
            else:                
                subprocess.run(['youtube-dl', '-f', 'bestvideo', url, '-o', tmpfname])
                subprocess.run(['ffmpeg', '-i', tmpfname, '-f', 'lavfi', '-i', 'anullsrc=channel_layout=stereo:sample_rate=44100', '-c:v', 'copy', '-c:a', 'aac', '-map', '0:v', '-map', '1:a', '-shortest', fname]) 
                os.remove(tmpfname)
            
            if url.find("gfycat.com") >= 0:
                titleraw = subprocess.run(['youtube-dl', '--get-title', redditlink], capture_output=True)
                title = titleraw.stdout.decode("utf-8")[0:len(titleraw.stdout)-1]

                fs = os.stat(fname).st_size
                if fs < 8388119:
                    stream=io.open(fname, "rb")
                    await ctx.send(content="Title: {}".format(title), file=discord.File(stream, filename="{}.mp4".format(title)))
                    os.remove(fname)
                else:
                    shrink: discord.Message = await ctx.send("File is more than 8mb... attempting to shrink.")
                    subprocess.run(['ffmpeg', '-i', fname, '-crf', '24', '-vf', 'scale=ceil(iw/4)*2:ceil(ih/4)*2,fps=24', '-c:a', 'copy', fname2])                   
                    fs2 = os.stat(fname2).st_size
                    if fs2 < 8388119:
                        stream=io.open(fname2, "rb")
                        await ctx.send(content="Title: {}".format(title), file=discord.File(stream, filename="{}.mp4".format(title)))
                        os.remove(fname)
                        os.remove(fname2)
                        await shrink.delete()
                    else:
                        await shrink.edit(content="File is still bigger than 8mb.. attempting maximum shrinkage (may take a while).")
                        subprocess.run(['ffmpeg', '-i', fname2, '-preset', 'veryslow', '-crf', '32', '-b:a', '96k', fname3])
                        fs3 = os.stat(fname3).st_size
                        if fs3 < 8388119:
                            stream=io.open(fname3, "rb")
                            await ctx.send(content="Title: {}".format(title), file=discord.File(stream, filename="{}.mp4".format(title)))
                            await shrink.delete()
                        else:
                            await shrink.delete()
                            await ctx.send("File too large, could not reduce below 8MB.")
                        os.remove(fname)
                        os.remove(fname2)
                        os.remove(fname3)
            else:
                await ctx.send("{} is not a valid gfycat link.".format(url))


    @commands.command()
    async def tenor(self, ctx):
        """Search 3 previous messages for tenor links, and link them without embedding the gif"""
        urls = []
        async for message in ctx.channel.history(limit=4):
            if message.content.find("tenor.com") >= 0:
                urls.append(message.content)
        if not urls:
            await ctx.send("No tenor gifs found in last 3 messages")
        else:
            urls.reverse()
            for url in urls:
                await ctx.send("<{}>".format(url))

    def get_submission_id(self, url):
        """Parses reddit url, finds submission ID. Comment ID will be the second object, but will be blank if none.
           @return: [submission_id, comment_id] """
        if url[len(url)-1] != '/':
            url = url + '/'
        submission_id = re.search(r'(http.?://.?.?.?.?reddit.com/r/[^/]*/comment.?/)([^/]*)(/[^/]*/?)(.*)/?', url).group(2)
        comment_id = re.search(r'(http.?://.?.?.?.?reddit.com/r/[^/]*/comment.?/)([^/]*)(/[^/]*/?)([^/]*)/?', url).group(4)
        return [submission_id, comment_id]

    async def get_submission(self, submission_id):
        """Gets a reddit submission.
           @return: Reddit submission"""
        try: 
            submission = await self.reddit.submission(submission_id, lazy=True)
            await submission.load()
            return submission
        except Exception as e:
            raise e

    async def get_comment(self, comment_id):
        """Gets a reddit comment.
           @return: Comment"""
        try:
            comment = await self.reddit.comment(comment_id)
            return comment
        except Exception as e:
            raise e

    async def post_comment(self, ctx, comment_info):
        embed_title = f'Comment by {comment_info.author.name}'
        embed_description = comment_info.body
        if (len(embed_title + embed_description) < 1950) and (len(embed_title) < 255):
            embed = discord.Embed(title=embed_title, description=embed_description.replace(">!", "||").replace("!<", "||"))
            try:
                await ctx.send(embed=embed)
                await ctx.message.edit(suppress=True)
            except:
                return
        else:
            await ctx.send("Comment too long to post (Discord max limit of 2000 characters).")

    @commands.command()
    async def redditlink(self, ctx, url, audio = "yes", auto = "no"):
        """Grab i.imgur or i.reddit links from a reddit comment page. Also will check for videos if images not found.
        Will also check for self post text and post if small enough, if nothing else is found."""
        if auto == "no":
            auto = False
        else:
            auto = True
        async with ctx.typing():
            if url[0] == '<':
                url = url[1:len(url)-1]
            else: 
                try:
                    await ctx.message.edit(suppress=True)
                except:
                    pass
            if "reddit" not in url:
                if not auto:
                    await ctx.send("Not a valid reddit link")
                return

            try:
                ids = self.get_submission_id(url)
                submission_id = ids[0]
                comment_id = ids[1]
                post_info = await self.get_submission(submission_id)
                if comment_id:
                    comment_info = await self.get_comment(comment_id)
                else:
                    comment_info = None
                title = post_info.title
                submission_link = post_info.url
                is_self = post_info.is_self
                selftext = post_info.selftext
            except Exception as ex:
                if not auto:
                    await ctx.send("Hoot! Error fetching the reddit submission. Either Reddit is having issues or your link is not what I expect.")
                    await ctx.send(f'Error: {str(ex)}')
                return
            if is_self:
                if len(selftext) < 1500:
                    if len(title) > 255:
                        return #TODO make it actually post, but cleanly
                    else:
                        e = discord.Embed(title=title, description=selftext.replace(">!", "||").replace("!<", "||"))
                        try:
                            await ctx.send(embed=e)
                            await ctx.message.edit(suppress=True)
                            return
                        except:
                            return
                else:
                    return

            regexlink = []
            regexlink.append(re.search(r'http.?://v.redd.it/[a-zA-Z0-9]*', str(submission_link)))
            regexlink.append(re.search(r'http.?://preview.redd.it/[a-zA-Z0-9]*.[pjg][npi][gf]', str(submission_link)))
            regexlink.append(re.search(r'http.?://i.redd.it/[a-zA-Z0-9]*.[pjg][npi][gf]', str(submission_link)))
            regexlink.append(re.search(r'http.?://[i]?.?imgur.com/[a-zA-Z0-9]*.?[pjg]?[npi]?[gf]?[v]?', str(submission_link)))   
            regexlink.append(re.search(r'http.?://gfycat.com/[a-zA-Z0-9]*', str(submission_link)))
            regexlink.append(re.search(r'http.?://.?.?.?.?reddit.com/gallery/.*', str(submission_link)))
                   
            imglink = "none"
            for search in regexlink:
                try:
                    imglink = search.group(0)
                    break
                except:
                    pass
            if "preview.redd.it" in imglink:
                imglink = imglink.replace("preview.redd", "i.redd")
            elif "/imgur.com" in imglink:
                imglink = imglink.replace("/imgur.com", "/i.imgur.com")
                if ".png" not in imglink and ".jpg" not in imglink and ".gif" not in imglink:
                    imglink = imglink + ".png"
            if "v.redd.it" in imglink:
                await self.vredditlink(ctx=ctx, url=url, audio=audio, title=title)
            elif "gfycat" in imglink:
                await self.gfylink(ctx=ctx, url=imglink, redditlink=url, audio=audio)
            elif ("imgur" in imglink) and (".gifv" in imglink):
                await self.genericlink(ctx=ctx, url=imglink, title=title)
            elif "reddit.com/gallery" in imglink:
                gallery = []
                discord_max_preview = 5

                for i in post_info.media_metadata.items():
                    url = i[1]['p'][0]['u']
                    url = url.split("?")[0].replace("preview", "i")
                    gallery.append(url)
                gallery = list(reversed(gallery)) #Since reddit apparently sends the list in reverse order...
                while len(gallery) > 0:
                    message = ""
                    i = 0
                    while i < discord_max_preview:
                        i += 1
                        if len(gallery) > 0:
                            message += gallery.pop(0)
                            message += '\n'
                    await ctx.send(message)
                await ctx.send(f'Title: {title}')
            else:
                if len(title) > 255:
                    description = title
                    title = ""
                else:
                    description = ""
                e = discord.Embed(title=title, description=description)
                if imglink == "none":
                    imglink = submission_link
                e.set_image(url=imglink)
                await ctx.send(embed=e)
                try:
                    await ctx.message.edit(suppress=True)
                except:
                    pass

            if comment_info:
                await self.post_comment(ctx, comment_info)

    @commands.guild_only()
    @commands.group(name="autoredditignore")
    async def autoredditignore(self, ctx):
        """Change autoredditpost cog ignore settings."""

    @autoredditignore.command(name="server")
    @checks.admin_or_permissions(manage_guild=True)
    async def _redditdownloadignore_server(self, ctx):
        """Ignore/Unignore the current server"""

        guild = ctx.message.guild
        guilds = await self.conf.guilds_ignored()
        if guild.id in guilds:
            guilds.remove(guild.id)
            await ctx.send("I will no longer ignore this server.")
        else:
            guilds.append(guild.id)
            await ctx.send("I will ignore this server. Explicitly use !redditlink to use this feature.")
        await self.conf.guilds_ignored.set(guilds)

    @autoredditignore.command(name="channel")
    @checks.admin_or_permissions(manage_guild=True)
    async def _redditdownloadignore_channel(self, ctx):
        """Ignore/Unignore the current channel"""

        chan = ctx.message.channel
        chans = await self.conf.channels_ignored()
        if chan.id in chans:
            chans.remove(chan.id)
            await ctx.send("I will no longer ignore this channel.")
        else:
            chans.append(chan.id)
            await ctx.send("I will ignore this channel. Explicitly use !redditlink to use this feature.")
        await self.conf.channels_ignored.set(chans)

    @autoredditignore.command(name="self")
    async def _redditdownloadignore_user(self, ctx):
        """Ignore/Unignore the current user"""

        user = ctx.message.author
        users = await self.conf.users_ignored()
        if user.id in users:
            users.remove(user.id)
            await ctx.send("I will no longer ignore your links.")
        else:
            users.append(user.id)
            await ctx.send("I will ignore your links. Explicitly use !redditlink to use this feature.")
        await self.conf.users_ignored.set(users)

    @commands.Cog.listener("on_message_without_command")
    async def autoredditlink(self, message):
        if message.author.bot:
            return
        if message.guild.id in await self.conf.guilds_ignored():
            return
        if message.channel.id in await self.conf.channels_ignored():
            return
        if message.author.id in await self.conf.users_ignored():
            return
        msg_content = message.content.lower()
        if "reddit" in msg_content and "com" in msg_content:
            reddit_regex = re.search(r'http.?://.?.?.?.?reddit.com/r/[^/]*/comment.?/[^/]*/.*', msg_content)
            if reddit_regex:
                ctx = await self.bot.get_context(message)
                await self.redditlink(ctx = ctx, url = reddit_regex.group(0), auto = "no")

    @commands.command()
    async def redditcomment(self, ctx, url):
        async with ctx.typing():
            if url[0] == '<':
                url = url[1:len(url)-1]
            else:
                try:
                    await ctx.message.edit(suppress=True)
                except:
                    pass
            if "reddit" not in url:
                await ctx.send("Not a valid reddit link")
                return
            try:
                ids = self.get_submission_id(url)
                comment_id = ids[1]
                if comment_id:
                    comment_info = await self.get_comment(comment_id)
                    await self.post_comment(ctx, comment_info)
                else:
                    await ctx.send("Could not fetch comment info. Either the link isn't what I expect, or reddit is having problems.")
                    return
            except:
                await ctx.send("Could not fetch comment info. Either the link isn't what I expect, or reddit is having problems.")
                return
            