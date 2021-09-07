from __future__ import annotations

import copy
import re

import discord
from discord.ext.commands import BadArgument

from jishaku.codeblocks import Codeblock
from typing import Union, TYPE_CHECKING

if TYPE_CHECKING:
    from rustpy.core import Context

__all__ = (
    'get_code',
)

CODEBLOCK_REGEX: re.Pattern[str] = re.compile(
    r'\s*```((?P<language>[a-zA-Z0-9]+)\s*\n)?(?P<code>.+)```',
    re.S
)

MYSTBIN_REGEX: re.Pattern[str] = re.compile(
    r'https?://mystb.in/(?P<code>[A-Za-z]{3,64})(\.(?P<syntax>[A-Za-z0-9]+))?/?'
)


async def get_code(ctx: Context, code: Union[Codeblock, str, None] = None) -> str:
    if code is not None:
        if isinstance(code, Codeblock):
            code = code.content

        code: str

        if match := MYSTBIN_REGEX.fullmatch(code):
            paste = await ctx.bot.mystbin.get_paste(match.group('code'))
            code = paste.content

    if not code:
        if attachments := ctx.message.attachments:
            target = attachments[0]
            if target.size > 1_000_000:  # 1 MB | TODO: Make this a config variable
                raise BadArgument('Attachment sizes cannot surpass 1 MB.')

            raw = await target.read()
            try:
                code = raw.decode('utf-8')  # Maybe errors='ignore' here but not sure if that's safe
            except UnicodeDecodeError:
                raise BadArgument('Attachment does not have readable code.')
            else:
                return code

        if reference := ctx.message.reference:
            if resolved := reference.resolved:
                if match := CODEBLOCK_REGEX.search(resolved.content):
                    _, language, code = match.groups()
                    return await get_code(
                        ctx,
                        Codeblock(language, code.strip('\n'))
                    )

                ctx_clone = copy.copy(ctx)
                ctx_clone.message = resolved
                return await get_code(ctx_clone, code)

        raise BadArgument('Please supply a block of code.')

    return code


async def send_output(ctx: Context, output: str, **kwargs) -> discord.Message:
    syntax = kwargs.pop('syntax', 'txt')
    sanitized_output = output.replace('```', '`\u200b``')

    if len(sanitized_output) > 1986 or output.count('\n') > 50:
        paste = await ctx.bot.mystbin.create_paste(output, syntax=syntax)
        return await ctx.send(f'Output can be viewed at <{paste.url}>', **kwargs)

    return await ctx.send(f'```{syntax}\n{sanitized_output}```')
