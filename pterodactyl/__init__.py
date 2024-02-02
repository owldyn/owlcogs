from .cog import Pterodactyl

__red_end_user_data_statement__ = ""


async def setup(bot):
    await bot.add_cog(Pterodactyl(bot))
