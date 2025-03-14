from dataclasses import dataclass
from datetime import datetime
from typing import List, Union
from urllib.parse import quote

from discord import Embed
from jsonpath_ng import parse


@dataclass
class GameInfo:
    """Info about the free games."""

    game_id: str
    title: str
    desc: str
    url: str
    start_date: Union[datetime, None]
    end_date: Union[datetime, None]
    thumbnail_url: str

    @classmethod
    def make_from_response(cls, response) -> List["GameInfo"]:
        """Builds a list of this class from the Epic free games response"""
        games = (
            response.get("data", {})
            .get("Catalog")
            .get("searchStore", {})
            .get("elements", [])
        )
        infos = []
        for game in games:
            parser_now = parse(
                "promotions.promotionalOffers.[*].promotionalOffers.[*].discountSetting.discountPercentage"
            )
            # Maybe do future stuff at some point?
            # parser_future = parse("promotions.upcomingPromotionalOffers.[*].promotionalOffers.[*].discountSetting.discountPercentage")

            if not parser_now or 0 not in [g.value for g in parser_now.find(game)]:
                continue

            start_dates = [
                g.context.context.value.get("startDate").split(".")[0]
                for g in parser_now.find(game)
                if g.context.context.value.get("startDate")
            ]
            end_dates = [
                g.context.context.value.get("endDate").split(".")[0]
                for g in parser_now.find(game)
                if g.context.context.value.get("endDate")
            ]

            image_urls = [
                image.get("url")
                for image in game.get("keyImages")
                if image.get("type") == "Thumbnail" and image.get("url")
            ]
            image_url = image_urls[0] if image_urls else None

            slug = game.get("productSlug")
            if not slug:
                parser_slug = parse("offerMappings.[*].pageType")
                slugs = [
                    ps.context.value.get("pageSlug")
                    for ps in parser_slug.find(game)
                    if ps.value == "productHome"
                ]
                if len(slugs) > 0:
                    slug = slugs[0]
            info_dict = {
                "game_id": game.get("id"),
                "title": f"Free on Epic: {game.get('title')}",
                "desc": game.get("description"),
                "url": f"https://store.epicgames.com/en-US/p/{slug}",
                "start_date": datetime.strptime(start_dates[0], "%Y-%m-%dT%H:%M:%S")
                if start_dates
                else None,
                "end_date": datetime.strptime(end_dates[0], "%Y-%m-%dT%H:%M:%S")
                if end_dates
                else None,
                "thumbnail_url": image_url,
            }

            info = cls(**info_dict)
            infos.append(info)
        return infos

    def embed(self):
        """Return an embed"""
        embed = Embed(title=self.title, description=self.desc, url=self.url)
        if self.thumbnail_url:
            embed.set_image(url=quote(self.thumbnail_url, safe=":/?&=)"))
        if self.end_date:
            end_footer = f"Ends on {self.end_date.strftime(r'%Y-%m-%d')}"
        else:
            end_footer = "No end time given."

        if self.start_date:
            start_footer = f"Started on {self.start_date.strftime(r'%Y-%m-%d')}"
        else:
            start_footer = "No Start Time given."
        embed.set_footer(text=f"{start_footer}\n{end_footer}")
        return embed
