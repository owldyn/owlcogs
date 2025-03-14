import asyncio
import logging
from collections import defaultdict
from dataclasses import dataclass

import requests
from redbot.core import Config, commands
from redbot.core.bot import Red

log = logging.getLogger("owlcogs.define")


@dataclass
class Definition:
    definition: str | None
    part_of_speech: str | None
    example: str | None
    source: str | None


class Define(commands.Cog):
    default_global_settings = {"settings": {}}

    def __init__(self, bot):
        """set it up"""
        super().__init__()
        self.bot: Red = bot
        self.config = Config.get_conf(self, 4007)
        self.config.register_global(**self.default_global_settings)

    @commands.command()
    async def define(self, ctx: commands.Context, *words: str):
        phrase = " ".join(words)
        definition_response = await asyncio.get_event_loop().run_in_executor(
            None,
            requests.get,
            f"https://api.dictionaryapi.dev/api/v2/entries/en/{phrase}",
        )
        if not definition_response.ok:
            await ctx.reply(f"Definition for {phrase} not found.", mention_author=False)
            return
        part_of_speech: defaultdict[str, list[Definition]] = defaultdict(list)
        for result in definition_response.json():
            for meaning in result.get("meanings") or []:
                for definition in meaning.get("definitions") or []:
                    part_of_speech[meaning.get("partOfSpeech")].append(
                        Definition(
                            definition.get("definition"),
                            meaning.get("partOfSpeech"),
                            definition.get("example"),
                            next(iter(result.get("sourceUrls")), None),
                        )
                    )
        message = ""

        def format_definition(d: Definition):
            return (
                f"- {d.definition}\n"
                + "-# " + (f"[Source]({d.source}) " if d.source else "")
                + (f"Example: {d.example}\n" if d.example else "")
            )

        for pos, definitions in part_of_speech.items():
            message += f"### {pos.title()}\n" + "\n".join(
                format_definition(d).rstrip() for d in definitions[:5]
            ) + "\n"

        await ctx.reply(message.strip(), mention_author=False, suppress_embeds=True)
