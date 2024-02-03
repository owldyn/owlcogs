from functools import wraps
from typing import Any, Callable, TypeVar

import discord

T = TypeVar("T", bound=Callable[..., Any])


def is_owner():
    def decorator(inner):
        @wraps(inner)
        async def wrapper(self, ctx, *args, **kwargs):
            if ctx.user.id not in self.bot.owner_ids:
                await ctx.response.send_message(
                    "You do not have permission to do that.", ephemeral=True
                )
                return
            return await inner(self, ctx, *args, **kwargs)

        return wrapper

    return decorator
