from .vredditdl import VRedditDL

async def setup(bot):
    await bot.add_cog(VRedditDL(bot))
