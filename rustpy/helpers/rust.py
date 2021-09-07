from __future__ import annotations

import re
from dataclasses import dataclass

import aiohttp

from rustpy.constants import RustChannel, RustEdition, RustMode, URLs
from typing import ClassVar, Literal, Type, TypeVar, TYPE_CHECKING

if TYPE_CHECKING:
    from aiohttp import ClientResponse, ClientSession
    from rustpy import RustPy
    R = TypeVar('R')

__all__ = (
    'RustPlaygroundClient',
    'RustPlaygroundResponse',
    'RustPlaygroundHTTPException',
)


class RustPlaygroundClient:
    """Makes requests to https://play.rust-lang.org"""

    FN_MAIN_REGEX: ClassVar[re.Pattern[str]] = re.compile(
        r'fn\s+main\s*\([^)]*\)\s*(->\s*[^{]+\s*)?{.*\}',
        re.S
    )

    def __init__(self, *, bot: RustPy) -> None:
        self.bot: RustPy = bot

    @property
    def session(self) -> ClientSession:
        return self.bot.session

    @staticmethod
    async def _raise_http_error(response: ClientResponse) -> None:
        fmt = f'{response.status} {response.reason}'
        try:
            if text := await response.text(encoding='utf-8'):
                fmt += ': ' + text
        except aiohttp.ClientConnectionError:
            pass

        raise RustPlaygroundHTTPException(fmt)

    async def _request(self, route: str, *, cls: Type[R] = None, **kwargs) -> R:
        async with self.session.post(URLs.RUST_PLAYGROUND + route, **kwargs) as response:
            if not response.ok:
                await self._raise_http_error(response)

            data = await response.json(encoding='utf-8')
            cls = cls or RustPlaygroundResponse
            return cls(**data)

    async def execute(
        self,
        code: str,
        *,
        channel: RustChannel = RustChannel.NIGHTLY,
        edition: RustEdition = RustEdition.E2018,
        mode: RustMode = RustMode.DEBUG,
    ) -> RustPlaygroundResponse:
        payload = {
            'backtrace': False,
            'channel': channel.name.lower(),
            'code': code,
            'crateType': 'bin' if self.FN_MAIN_REGEX.search(code) else 'lib',
            'edition': edition.name[1:],
            'mode': mode.name.lower(),
            'tests': False,
        }

        async with self.session.post(URLs.RUST_PLAYGROUND + 'execute', json=payload) as response:
            if response.status == 500:
                return RustPlaygroundResponse(
                    success=False,
                    stdout='',
                    stderr='Timed out.',
                )

            if not response.ok:
                await self._raise_http_error(response)

            data = await response.json(encoding='utf-8')
            return RustPlaygroundResponse(**data)

    async def format(self, code: str, *, edition: RustEdition = RustEdition.E2018) -> RustFormatResponse:
        payload = {
            'code': code,
            'edition': edition.name[1:],
        }

        return await self._request('format', cls=RustFormatResponse, json=payload)

    async def clippy(self, code: str, *, edition: RustEdition.E2018) -> RustPlaygroundResponse:
        payload = {
            'code': code,
            'crateType': 'bin' if self.FN_MAIN_REGEX.search(code) else 'lib',
            'edition': edition.name[1:],
        }

        return await self._request('clippy', json=payload)

    async def expand_macros(self, code: str, *, edition: RustEdition.E2018) -> RustPlaygroundResponse:
        payload = {
            'code': code,
            'edition': edition.name[1:],
        }

        return await self._request('macro-expansion', json=payload)


@dataclass
class RustPlaygroundResponse:
    success: bool
    stdout: str
    stderr: str

    def __str__(self) -> str:
        if self.success:
            return self.stdout

        return f'{self.stderr}\n{self.stdout}'

    def __repr__(self) -> str:
        return f'<{self.__class__.__name__} success={self.success}>'


@dataclass
class RustFormatResponse(RustPlaygroundResponse):
    code: str

    def __str__(self) -> str:
        if not self.success:
            return f'{self.stdout}\n{self.stderr}\n{self.code}'.strip('\n')

        return self.code


class RustPlaygroundHTTPException(Exception):
    """Raised when an error occurs while requesting to the playground."""
