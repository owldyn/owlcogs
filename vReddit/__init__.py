from .vredditdl import VRedditDL
from bs4 import BeautifulSoup
import praw
import requests

def setup(bot):
    bot.add_cog(VRedditDL(bot))