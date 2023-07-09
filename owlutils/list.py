import discord
from redbot.core import commands
from redbot.core.commands import Context


class ListMixin:
    """Class to mixin because I'm too lazy to make it its own full cog"""

    def make_list_embed(self, list_name, lst):
        """Returns an embed for the list"""
        return discord.Embed(title=list_name, description="\n".join(lst))

    @commands.hybrid_group(
        name="list",
        description="Make and print lists",
    )
    async def owl_list(self, ctx):
        """This is now a slash command! use /list now"""

    @owl_list.app_command.command(
        name="create",
        description="Create a list",
    )
    async def create(self, ctx: discord.Interaction, list_name: str):
        """Create a list"""
        async with self.conf.list() as list_conf:
            aid = str(ctx.user.id)
            user_conf = list_conf.get(aid, {})
            if user_conf.get(list_name):
                await ctx.response.send_message("List already exists!", ephemeral=True)
                return
            user_conf[list_name] = []
            list_conf[aid] = user_conf
        await ctx.response.send_message("Done!", ephemeral=True)

    @owl_list.app_command.command(
        name="bulk_set",
        description="set the list with a comma separated values list",
    )
    async def bset(self, ctx: discord.Interaction, list_name: str, *, values: str):
        """Set a comma separated list of values to the list"""
        async with self.conf.list() as list_conf:
            aid = str(ctx.user.id)
            user_conf = list_conf.get(aid, {})
            if user_conf.get(list_name) is None:
                await ctx.response.send_message("List doesn't already exist!", ephemeral=True)
                return
            user_conf[list_name] = values.split(",")
            list_conf[aid] = user_conf
        await ctx.response.send_message(
            embed=self.make_list_embed(list_name, user_conf[list_name]), ephemeral=True
        )

    @owl_list.app_command.command(
        name="add",
        description="add to the list with a comma separated values list",
    )
    async def badd(self, ctx: discord.Interaction, list_name: str, *, values: str):
        """Add a comma separated list of values to the list"""
        async with self.conf.list() as list_conf:
            aid = str(ctx.user.id)
            user_conf = list_conf.get(aid, {})
            if user_conf.get(list_name) is None:
                await ctx.response.send_message("List doesn't already exist!", ephemeral=True)
                return
            user_conf[list_name].extend(values.split(","))
            list_conf[aid] = user_conf
        await ctx.response.send_message(
            embed=self.make_list_embed(list_name, user_conf[list_name]), ephemeral=True
        )

    @owl_list.app_command.command(
        name="add_single",
        description="add to the list",
    )
    async def sadd(self, ctx: discord.Interaction, list_name: str, *, values: str):
        """Add a single values to the list"""
        async with self.conf.list() as list_conf:
            aid = str(ctx.user.id)
            user_conf = list_conf.get(aid, {})
            if user_conf.get(list_name) is None:
                await ctx.response.send_message("List doesn't already exist!", ephemeral=True)
                return
            user_conf[list_name].append(values)
            list_conf[aid] = user_conf
        await ctx.response.send_message(
            embed=self.make_list_embed(list_name, user_conf[list_name]), ephemeral=True
        )

    @owl_list.app_command.command()
    async def pop(self, ctx: Context, list_name: str):
        """Remove and send the next item in the list"""
        async with self.conf.list() as list_conf:
            aid = str(ctx.user.id)
            try:
                value = list_conf.get(aid, {}).get(list_name, []).pop(0)
            except IndexError:
                await ctx.response.send_message(
                    f"List {list_name} is empty or does not exist!", ephemeral=False
                )
                return
        await ctx.response.send_message(value, ephemeral=False)

    @owl_list.app_command.command()
    async def list(self, ctx: Context):
        """list all of your lists"""
        async with self.conf.list() as list_conf:
            aid = str(ctx.user.id)
            lst = list_conf.get(aid, {})
            await ctx.response.send_message(
                embed=self.make_list_embed("All lists", lst), ephemeral=True
            )

    @owl_list.app_command.command()
    async def show(self, ctx: Context, list_name: str):
        """list items in a list"""
        async with self.conf.list() as list_conf:
            aid = str(ctx.user.id)
            lst = list_conf.get(aid, {}).get(list_name)
            if lst is None:
                await ctx.response.send_message(
                    f"List {list_name} is empty or does not exist!", ephemeral=True
                )
                return
            await ctx.response.send_message(
                embed=self.make_list_embed(list_name, lst), ephemeral=True
            )
