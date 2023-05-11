from .medialinks import MediaLinks

async def setup(bot):
    await bot.add_cog(MediaLinks(bot))
