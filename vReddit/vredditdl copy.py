from redbot.core import Config, checks, commands
import asyncio
import time
import subprocess
import os
import io
import discord

class VRedditDL(commands.Cog):
    """v.redd.it downloader"""

    def __init__(self, bot):
        """set it up"""
        super().__init__()
        self.bot = bot

    async def file_size(self, fname):
        statinfo = os.stat(fname)
        return statinfo.st_size

    @commands.command()
    async def vredditdl(self, ctx, url):
        """Downloads the vreddit video and links it to webserver if too large"""
        async with ctx.typing():
            if url[0] == '<':
                url = url[1:len(url)-1]
                
            fname = '/tmp/{}.mp4'.format(ctx.message.id)

            if url.find("v.redd.it") >= 0:
                subprocess.run(['youtube-dl', url, '-o', fname])
                fs = os.stat(fname).st_size
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
                
                fs = os.stat(fname).st_size
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
    async def vredditlink(self, ctx, url):
        """Downloads the vreddit video and shrinks it then attempts to upload again if too large"""
        async with ctx.typing():
            if url[0] == '<':
                url = url[1:len(url)-1]

            fname = '/tmp/{}.mp4'.format(ctx.message.id)
            fname2 = '/tmp/{}2.mp4'.format(ctx.message.id)
            fname3 = '/tmp/{}3.mp4'.format(ctx.message.id)

            if url.find("v.redd.it") >= 0:
                subprocess.run(['youtube-dl', url, '-o', fname])
                fs = os.stat(fname).st_size
                if fs < 8388119:
                    stream=io.open(fname, "rb")
                    await ctx.send(content="", file=discord.File(stream, filename=f"vid.mp4"))
                    os.remove(fname)
                else:
                    shrink: discord.Message = await ctx.send("File is more than 8mb... attempting to shrink.")
                    subprocess.run(['ffmpeg', '-i', fname, '-crf', '24', '-vf', 'scale=ceil(iw/4)*2:ceil(ih/4)*2', '-c:a', 'copy', fname2])                    
                    fs2 = os.stat(fname2).st_size
                    if fs2 < 8388119:
                        stream=io.open(fname2, "rb")
                        await ctx.send(content="", file=discord.File(stream, filename=f"vid.mp4"))
                        os.remove(fname)
                        os.remove(fname2)
                        await shrink.delete()
                    else:
                        await shrink.edit(content="File is still bigger than 8mb.. attempting extra shrinkage.")
                        subprocess.run(['ffmpeg', '-i', fname2, '-crf', '28', '-c:a', 'copy', fname3])
                        fs3 = os.stat(fname3).st_size
                        if fs3 < 8388119:
                            stream=io.open(fname3, "rb")
                            await ctx.send(content="", file=discord.File(stream, filename="vid.mp4"))
                            await shrink.delete()
                        else:
                            await shrink.delete()
                            await ctx.send("File too large, could not reduce below 8MB.")
                        os.remove(fname)
                        os.remove(fname2)
                        os.remove(fname3)
            elif url.find("reddit.com") >= 0:
                subprocess.run(['youtube-dl', url, '-o', fname])
                titleraw = subprocess.run(['youtube-dl', '--get-title', url], capture_output=True)
                title = titleraw.stdout.decode("utf-8")[0:len(titleraw.stdout)-1]

                fs = os.stat(fname).st_size
                if fs < 8388119:
                    stream=io.open(fname, "rb")
                    await ctx.send(content="Title: {}".format(title), file=discord.File(stream, filename="{}.mp4".format(title)))
                    os.remove(fname)
                else:
                    shrink: discord.Message = await ctx.send("File is more than 8mb... attempting to shrink.")
                    subprocess.run(['ffmpeg', '-i', fname, '-crf', '24', '-vf', 'scale=ceil(iw/4)*2:ceil(ih/4)*2', '-c:a', 'copy', fname2])                   
                    fs2 = os.stat(fname2).st_size
                    if fs2 < 8388119:
                        stream=io.open(fname2, "rb")
                        await ctx.send(content="Title: {}".format(title), file=discord.File(stream, filename="{}.mp4".format(title)))
                        os.remove(fname)
                        os.remove(fname2)
                        await shrink.delete()
                    else:
                        await shrink.edit(content="File is still bigger than 8mb.. attempting extra shrinkage.")
                        subprocess.run(['ffmpeg', '-i', fname2, '-crf', '28', '-c:a', 'copy', fname3])
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
                await ctx.send("{} is not a valid reddit video link.".format(url))
                

    @commands.command()
    async def Hoot(self, ctx):
        test: discord.Message = await ctx.send("Hoot!")
        i = 0
        while i < 10:
            await test.edit(content="{} Hoot!".format(test.content))
            i = i + 1
            await asyncio.sleep(1)
    
    
    @commands.command()
    async def tenor(self, ctx):
        urls = []
        async for message in ctx.channel.history(limit=4):
            if message.content.find("tenor.com") >= 0:
                urls.append(message.content)
        if not urls:
            await ctx.send("No tenor gifs found in last 3 messages")
        else:
            urls.reverse()
            for url in urls:
                tmp= url.index("tenor.com/view/")
                name = url[tmp+15:]
                await ctx.send(name)
        

