from .owlutils import OwlUtils

__red_end_user_data_statement__ = (
    "This cog doesn't store information about users."
)


def setup(bot):
    bot.add_cog(OwlUtils(bot))
