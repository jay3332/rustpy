from __future__ import annotations

import asyncio
import asyncpg
import os
import platform

from dataclasses import dataclass
from rustpy.constants import RustChannel, RustEdition, RustMode

from typing import Any, Awaitable, overload, Union

__all__ = (
    'Database',
    'SettingsEntry',
)


class _Database:
    _internal_pool: asyncpg.Pool

    def __init__(self, *, loop: asyncio.AbstractEventLoop = None) -> None:
        self.loop: asyncio.AbstractEventLoop = loop or asyncio.get_event_loop()
        self.loop.create_task(self._connect())

    async def _connect(self) -> asyncpg.Pool:
        env_entry = 'BETA_DATABASE_PASSWORD' if platform.system() == 'Windows' else 'DATABASE_PASSWORD'

        self._internal_pool = await asyncpg.create_pool(
            host='localhost',
            user='postgres',
            database='rustpy',
            password=os.environ[env_entry]
        )
        await self._run_initial_query()

    async def _run_initial_query(self) -> None:
        def wrapper() -> str:
            with open('schema.sql') as fp:
                return fp.read()

        await self.execute(await asyncio.to_thread(wrapper))

    @overload
    def acquire(self, *, timeout: float = None) -> Awaitable[asyncpg.Connection]:
        ...

    def acquire(self, *, timeout: float = None) -> asyncpg.pool.PoolAcquireContext:
        return self._internal_pool.acquire(timeout=timeout)

    def execute(self, query: str, *args: Any, timeout: float = None) -> Awaitable[str]:
        return self._internal_pool.execute(query, *args, timeout=timeout)

    def fetch(self, query: str, *args: Any, timeout: float = None) -> Awaitable[list[asyncpg.Record]]:
        return self._internal_pool.fetch(query, *args, timeout=timeout)

    def fetchrow(self, query: str, *args: Any, timeout: float = None) -> Awaitable[asyncpg.Record]:
        return self._internal_pool.fetchrow(query, *args, timeout=timeout)

    def fetchval(self, query: str, *args: Any, column: Union[str, int] = 0, timeout: float = None) -> Awaitable[Any]:
        return self._internal_pool.fetchval(query, *args, column=column, timeout=timeout)


class Database(_Database):
    def __init__(self, *, loop: asyncio.AbstractEventLoop = None) -> None:
        super().__init__(loop=loop)
        self._settings_cache: dict[int, SettingsEntry] = {}

    async def setup(self, user_id: int) -> None:
        query = """
                INSERT INTO settings (user_id) VALUES ($1)
                ON CONFLICT DO NOTHING;
                """
        await self.execute(query, user_id)

    async def fetch_settings(self, user_id: int) -> SettingsEntry:
        query = 'SELECT * FROM settings WHERE user_id = $1;'

        if record := await self.fetchrow(query, user_id):
            entry = SettingsEntry(
                user_id=user_id,
                rust_channel=RustChannel(record['preferred_rust_channel']),
                rust_edition=RustEdition(record['preferred_rust_edition']),
                rust_mode=RustMode(record['preferred_rust_mode']),
            )
            self._settings_cache[user_id] = entry
            return entry
        else:
            await self.setup(user_id)
            return await self.fetch_settings(user_id)

    async def get_settings(self, user_id: int) -> SettingsEntry:
        try:
            return self._settings_cache[user_id]
        except KeyError:
            return await self.fetch_settings(user_id)

    async def update_rust_settings(
        self,
        user_id: int,
        *,
        channel: RustChannel = None,
        edition: RustEdition = None,
        mode: RustMode = None,
    ) -> None:
        entry = await self.get_settings(user_id)

        if entry.rust_channel is channel:
            channel = None

        if entry.rust_edition is edition:
            edition = None

        if entry.rust_mode is mode:
            mode = None

        if not any((channel, edition, mode)):
            return

        query = """
                UPDATE 
                    settings 
                SET 
                    preferred_rust_channel = $1, 
                    preferred_rust_edition = $2, 
                    preferred_rust_mode = $3
                WHERE 
                    user_id = $4
                RETURNING *;
                """

        new = await self.fetchrow(
            query,
            (channel or entry.rust_channel).value,
            (edition or entry.rust_edition).value,
            (mode or entry.rust_mode).value,
            user_id
        )

        entry.rust_channel = RustChannel(new['preferred_rust_channel'])
        entry.rust_edition = RustEdition(new['preferred_rust_edition'])
        entry.rust_mode = RustMode(new['preferred_rust_mode'])


@dataclass
class SettingsEntry:
    user_id: int
    rust_channel: RustChannel
    rust_edition: RustEdition
    rust_mode: RustMode
