import asyncio

from discord.ext import commands
from jishaku.codeblocks import codeblock_converter

from rustpy.core import Cog, Context, RustPy
from rustpy.helpers.common import get_code, send_output


class RustCommands(Cog, name='Rust'):
    """Rust related commands."""

    @commands.command('rust', aliases=('rs', 'ferris'))
    @commands.cooldown(2, 7, commands.BucketType.user)
    @commands.max_concurrency(1, commands.BucketType.user)
    async def run_rust(self, ctx: Context, *, code: codeblock_converter = None) -> None:
        """Compiles and runs a rust program.

        See `{PREFIX}help eval` on information on supplying code.
        Behavior of this command can be configured through `{RPEFIX}settings rust`.
        """
        code = await get_code(ctx, code)
        settings = await ctx.db.get_settings(ctx.author.id)

        async def _persist_reaction():
            await asyncio.sleep(14)
            await ctx.try_reaction('\U0001f550')

        task = ctx.bot.loop.create_task(_persist_reaction())

        async with ctx.typing():
            response = await ctx.bot.rust.execute(
                code,
                channel=settings.rust_channel,
                edition=settings.rust_edition,
                mode=settings.rust_mode,
            )

        if not task.done():
            task.cancel()

        reaction = '\U0001f44d' if response.success else '\u274c'
        ctx.bot.loop.create_task(ctx.try_reaction(reaction))

        await send_output(ctx, str(response), syntax='rs')

    _rustfmt_aliases = 'rust-format', 'rsformat', 'rsfmt', 'rfmt', 'cargo-fmt', 'cargofmt'

    @commands.command('rustfmt', aliases=_rustfmt_aliases)
    @commands.cooldown(2, 7, commands.BucketType.user)
    @commands.max_concurrency(1, commands.BucketType.user)
    async def rustfmt(self, ctx: Context, *, code: codeblock_converter = None) -> None:
        """Formats the given Rust code using `cargo fmt`.

        See `{PREFIX}help eval` on information on supplying code.
        Behavior of this command can be configured through `{PREFIX}settings rust`.
        """
        code = await get_code(ctx, code)
        settings = await ctx.db.get_settings(ctx.author.id)

        async with ctx.typing():
            response = await ctx.bot.rust.format(code, edition=settings.rust_edition)

        reaction = '\U0001f44d' if response.success else '\u274c'
        ctx.bot.loop.create_task(ctx.try_reaction(reaction))

        await send_output(ctx, str(response), syntax='rs')

    _expand_macros_aliases = (
        'expandmacros',
        'expand-macro',
        'expandmacro',
        'macros',
        'emacros',
        'macro-expansion',
        'macroexpansion',
    )

    @commands.command('expand-macros', aliases=_expand_macros_aliases)
    @commands.cooldown(2, 7, commands.BucketType.user)
    @commands.max_concurrency(1, commands.BucketType.user)
    async def expand_macros(self, ctx: Context, *, code: codeblock_converter = None) -> None:
        """Expands all Rust macros in the given code.

        See `{PREFIX}help eval` on information on supplying code.
        Behavior of this command can be configured through `{PREFIX}settings rust`.
        """
        code = await get_code(ctx, code)
        settings = await ctx.db.get_settings(ctx.author.id)

        async with ctx.typing():
            response = await ctx.bot.rust.expand_macros(code, edition=settings.rust_edition)

        reaction = '\U0001f44d' if response.success else '\u274c'
        ctx.bot.loop.create_task(ctx.try_reaction(reaction))

        await send_output(ctx, str(response), syntax='rs')


def setup(bot: RustPy) -> None:
    bot.add_cog(RustCommands(bot))
