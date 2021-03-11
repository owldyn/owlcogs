from .vredditdl import VRedditDL

def setup(bot):
    bot.add_cog(VRedditDL(bot))