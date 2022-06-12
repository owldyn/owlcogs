import discord
from redbot.core import Config, checks, commands


class Turns(commands.Cog):

    """Make lists to remember whose turn it is to do something."""

    default_global_settings = {"turn_lists": {}}
    # Format it is saved in:
    #{ "turn_lists":
    #   { guild_id (str): {
    #       name_of_list: {
    #           "turn_list": [user1, user2, user3],
    #           "current": 1
    #       }
    #   }
    #}

    def __init__(self, bot):
        self.bot = bot
        self.conf = Config.get_conf(self, identifier=254007352)
        self.conf.register_global(**self.default_global_settings)

    @commands.guild_only()
    @commands.group(name="turns")
    async def turns(self, ctx):
        """Make, list, or modify turn lists!"""

    @turns.command(name="list")
    async def _list_turns_lists(self, ctx):
        """Show all of the turn lists for the server"""
        async with self.conf.turn_lists() as config_turn_list:
            if not config_turn_list:
                await ctx.send("This guild doesn't have any!")
            else:
                turn_list = config_turn_list.get(str(ctx.guild.id), None)
                if turn_list:
                    await ctx.send('\n'.join(turn_list))
                else:
                    await ctx.send("This guild doesn't have any!")

    @turns.command(name="create")
    async def _create_turn_list(self, ctx, name, *list_entrances):
        """Create a turn list for this server

            name: The name of the list. Must have no spaces
            list_entrances: space delimited list of things you want to be in the list (so, this person that person thisperson would be [this, person, that, person, thisperson] )
        """
        async with self.conf.turn_lists() as config_turn_list:
            turn_list = config_turn_list.get(str(ctx.guild.id), None)
            if not turn_list:
                config_turn_list[str(ctx.guild.id)] = {}
                turn_list = config_turn_list.get(str(ctx.guild.id), None)
            if turn_list.get(name, None):
                await ctx.send("A list by that name already exists!")
            else:
                new_turn_list = {'turn_list': list_entrances,
                                   'current': 0}
                config_turn_list[str(ctx.guild.id)][name] = new_turn_list
                embed = discord.Embed(title = name, description = self.pretty_print(turn_list=list_entrances, current=0))
                await ctx.send(embed=embed)

    @turns.command(name="get")
    async def _get_turns_list(self, ctx, name):
        """Get a turn list by name"""
        async with self.conf.turn_lists() as config_turn_list:
            turn_list = config_turn_list.get(str(ctx.guild.id), None)
            if turn_list:
                current_list = turn_list.get(name)
                if current_list:
                    list_entrances, current = self.get_list_info(current_list)
                    embed = discord.Embed(title = name, description = self.pretty_print(turn_list=list_entrances, current=current))
                    await ctx.send(embed=embed)
                else:
                    await ctx.send("That list name doesn't seem to exist!")
            else:
                await ctx.send("This guild doesn't have any!")
            
    @turns.command(name="next")
    async def _next_person(self, ctx, name):
        """Goes to the next index in the list"""
        await self._add_to_index(ctx, name, 1)

    @turns.command(name="previous")
    async def _previous_person(self, ctx, name):
        """Goes to the previous index in the list"""
        await self._add_to_index(ctx, name, -1)

    async def _add_to_index(self, ctx, name, number):
        async with self.conf.turn_lists() as config_turn_list:
            turn_list = config_turn_list.get(str(ctx.guild.id), None)
            if turn_list:
                if turn_list.get(name):
                    t_l = turn_list.get(name)
                    t_l['current'] += number
                    if len(t_l['turn_list']) <= t_l['current']:
                        t_l['current'] = 0
                    elif t_l['current'] < 0:
                        t_l['current'] = len(t_l['turn_list']) - 1

                    list_entrances, current = self.get_list_info(t_l)
                    embed = discord.Embed(title = name, description = self.pretty_print(turn_list=list_entrances, current=current))
                    await ctx.send(embed=embed)
                else:
                    await ctx.send("That list name doesn't seem to exist!")
    @staticmethod
    def get_list_info(turn_list_dict):
        """qol method to get the stuff easier"""
        return turn_list_dict.get('turn_list'), turn_list_dict.get('current')

    @staticmethod
    def pretty_print(**turn_list_dict):
        """Creates prettyprint from list in format:
        ` *1 | list_object 0`
        `  2 | list_object 1`
        `  3 | list_object 2`
        `-------------------`
        `Current: 1 | list_object 0`
        Args:
            - **turn_list_dict:
                - turn_list (list) : the list to grab from
                - current (int) : the current index in the list
        """
        turn_list = turn_list_dict['turn_list']
        current = turn_list_dict['current']
        output = ""
        longest = 0
        for index, value in enumerate(turn_list):
            if (index + 1) == current + 1:
                index_str = f'*{index + 1}'
            else:
                index_str = str(index + 1)
            add_to_output = f'`{index_str:>3} | {value}`\n'
            output += add_to_output
            longest = max(longest, len(add_to_output) - 3)
        output += f"`{'-' * longest}`\n`Current: {current + 1} | {turn_list[current]}`"
        return output
