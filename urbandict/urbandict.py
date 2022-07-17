import discord
import requests
from redbot.core import Config, checks, commands


class urbandict(commands.Cog):

    """Make lists to remember whose turn it is to do something."""

    default_global_settings = {"turn_lists": {}}
    # Format it is saved in:
    #{ "turn_lists":
    #   { guild_id (str): {
    #       name_of_list: {
    #           "turn_list": [user1, user2, user3],
    #           "current": 1
    #       }
    #   }
    #}

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def defineu(self, ctx, *words):
        """define a word from urban dictionary"""
        phrase = " ".join(words)
        api_endpoint = "https://api.urbandictionary.com/v0/define"
        params = {'term': phrase}
        try:
            term = requests.get(api_endpoint, params=params).json()
        except requests.JSONDecodeError:
            ctx.send("Couldn't parse output from urban dictionary!")
            return
        term = term.get('list')
        if term:
            best_index = self.get_best(term)
            definition = term[best_index].get('definition').replace('[','').replace(']','')
            definition = f"[link]({term[best_index].get('permalink')})\n{definition}"
            embed = discord.Embed(title=phrase, description=definition)
            #embed.set_footer(text = f"[{phrase}]({term[best_index].get('permalink')})")
            await ctx.send(embed=embed)
        else:
            await ctx.send("Definition not found!")
    
    @staticmethod
    def get_best(term_list):
        best_index = 0
        best_score = -1000000
        for index, term in enumerate(term_list):
            score = term.get('thumbs_up', 0) - term.get('thumbs_down', 100)
            if score > best_score:
                best_index = index
                best_score = score
        return best_index