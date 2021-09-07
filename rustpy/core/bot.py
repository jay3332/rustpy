import os

import aiohttp
import discord

from dotenv import load_dotenv
from discord.ext import commands
from jishaku.flags import Flags

from rustpy.core.database import Database
from rustpy.core.models import Context
from rustpy.helpers import MystBinClient, PistonClient, RustPlaygroundClient, TIOClient

from typing import TYPE_CHECKING

load_dotenv()

Flags.NO_UNDERSCORE = True
Flags.NO_DM_TRACEBACK = True
Flags.HIDE = True

INTENTS = discord.Intents(
    guilds=True,
    invites=True,
    messages=True,
    reactions=True,
    typing=True
)

ALLOWED_MENTIONS = discord.AllowedMentions(
    users=True,
    roles=False,
    everyone=False,
    replied_user=False
)

__all__ = (
    'RustPy',
)


class RustPy(commands.Bot):
    session: aiohttp.ClientSession
    db: Database

    mystbin: MystBinClient
    piston: PistonClient
    rust: RustPlaygroundClient
    tio: TIOClient

    def __init__(self) -> None:
        super().__init__(
            command_prefix=self.__class__._get_prefix,
            case_insensitive=True,
            owner_id=414556245178056706,
            description='suspicious',
            max_messages=10,
            strip_after_prefix=True,
            intents=INTENTS,
            allowed_mentions=ALLOWED_MENTIONS,
            status=discord.Status.dnd,
            activity=discord.Activity(name='with code', type=discord.ActivityType.playing),
            chunk_guilds_at_startup=False
        )
        self.setup()

    async def _get_prefix(self, _message: discord.Message) -> str:
        return '.'  # Too lazy to make a decent prefix system so here you go

    def load_extensions(self) -> None:
        self.load_extension('jishaku')

        for file in os.listdir('./rustpy/extensions'):
            if file.endswith('.py') and not file.startswith('_'):
                self.load_extension(f'rustpy.extensions.{file[:-3]}')

    async def setup_database(self) -> None:
        self.db = Database(loop=self.loop)

    def setup(self) -> None:
        self.session = aiohttp.ClientSession()

        self.mystbin = MystBinClient(bot=self)
        self.piston = PistonClient(bot=self)
        self.rust = RustPlaygroundClient(bot=self)
        self.tio = TIOClient(bot=self)

        self.loop.create_task(self._dispatch_first_ready())
        self.load_extensions()

        self.loop.run_until_complete(self.setup_database())

    async def process_commands(self, message: discord.Message) -> None:
        if message.author.bot:
            return

        ctx = await self.get_context(message, cls=Context)
        await self.invoke(ctx)

    async def _dispatch_first_ready(self) -> None:
        await self.wait_until_ready()
        self.dispatch('first_ready')

    async def on_first_ready(self) -> None:
        print(f'Logged in as {self.user} (ID: {self.user.id})')

    async def on_message(self, message: discord.Message) -> None:
        await self.process_commands(message)

    async def on_command_error(self, ctx: commands.Context, error: Exception) -> None:
        if isinstance(error, commands.CommandNotFound):
            return

        error = getattr(error, 'original', error)

        if isinstance(error, discord.NotFound) and error.code == 10062:
            return

        await ctx.send(error)
        raise error

    def run(self) -> None:
        try:
            super().run(os.environ['TOKEN'])
        except KeyError:
            raise ValueError('The "TOKEN" environment variable must be supplied.')

    async def close(self) -> None:
        await self.session.close()
        await super().close()
