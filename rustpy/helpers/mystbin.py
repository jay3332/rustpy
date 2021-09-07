from __future__ import annotations

import aiohttp
import textwrap

from rustpy.constants import URLs
from typing import NamedTuple, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from rustpy import RustPy

__all__ = (
    'MystBinClient',
    'MystBinHTTPException',
    'MystBinPasteNotFound',
    'MystBinPaste',
)


class MystBinClient:
    """Makes requests to https://mystb.in."""

    def __init__(self, *, bot: RustPy) -> None:
        self.bot: RustPy = bot

    @property
    def session(self) -> aiohttp.ClientSession:
        return self.bot.session

    @staticmethod
    async def _raise_http_error(response: aiohttp.ClientResponse) -> None:
        fmt = f'{response.status} {response.reason}'
        try:
            if text := await response.text(encoding='utf-8'):
                fmt += ': ' + text
        except aiohttp.ClientConnectionError:
            pass

        raise MystBinHTTPException(fmt)

    async def get_paste(self, code: str) -> MystBinPaste:
        async with self.session.get(
            URLs.MYSTBIN + '/' + code,
            timeout=aiohttp.ClientTimeout(15)
        ) as response:
            if response.status == 404:
                raise MystBinPasteNotFound(code)

            if not response.ok:
                await self._raise_http_error(response)

            data = await response.json(encoding='utf-8')

            return MystBinPaste(
                content=textwrap.dedent(data['data']),
                code=code,
                syntax=data['syntax']
            )

    async def create_paste(self, content: str, syntax: Optional[str] = None) -> MystBinPaste:
        writer = aiohttp.MultipartWriter()
        writer.append(content).set_content_disposition('form-data', name='data')

        metadata = {"meta": [{"index": 0, "syntax": syntax}]}
        writer.append_json(metadata).set_content_disposition('form-data', name='meta')

        async with self.session.post(
            URLs.MYSTBIN,
            data=writer,
            timeout=aiohttp.ClientTimeout(15)
        ) as response:
            if not response.ok:
                await self._raise_http_error(response)

            data = await response.json(encoding='utf-8')
            code = data['pastes'][0]['id']

            return MystBinPaste(
                content=content,
                code=code,
                syntax=syntax
            )


class MystBinPaste(NamedTuple):
    # There could be more fields but this is all we need
    content: str
    code: str
    syntax: str = ''

    def __str__(self) -> str:
        return self.content

    def __repr__(self) -> str:
        return f'<MystBinPaste id={self.code!r} syntax={self.syntax!r}>'

    @property
    def url(self) -> str:
        suffix = '.' + self.syntax if self.syntax else ''
        return 'https://mystb.in/' + self.code + suffix

    def to_codeblock(self) -> str:
        if not self.syntax:
            return f'```{self.content}```'

        return f'```{self.syntax}\n{self.content}```'


class MystBinHTTPException(Exception):
    """Raised when an HTTP-related error occurs when requesting to MystBin."""


class MystBinPasteNotFound(MystBinHTTPException):
    """Raised when a MystBin paste is not found."""

    def __init__(self, *, code: str) -> None:
        self.code: str = code
        super().__init__(f'MystBin paste with ID {code[:16]!r} does not exist.')
