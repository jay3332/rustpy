import ast
from contextlib import suppress

from discord.ext import commands
from rustpy.core import Cog, RustPy

__all__ = (
    'PythonCommands',
)


class PythonCommands(Cog, name='Python'):
    """Python-related commands."""

    def _insert_print(self, body: list[ast.AST]) -> None:
        """Inserts a print statement if there isn't already one."""
        with suppress(AttributeError):
            if isinstance(body[-1], ast.Expr):
                placeholder = ast.parse('print(0)').body[0].value
                if body[-1].value.__class__ is placeholder.__class__:  # ast.Call
                    if body[-1].value.func.id == 'print':
                        return

                placeholder.args[0] = body[-1].value
                body[-1].value = placeholder
                ast.fix_missing_locations(body[-1])

            if isinstance(body[-1], ast.If):
                self._insert_print(body[-1].body)
                self._insert_print(body[-1].orelse)

            if isinstance(body[-1], (ast.With, ast.AsyncWith)):
                self._insert_print(body[-1].body)


def setup(bot: RustPy) -> None:
    bot.add_cog(PythonCommands(bot))
