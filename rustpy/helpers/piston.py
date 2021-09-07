from __future__ import annotations

from rustpy.constants import URLs
from typing import Iterable, NamedTuple, Optional, TYPE_CHECKING, TypedDict

if TYPE_CHECKING:
    from aiohttp import ClientResponse, ClientSession
    from rustpy import RustPy

__all__ = (
    'PistonClient',
    'PistonRuntime',
    'PistonFile',
    'PistonOutput',
    'PistonResponse',
    'PistonException',
    'PistonHTTPException',
    'PistonRuntimeNotFound',
)


class PistonClient:
    """Makes requests to Piston API."""

    def __init__(self, *, bot: RustPy) -> None:
        self.bot: RustPy = bot
        self._cached_runtimes: dict[str, PistonRuntime] = {}

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

        raise PistonHTTPException(fmt)

    async def runtimes(self) -> dict[str, PistonRuntime]:
        if len(self._cached_runtimes):
            return self._cached_runtimes

        async with self.session.get(URLs.PISTON + 'runtimes') as response:
            if not response.ok:
                await self._raise_http_error(response)

            data = await response.json(encoding='utf-8')

            self._cached_runtimes = res = {
                entry['language']: PistonRuntime(**entry)
                for entry in data
            }
            return res

    async def get_runtime(self, runtime: str, /) -> PistonRuntime:
        runtime = runtime.lower()
        runtimes = await self.runtimes()

        try:
            return runtimes[runtime]
        except KeyError:
            for rt in runtimes.values():
                if runtime in rt.aliases:
                    return rt

        raise PistonRuntimeNotFound(f'Runtime {runtime!r} not found.')

    # noinspection PyShadowingBuiltins
    async def execute(
        self,
        runtime: PistonRuntime,
        files: Iterable[PistonFile],
        *,
        input: str = '',
        args: Iterable[str] = (),
        compile_timeout: float = 10.0,
        run_timeout: float = 5.0,
        compile_memory_limit: int = -1,
        run_memory_limit: int = -1,
    ) -> PistonResponse:
        payload = {
            **runtime.to_json(),
            'files': [file.to_json() for file in files],
            'input': str(input),
            'args': list(args),
            'compile_timeout': int(compile_timeout * 1000),
            'run_timeout': int(run_timeout * 1000),
            'compile_memory_limit': compile_memory_limit,
            'run_memory_limit': run_memory_limit,
        }

        async with self.session.post(URLs.PISTON + 'execute', json=payload) as response:
            if not response.ok and response.status != 400:  # 400's handled below
                await self._raise_http_error(response)

            data = await response.json(encoding='utf-8')
            if response.status == 400:
                raise PistonRuntimeNotFound(data['message'])

            compile_output = PistonOutput(**data['compile']) if 'compile' in data else None

            return PistonResponse(
                runtime=runtime,
                run_output=PistonOutput(**data['run']),
                compile_output=compile_output,
            )


class PistonRuntimeJSON(TypedDict):
    language: str
    version: str


class PistonRuntime(NamedTuple):
    language: str
    version: str
    aliases: list[str]
    runtime: Optional[str] = None

    def __repr__(self) -> str:
        return f'<PistonRuntime language={self.language!r} version={self.version!r}>'

    def to_json(self) -> PistonRuntimeJSON:
        return {
            'language': self.language,
            'version': self.version,
        }


class PistonFileJSON(TypedDict):
    name: str
    content: str


class PistonFile(NamedTuple):
    name: str
    content: str

    def to_json(self) -> PistonFileJSON:
        return {
            'name': self.name,
            'content': self.content,
        }


class PistonOutput(NamedTuple):
    stdout: str
    stderr: str
    output: str
    code: Optional[int]
    signal: Optional[int]

    def __str__(self) -> str:
        return self.output

    def __repr__(self) -> str:
        return f'<PistonOutput output={self.output!r} exit_code={self.code}>'


class PistonResponse(NamedTuple):
    runtime: PistonRuntime
    run_output: PistonOutput
    compile_output: Optional[PistonOutput] = None

    def __str__(self) -> str:
        if self.compile_output:
            return f'{self.compile_output!s}\n{self.run_output!s}'

        return str(self.run_output)

    def __repr__(self) -> str:
        return f'<PistonResponse runtime={self.runtime!r} ' \
               f'run={self.run_output!r} compile={self.compile_output}>'

    @property
    def code(self) -> int:
        if self.compile_output and self.compile_output.code != 0:
            return self.compile_output.code

        return self.run_output.code

    @property
    def output(self) -> str:
        return str(self)


class PistonException(Exception):
    """Raised when an error related to Piston occurs."""


class PistonHTTPException(PistonException):
    """Raised when an error occurs when requesting to Piston."""


class PistonRuntimeNotFound(PistonException):
    """Raised when a runtime is not found."""
