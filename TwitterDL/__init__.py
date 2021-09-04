from .twitter import twitter_DL
from bs4 import BeautifulSoup
import tweepy
import youtube_dl
import requests

def setup(bot):
    bot.add_cog(twitter_DL(bot))