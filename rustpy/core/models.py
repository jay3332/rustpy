from __future__ import annotations

import discord
from discord.ext import commands

from typing import TYPE_CHECKING, Union

if TYPE_CHECKING:
    from rustpy.core.bot import RustPy
    from rustpy.core.database import Database

    EmojiType = Union[Emoji, PartialEmoji, str]

__all__ = (
    'Cog',
    'Context',
)


class Cog(commands.Cog):
    def __init__(self, bot: RustPy) -> None:
        self.bot: RustPy = bot
        bot.loop.create_task(discord.utils.maybe_coroutine(self.__setup__))

    def __setup__(self) -> Union[None, Awaitable[None]]:
        ...


class Context(commands.Context):
    bot: RustPy

    @property
    def db(self) -> Database:
        return self.bot.db

    async def try_reaction(self, reaction: EmojiType, *, message: discord.Message = None) -> bool:
        message = message or self.message
        try:
            await message.add_reaction(reaction)
            return True
        except discord.HTTPException:
            return False
