from .owlutils import OwlUtils

__red_end_user_data_statement__ = (
    "This cog only stores information that is explicitly given by a user."
)


async def setup(bot):
    await bot.add_cog(OwlUtils(bot))
