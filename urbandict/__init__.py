from .urbandict import urbandict

__red_end_user_data_statement__ = (
    "This cog doesn't store information about users, but stores user generated information that is likely to contain a user's name."
)


async def setup(bot):
    await bot.add_cog(urbandict(bot))
