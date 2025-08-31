from .countdown import Countdown
from .owed import Owed
from .owlutils import OwlUtils
from .snooper import StatusSnooper
from .timestamp import Timestamp

__red_end_user_data_statement__ = "This cog stores information that is explicitly given by a user, as well as their status history."


async def setup(bot):
    await bot.add_cog(OwlUtils(bot))
    await bot.add_cog(StatusSnooper(bot))
    await bot.add_cog(Countdown(bot))
    await bot.add_cog(Timestamp(bot))
    await bot.add_cog(Owed(bot))
