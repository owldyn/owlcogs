from .vredditdl import VRedditDL
from bs4 import BeautifulSoup
import praw
import requests
import youtube_dl

def setup(bot):
    bot.add_cog(VRedditDL(bot))