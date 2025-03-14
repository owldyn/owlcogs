from .define import Define

__red_end_user_data_statement__ = (
    "This cog stores no information about any users."
)


async def setup(bot):
    await bot.add_cog(Define(bot))
