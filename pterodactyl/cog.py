import logging
import re
from concurrent.futures import ThreadPoolExecutor
from tempfile import NamedTemporaryFile
from typing import Any, Coroutine

import discord
from discord.interactions import Interaction
from redbot.core import Config, app_commands, commands

from .api_wrapper import PterodactylAPI
from .modals import NodeModal
from .ssh_handler import ZFSSSHHandler

CHECK_MARK = "✅"
RED_X_MARK = "❌"


class Pterodactyl(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.conf = Config.get_conf(self, identifier=26400736017)
        self.conf.register_global(
            pterodactyl_api_key=None,
            url=None,
            nodes={},
        )
        self.log = logging.getLogger("owlcogs.Pterodactyl")

    pterodactyl = app_commands.Group(
        name="pterodactyl",
        description="Pterodactyl commands.",
        guild_only=True,
        guild_ids=[89533605344215040, 83431109957783552],
    )

    async def _check_api_key(self):
        if not await self.conf.pterodactyl_api_key() and not await self.conf.url():
            return False

    async def _get_pterodactyl(self):
        url = await self.conf.url()
        api_key = await self.conf.pterodactyl_api_key()
        return url, PterodactylAPI(
            await self.conf.url(), await self.conf.pterodactyl_api_key()
        )

    async def server_autocomplete(self, ctx: commands.Context, current: str):
        if not self._check_api_key():
            return []
        _, pterodactyl = await self._get_pterodactyl()
        servers = pterodactyl.get_servers()

        return [
            app_commands.Choice(name=server.name, value=server.uuid)
            for server in servers
            if current in server.name
        ]

    async def online_server_autocomplete(self, ctx: commands.Context, current: str):
        if not self._check_api_key():
            return []
        _, pterodactyl = await self._get_pterodactyl()
        servers = pterodactyl.get_servers()
        servers = await self.server_autocomplete(ctx, current)
        with ThreadPoolExecutor() as pool:
            server_statuses = pool.map(
                pterodactyl.get_server_status, [server.value for server in servers]
            )
        response = [
            server
            for server, status in zip(servers, server_statuses)
            if status.current_state == "running"
        ]
        self.log.debug(response)
        return response

    @pterodactyl.command(name="set_api")  # type: ignore
    @commands.is_owner()
    async def set_api(self, ctx: discord.Interaction, api_key: str, url: str):
        """Set the api key for the pterodactyl instance."""
        await self.conf.pterodactyl_api_key.set(api_key)
        await self.conf.url.set(url)
        await ctx.response.send_message("Done.", ephemeral=True)

    @pterodactyl.command(name="list_servers")
    async def list_servers(self, ctx: discord.Interaction):
        """List all servers."""
        if not self._check_api_key():
            await ctx.response.send_message("No API key set.", ephemeral=True)
            return
        url, pterodactyl = await self._get_pterodactyl()
        servers = pterodactyl.get_servers()
        servers = sorted(servers, key=lambda x: x.default_port)
        servers_string = "\n".join(
            [
                f"[{server.name}]({url}/server/{server.identifier}): {server.default_port} ({server.node})"
                for server in servers
            ]
        )
        await ctx.response.send_message(f"{servers_string}", ephemeral=True)

    @pterodactyl.command(name="get_server_status")
    @app_commands.autocomplete(server_name=server_autocomplete)  # type: ignore
    async def get_server_status(self, ctx: discord.Interaction, server_name: str):
        """Get the status of a server."""
        if not self._check_api_key():
            await ctx.response.send_message("No API key set.", ephemeral=True)
            return
        url, pterodactyl = await self._get_pterodactyl()

        if not (server := pterodactyl.get_servers_dict("name").get(server_name)):
            await ctx.response.send_message(
                f"Server {server_name} not found.", ephemeral=True
            )
            return
        status = pterodactyl.get_server_status(server)
        memory_mb = status.memory_bytes / 1024 / 1024
        memory_percent = memory_mb / server.limits.memory
        check_or_x = CHECK_MARK if status.current_state == "running" else RED_X_MARK
        embed = (
            discord.Embed(
                url=f"https://{url}/server/{server.identifier}", title=f"{server_name}"
            )
            .add_field(name="Status", value=f"{check_or_x}")
            .add_field(
                name="Memory Percent",
                value=f"{memory_percent:.2%}",
            )
            .add_field(
                name="Memory",
                value=f"{memory_mb:.2f}MB/{server.limits.memory}MB",
            )
        )
        await ctx.response.send_message(embed=embed)

    @pterodactyl.command(name="restart_server")
    @commands.cooldown(1, 600)
    @app_commands.autocomplete(server_name=online_server_autocomplete)  # type: ignore
    async def restart_server(self, ctx: discord.Interaction, server_name: str):
        """Restart a server."""
        if not self._check_api_key():
            await ctx.response.send_message("No API key set.", ephemeral=True)
            return
        _, pterodactyl = await self._get_pterodactyl()

        if not (server := pterodactyl.get_servers_dict().get(server_name)):
            await ctx.response.send_message(
                f"Server {server_name} not found.", ephemeral=True
            )
            return
        worked = pterodactyl.restart_server(server)
        if worked:
            await ctx.response.send_message(f"Server {server.name} restarted.")
        else:
            await ctx.response.send_message(
                "Server returned unknown value.", ephemeral=True
            )

    @pterodactyl.command(name="set_node")  # type: ignore
    @commands.is_owner()
    async def set_node(self, ctx: discord.Interaction):
        """Set a node for zfs snapshots."""

        class _NodeModal(NodeModal):
            async def on_submit(_self, interaction: Interaction):
                self.log.info("saving node")
                await self.conf.nodes.set_raw(
                    _self.host.value,
                    value={
                        "host": _self.host.value,
                        "key": _self.key.value,
                        "dataset": _self.dataset.value,
                        "username": _self.username.value,
                    },
                )
                await interaction.response.send_message("Done.", ephemeral=True)

        await ctx.response.send_modal(_NodeModal())

    @pterodactyl.command(name="delete_node")  # type: ignore
    @commands.is_owner()
    async def delete_node(self, ctx: discord.Interaction, node: str):
        """Delete a node for zfs snapshots."""
        async with self.conf.nodes() as nodes:
            if node in nodes:
                del nodes[node]
        await ctx.response.send_message("Done.", ephemeral=True)

    @pterodactyl.command(name="zfs_snapshot")  # type: ignore
    @commands.is_owner()
    async def zfs_snapshot(self, ctx: discord.Interaction):
        """Create a zfs snapshot of a server."""
        responses = []
        nodes: dict = await self.conf.nodes()
        for node in nodes.values():
            self.log.debug("node: %s", node["host"])
            with ZFSSSHHandler(node) as handler:
                responses.append(handler.zfs_snapshot())

        await ctx.response.send_message(str(responses), ephemeral=True)
