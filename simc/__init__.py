from .cog import Simc


async def setup(bot):
    await bot.add_cog(Simc(bot))
