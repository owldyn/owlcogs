from .vredditdl import VRedditDL
from bs4 import BeautifulSoup

def setup(bot):
    bot.add_cog(VRedditDL(bot))