from .genericdl import Genericdl
import yt_dlp

async def setup(bot):
    await bot.add_cog(Genericdl(bot))