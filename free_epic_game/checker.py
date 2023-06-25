import discord
from redbot.core import Config, commands
from redbot.core.commands import Context
from epicstore_api import EpicGamesStoreAPI


class EpicGamesChecker(commands.Cog):

    """Small utils I'm making for myself."""

    CHECK_MARK = "✅"
    default_global_settings = {
        "history": {
            "last_check": [],
            "historical": {},
        }
    }

    def __init__(self, bot):
        self.bot = bot
        self.conf = Config.get_conf(self, identifier=26400736017)
        self.conf.register_global(**self.default_global_settings)
