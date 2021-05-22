from redbot.core import Config, checks, commands
import asyncio
import time
import subprocess
import os
import io
import discord
import re
from urllib.request import Request, urlopen
from bs4 import BeautifulSoup

class VRedditDL(commands.Cog):
    """v.redd.it downloader"""

    def __init__(self, bot):
        """set it up"""
        super().__init__()
        self.bot = bot

    async def file_size(self, fname):
        """check filesize"""
        statinfo = os.stat(fname)
        return statinfo.st_size

    async def check_audio(self, audio, fname, tmpfname, url):
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

    async def download_and_send(self, ctx, title, fs, fname, fname2, fname3):
        if title is None:
            titlestring = ""
        else:
            titlestring = f'Title: {title}'
        if fs < 8388119:
            with io.open(fname, "rb") as stream:
                await ctx.send(content=titlestring, file=discord.File(stream, filename="{}.mp4".format(title)))
            os.remove(fname)
        else:
            shrink: discord.Message = await ctx.send("File is more than 8mb... attempting to shrink.")
            subprocess.run(['ffmpeg', '-i', fname, '-crf', '24', '-vf', 'scale=ceil(iw/4)*2:ceil(ih/4)*2', '-c:a', 'copy', fname2])                   
            fs2 = os.stat(fname2).st_size
            if fs2 < 8388119:
                with io.open(fname2, "rb") as stream:
                    await ctx.send(content=titlestring, file=discord.File(stream, filename="{}.mp4".format(title)))
                os.remove(fname)
                os.remove(fname2)
                await shrink.delete()
            else:
                await shrink.edit(content="File is still bigger than 8mb.. attempting extra shrinkage. (quality may be very bad on long videos)")
                subprocess.run(['ffmpeg', '-i', fname2, '-preset', 'veryfast', '-crf', '28', '-c:a', 'copy', fname3])
                fs3 = os.stat(fname3).st_size
                if fs3 < 8388119:
                    with io.open(fname3, "rb") as stream:
                        await ctx.send(content=titlestring, file=discord.File(stream, filename="{}.mp4".format(title)))
                    os.remove(fname)
                    os.remove(fname2)
                    os.remove(fname3)
                    await shrink.delete()
                else:
                    await shrink.delete()
                    await ctx.send("File too large, could not reduce below 8MB.")
                    os.remove(fname)
                    os.remove(fname2)
                    os.remove(fname3)
    async def calc_bitrate(self, fname, filesize):
        pass #TODO FINISH THIS

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
                    subprocess.run(['cp', fname, '/mnt/NAS/webshare/redditlinks/{}.mp4'.format(fname2)])
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
                    subprocess.run(['cp', fname, '/mnt/NAS/webshare/redditlinks/{}.mp4'.format(title)])
                    title = title.replace(' ', '%20')
                    await ctx.send("File was too large. Link: https://owldyn.net/share/redditlinks/{}.mp4".format(title))
                    os.remove(fname)
            else:
                await ctx.send("{} is not a valid v.redd.it link.".format(url))
        
    @commands.command()
    async def vredditlink(self, ctx, url, audio="yes"):
        """Downloads the vreddit video and shrinks it then attempts to upload again if too large"""
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

            await self.check_audio(audio, fname, tmpfname, url)
            
            if url.find("v.redd.it") >= 0:
                fs = await self.file_size(fname)
                title = None
                await self.download_and_send(ctx, title, fs, fname, fname2, fname3)
            elif url.find("reddit.com") >= 0:
                titleraw = subprocess.run(['youtube-dl', '--get-title', url], capture_output=True)
                title = titleraw.stdout.decode("utf-8")[0:len(titleraw.stdout)-1]
                fs = os.stat(fname).st_size
                await self.download_and_send(ctx, title, fs, fname, fname2, fname3)
            else:
                await ctx.send("{} is not a valid reddit link.".format(url))
                try:
                    await ctx.message.edit(suppress=True)
                except:
                    pass
                

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
        
    @commands.command()
    async def redditlink(self, ctx, url, audio = "yes"):
        """Grab i.imgur or i.reddit links from a reddit comment page. Also will check for videos if images not found"""
        async with ctx.typing():
            if url[0] == '<':
                url = url[1:len(url)-1]
            else: 
                try:
                    await ctx.message.edit(suppress=True)
                except:
                    pass
            if "www.reddit.com" in url:
                url = url.replace("www.reddit", "old.reddit")
            elif "://reddit.com" in url:
                url = url.replace("reddit", "old.reddit")
            elif "new.reddit.com" in url:
                url = url.replace("new.reddit", "old.reddit")
            elif "reddit" not in url:
                await ctx.send("Not a valid reddit link")
                return
            req = Request(url,headers={'User-Agent': 'Mozilla/5.0'})
            webpageall = urlopen(req).read().decode('utf8')
            webpage = webpageall.partition('\n')[0]
            regexlink = []
            regexlink.append(re.search('http.?://v.redd.it/[a-zA-Z0-9]*', str(webpage)))
            regexlink.append(re.search('http.?://preview.redd.it/[a-zA-Z0-9]*.[pjg][npi][gf]', str(webpage)))
            regexlink.append(re.search('http.?://i.redd.it/[a-zA-Z0-9]*.[pjg][npi][gf]', str(webpage)))
            regexlink.append(re.search('http.?://[i]?.?imgur.com/[a-zA-Z0-9]*.[pjg][npi][gf][v]?', str(webpage)))   
            regexlink.append(re.search('http.?://gfycat.com/[a-zA-Z0-9]*', str(webpage)))         
            imglink = "none"
            for search in regexlink:
                try:
                    imglink = search.group(0)
                    break
                except:
                    pass
            if "preview.redd.it" in imglink:
                imglink = imglink.replace("preview.redd", "i.redd")

            if "v.redd.it" in imglink:
                await self.vredditlink(ctx=ctx, url=url, audio=audio)
            elif "gfycat" in imglink:
                await self.gfylink(ctx=ctx, url=imglink, redditlink=url, audio=audio)
            else:
                #titleraw = subprocess.run(['youtube-dl', '--get-title', url], capture_output=True)
                #title = titleraw.stdout.decode("utf-8")[0:len(titleraw.stdout)-1]
                soup = BeautifulSoup(webpage, 'html.parser')
                titleraw = soup.find('title')
                title = titleraw.string.split(' : ')
                e = discord.Embed(title=title[0])
                e.set_image(url=imglink)
                await ctx.send(embed=e)
                try:
                    await ctx.message.edit(suppress=True)
                except:
                    pass



