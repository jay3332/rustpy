from enum import Enum

__all__ = (
    'DEFAULT_GROUP_KWARGS',
    'URLs',
    'RustChannel',
    'RustEdition',
    'RustMode',
)

DEFAULT_GROUP_KWARGS = dict(case_insensitive=True, invoke_without_command=True)


class URLs:
    TIO_RUN: str = "https://tio.run/cgi-bin/run/api/"
    TIO_LANGUAGES: str = "https://tio.run/languages.json"
    PISTON: str = "https://emkc.org/api/v2/piston/"
    MYSTBIN: str = "https://mystb.in/api/pastes"
    RUST_PLAYGROUND: str = "https://play.rust-lang.org/"


class RustEdition(Enum):
    E2015 = 0
    E2018 = 1
    E2021 = 2


class RustChannel(Enum):
    STABLE  = 0
    BETA    = 1
    NIGHTLY = 2


class RustMode(Enum):
    DEBUG   = 0
    RELEASE = 1
