from .genericdl import Genericdl
import yt_dlp

def setup(bot):
    bot.add_cog(Genericdl(bot))