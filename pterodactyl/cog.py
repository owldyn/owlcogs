import logging
import re
from tempfile import NamedTemporaryFile

import discord
from redbot.core import Config, app_commands, commands

from .calculate import Calculator

DISCORD_MAX_FILESIZE = 8388119


class Pterodactyl(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.conf = Config.get_conf(self, identifier=26400736017)
        self.conf.register_global(
            pterodactyl_api_key=None,
            url=None,
            ssh_keys={},
        )
        self.log = logging.getLogger("owlcogs.Pterodactyl")
