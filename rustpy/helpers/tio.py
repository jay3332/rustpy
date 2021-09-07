from __future__ import annotations

from rustpy.constants import URLs
from zlib import compress

from typing import ClassVar, TYPE_CHECKING, Union

if TYPE_CHECKING:
    from aiohttp import ClientSession
    from rustpy import RustPy

__all__ = (
    'TIOClient',
    'TIOResponse',
    'TIOException',
    'TIOHTTPException',
    'TIOLanguageUnavailable',
)


class TIOClient:
    """Makes requests to tio.run."""

    LANGUAGE_SHORTCUTS: ClassVar[dict[str, str]] = {
        'python': 'python38pr',
        'python3': 'python38pr',
        'python3.7': 'python3',
        'py': 'python38pr',
        'py3': 'python38pr',
        'py3.7': 'python3',
        'py2': 'python2',
        'py1': 'python1',
        'pypy': 'python3-pypy',
        'cython': 'python3-cython',
        'pyx': 'python3-cython',
        'javascript': 'javascript-node',
        'js': 'javascript-node',
        'node': 'javascript-node',
        'babel': 'javascript-babel-node',
        'javascript8': 'javascript-v8',
        'js8': 'javascript-v8',
        'ts': 'typescript',
        'rs': 'rust',
        'ferris-lang': 'rust',
        'sh': 'bash',
        'shell': 'bash',
        'asm': 'assembly',
        'c#': 'cs',
        'c++': 'cpp',
        'csharp': 'cs',
        'f#': 'fs',
        'nimrod': 'nim',
        'q#': 'qs',
        'jl': 'julia',
        'hs': 'haskell',
    }

    def __init__(self, *, bot: RustPy) -> None:
        self.bot: RustPy = bot
        self._cached_languages: list[str] = None

    @property
    def session(self) -> ClientSession:
        return self.bot.session

    async def languages(self) -> list[str]:
        if self._cached_languages:
            return self._cached_languages

        async with self.session.get(URLs.TIO_LANGUAGES) as response:
            if not response.ok:
                return

            json = await response.json()
            self._cached_languages = res = list(json.keys())
            return res

    async def _get_language(self, language: str) -> str:
        language = language.lower()

        if language not in await self.languages():
            if lang := self.LANGUAGE_SHORTCUTS.get(language):
                return lang

            start = language[:3]
            raise TIOLanguageUnavailable(language, close_matches=[
                lang for lang in self._cached_languages if lang.startswith(start)
            ][:10])
        else:
            return language

    def _encode(self, key: str, value: Union[list[str], str] = None) -> bytes:
        if not value:
            return bytes()

        if isinstance(value, str):
            return bytes(
                f'F{key}\x00{len(bytes(value, encoding="utf-8"))}\x00{value}\x00',
                encoding='utf-8'
            )

        payload = ['V' + key, str(len(value))] + value
        return bytes('\x00'.join(payload) + '\x00', encoding='utf-8')

    def _compress_payload(self, payload: dict[str, Union[str, list[str]]]) -> bytes:
        encoded = b''.join(
            map(self._encode, payload.keys(), payload.values())
        )
        return compress(encoded + b'R', 9)[2:-4]

    async def request(self, payload: dict[str, Union[str, list[str]]]) -> str:
        payload = self._compress_payload(payload)

        async with self.session.post(URLs.TIO_RUN, data=payload) as response:
            if not response.ok:
                raise TIOHTTPException(f'{response.status}: {response.reason}')

            data = await response.read()
            return data.decode('utf-8')

    # noinspection PyShadowingBuiltins
    async def run(
        self,
        code: str,
        language: str,
        *,
        input: str = '',
        flags: list[str] = None,
        options: list[str] = None,
        args: list[str] = None
    ) -> TIOResponse:
        language = await self._get_language(language)

        payload = {
            'lang': [language],
            '.code.tio': code,
            '.input.tio': input,
            'TIO_CFLAGS': flags or [],
            'TIO_OPTIONS': options or [],
            'args': args or []
        }

        return TIOResponse(await self.request(payload), language=language)


class TIOResponse:
    real_time: float
    user_time: float
    sys_time: float
    cpu_share: float  # In percent

    def __init__(self, raw: str, *, language: str) -> None:
        self.language: str = language
        self.token: str = raw[:16]
        self.raw: str = raw[16:-16]

        chunks = self.raw.split('\n')

        self.real_time, self.user_time, self.sys_time, self.cpu_share = [
            self._parse_chunk(chunk) for chunk in chunks[-5:-1]
        ]

        try:
            self.exit_code: int = int(chunks[-1][11:])
        except ValueError:
            self.exit_code = 0

        self.output: str = '\n'.join(chunks[:-6])

    @property
    def successful(self) -> bool:
        return self.exit_code == 0

    def _parse_chunk(self, chunk: str, /) -> str:
        return float(chunk[11:-2])

    def __repr__(self) -> None:
        return f'<TIOResponse language={self.language!r} exit_code={self.exit_code}>'


class TIOException(Exception):
    """Raised when an error related to TIO occurs."""


class TIOHTTPException(TIOException):
    """Raised when an HTTP related error related to TIO occurs."""


class TIOLanguageUnavailable(TIOException):
    def __init__(self, query: str, *, close_matches: list[str] = None) -> None:
        self.query: str = query
        self.close_matches: list[str] = close_matches or []

        if self.close_matches:
            first_3 = '`, `'.join(self.close_matches[:3])
            extra = f'\nDid you mean: `{first_3}`?'
        else:
            extra = ''

        super().__init__(f'Language `{self.query[:24]}` is not available.' + extra)
