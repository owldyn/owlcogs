"""
simc runner
"""
import asyncio
import logging
import os
from pathlib import Path
from time import time
from typing import Optional, cast

import discord
from discord.ui import Modal
from kubernetes.client import V1Job
from redbot.core import Config, app_commands, commands

from .kub_setup import KubernetesWrapper


class Simc(commands.Cog):
    default_global_settings = {
        "k8s_settings": {
            "pvc_name": "redbot-simc",
            "namespace": "default",
            "file_location": "/mnt/simc/",
            "base_url": "https://simc.owldyn.net/",
        },
    }

    def __init__(self, bot):
        """set it up"""
        super().__init__()
        self.log = logging.getLogger("owlcogs.simc")
        self.bot = bot
        self.config = Config.get_conf(self, 4007)
        self.config.register_global(**self.default_global_settings)
        self.config.register_member(characters=[])
        self.k8s: KubernetesWrapper

    simc_command = app_commands.Group(
        name="simc",
        description="Run your character through simc.",
        guild_only=True,
        guild_ids=[89533605344215040, 83431109957783552],
    )

    @simc_command.command(name="load_settings")  # type: ignore
    @commands.is_owner()
    async def load_settings(self, ctx: discord.Interaction):
        """Load the settings."""
        await self._load_settings()
        await ctx.response.send_message("Reloaded.", ephemeral=True)

    @simc_command.command(name="set_settings")  # type: ignore
    @commands.is_owner()
    async def set_k8s_settings(
        self,
        ctx: discord.Interaction,
        namespace: Optional[str] = None,
        pvc: Optional[str] = None,
        location: Optional[str] = None,
    ):
        """Admin command to set settings for how to run simc"""
        async with self.config.k8s_settings() as settings:
            settings["namespace"] = namespace or settings["namespace"]
            settings["pvc"] = pvc or settings["pvc"]
            settings["file_location"] = location or settings["file_location"]
        await ctx.response.send_message("Done.", ephemeral=True)

    async def _load_settings(self):
        async with self.config.k8s_settings() as settings:
            self.k8s = KubernetesWrapper(settings["namespace"], settings["pvc_name"])
            self.location = settings["file_location"]

    async def get_characters(self, ctx: discord.Interaction, current: str):
        """Get users characters for completion"""
        async with self.config.user(ctx.user)() as conf:
            return [
                app_commands.Choice(name=n, value=n)
                for n in conf.get("characters", [])
                if current in n
            ]

    async def get_type(self, ctx, current):
        selections = [
            app_commands.Choice(name="Dungeon Slice", value="DungeonSlice"),
            app_commands.Choice(name="Patchwerk", value="Patchwerk"),
        ]
        return [s for s in selections if current in s.name]

    @simc_command.command(name="run_character")
    @app_commands.autocomplete(sim_type=get_type)
    async def run_character(
        self,
        ctx: discord.Interaction,
        weights: bool = True,
        sim_type: str = "Patchwerk",
    ):
        """Run a character via the simc addon output."""

        class CharacterModal(Modal, title="Character Information"):
            character = discord.ui.TextInput(
                label="Simc output",
                style=discord.TextStyle.long,
                placeholder="Paste your simc output here",
                required=True,
            )

            async def on_submit(_self, interaction: discord.Interaction):
                now = int(time())
                async with self.config.k8s_settings() as settings:
                    location = settings.get("file_location")

                # Make input path if not exists
                path = Path(location, "input")
                if not path.exists():
                    os.mkdir(path)

                # Make user path if not exists
                path = Path(path, str(interaction.user.id))
                if not path.exists():
                    os.mkdir(path)
                simc_file = Path(path, f"{now}.simc")
                self.log.debug(simc_file)
                with open(simc_file, "w", encoding="ascii") as file:
                    file.write(_self.character.value)

                await self._run(
                    interaction,
                    str(interaction.user.id),
                    [],
                    weights,
                    sim_type,
                    now,
                    str(simc_file),
                )

        await ctx.response.send_modal(CharacterModal())

    @simc_command.command(name="run_armoury")
    @app_commands.autocomplete(character=get_characters, sim_type=get_type)
    async def run_armory(
        self,
        ctx: discord.Interaction,
        character: str,
        weights: bool = True,
        sim_type: str = "Patchwerk",
    ):
        """Run a character via the armoury."""
        if len(c_s := character.split("-")) != 3:
            await ctx.response.send_message(
                "Character must be in format `CharName-Server-Region`, eg: `Infurnal-Draenor-US`"
            )
            return
        async with self.config.user(ctx.user)() as conf:
            if not conf.get("characters"):
                conf["characters"] = []
            if character not in conf.get("characters"):
                conf["characters"].append(character)
        c_s.reverse()
        armory_string = f'armory={",".join(c_s)}'
        await self._run(ctx, character, [armory_string], weights, sim_type)

    async def _run(
        self,
        ctx: discord.Interaction,
        name: str,
        args: list,
        weights: bool,
        sim_type: str,
        now: Optional[int] = None,
        simc_file: Optional[str] = None,
    ):
        # Load settings if not loaded
        if not getattr(self, "k8s", None):
            await self._load_settings()
        # Get values from settings
        async with self.config.k8s_settings() as settings:
            location = settings.get("file_location")
            url = settings.get("base_url")
        # Get the timestamp to save the file as
        now = now or int(time())
        # Get the optional arguments
        if weights:
            args.append("calculate_scale_factors=1")
        args.extend([f"fight_style={sim_type}", "iterations=10000", "target_error=0.1"])

        # Make sure the path exists to save to.
        folder = Path(f"{location}{name}")
        if not folder.exists():
            os.mkdir(folder)

        # Add the args
        file_name = f"{now}.html"
        args.append(f"html={str(folder)}/{file_name}")
        full_name = f"{name}-{now}".lower()
        if simc_file:
            args.append(simc_file)

        # Run the job
        job: V1Job = cast(V1Job, self.k8s.create_job_object(full_name, args))

        # Give output
        await ctx.response.send_message("Started. This may take a few minutes.")
        await self.k8s.watch(job)

        path = f"{name}/{file_name}"
        html_file = Path(folder, file_name)
        if not html_file.exists():
            self.log.error("the file didn't exist! %s", html_file)
            await ctx.followup.send("There was an error saving your file. Try again.")
            return False
        pawn_string = None
        if weights:
            with open(html_file) as file:
                for line in file:
                    if "( Pawn" in line:
                        pawn_string = line
        await ctx.followup.send(
            f"[Done! Click here for your results.]({url}{path})"
            + (f"\nYour pawn string is `{pawn_string}`" if pawn_string else "")
        )
        return True
