from .urbandict import urbandict


async def setup(bot):
    await bot.add_cog(urbandict(bot))
