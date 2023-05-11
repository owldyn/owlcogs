"""

This is supposed to be better than discord's default search system.

I guess we'll see.

"""

from .messageindex import MessageIndex

__red_end_user_data_statement__ = (
    "This cog stores all messages sent on the servers it is enabled in."
)


async def setup(bot):
    """Setup the bot"""
    await bot.add_cog(MessageIndex(bot))
