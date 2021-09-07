import asyncio

import discord
from discord.ext import commands
from jishaku.codeblocks import codeblock_converter

from rustpy.core import Cog, Context, RustPy
from rustpy.helpers import PistonFile, PistonResponse, PistonRuntime, PistonRuntimeNotFound
from rustpy.helpers.common import get_code, send_output

from typing import Optional


class PistonRuntimeConverter(commands.Converter):
    async def convert(self, ctx: commands.Context, argument: str) -> PistonRuntime:
        try:
            return await ctx.bot.piston.get_runtime(argument)
        except PistonRuntimeNotFound:
            raise commands.BadArgument('Piston runtime with that name not found.')


class OtherCommands(Cog, name='Other'):
    """Other programming-related commands that don't apply to just Python or Rust."""

    @commands.command('run', aliases=['piston', 'exec', 'execute', 'e'])
    @commands.cooldown(2, 6, commands.BucketType.user)
    @commands.max_concurrency(1, commands.BucketType.user)
    async def run_piston(
        self,
        ctx: Context,
        runtime: Optional[PistonRuntimeConverter],
        *,
        code: codeblock_converter = None
    ) -> None:
        """Executes the given code with the given runtime.

        This is the main general evaluation command for this bot,
        however the alternative `{PREFIX}tio` command can be used too.

        For Rust evaluation, `{PREFIX}rust` can also be used.

        Code can be supplied in a few ways:

        - Normally (Raw text)
        - By codeblock. If the runtime is not given, it will default to
        the syntax highlighting for the codeblock.
        - By text-based file. You can either pass it in as an attachment,
        or reply to the message containing the file.
        - Using the [Mystb.in](https://mystb.in/) paste-bin. Argument should be the URL that
        leads to your paste.

        All code is executed through [Piston](https://github.com/engineer-man/piston/).
        """
        if runtime is None:
            if code is not None:
                runtime = await PistonRuntimeConverter().convert(ctx, code.language or '')
            else:
                raise commands.BadArgument(
                    'Missing runtime/language. '
                    f'See `{ctx.clean_prefix}run runtimes` to see all possible runtimes.\n'
                    f'Alternatively, you can use `{ctx.clean_prefix}tio` for more language options.'
                )

        code: str = await get_code(ctx, code)
        runtime: PistonRuntime

        file = PistonFile(f'run.{runtime.language}', code)

        async def _persist_reaction():
            await asyncio.sleep(5)
            await ctx.try_reaction('\U0001f550')

        task = ctx.bot.loop.create_task(_persist_reaction())

        async with ctx.typing():
            output: PistonResponse = await ctx.bot.piston.execute(runtime, [file])

        if not task.done():
            task.cancel()

        # Compile-time errors get a warning reaction
        if output.compile_output and output.compile_output.code != 0:
            reaction = '\u26a0'

        # SIGKILL means it was probably exited from timeout (E.g. while true)
        elif output.run_output.signal == 'SIGKILL':
            reaction = '\U0001f501'

        # If the exit code is None, there was probably some other signal
        elif output.run_output.code is None:
            reaction = '\u2754'

        # Runtime errors get an X reaction
        elif output.run_output.code != 0:
            reaction = '\u274c'

        # No errors get a thumbs up
        else:
            reaction = '\U0001f44d'

        ctx.bot.loop.create_task(ctx.try_reaction(reaction))

        fmt = f'{output.output}\n\nExit code: {output.code}'
        await send_output(ctx, fmt, syntax=runtime.language)


def setup(bot: RustPy) -> None:
    bot.add_cog(OtherCommands(bot))
