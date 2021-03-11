from .evgacheck import EVGACheck

def setup(bot):
    bot.add_cog(EVGACheck(bot))