from .twitter import twitter_DL
from bs4 import BeautifulSoup
import tweepy
import youtube_dl
import requests

async def setup(bot):
    await bot.add_cog(twitter_DL(bot))