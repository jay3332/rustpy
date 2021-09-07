from __future__ import annotations

import functools

import discord
from discord.ext import commands

from rustpy.core import Cog, Context, RustPy
from rustpy.constants import DEFAULT_GROUP_KWARGS, RustChannel, RustEdition, RustMode

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rustpy.core.database import SettingsEntry
    RustEnum = Union[RustChannel, RustEdition, RustMode]


class RustSettingsButton(discord.ui.Button['RustSettingsView']):
    def __init__(self, choice: RustEnum, *, key: str, row: int) -> None:
        self.key: str = key
        self.choice: RustEnum = choice
        self.toggled: bool = False

        super().__init__(label=choice.name.title(), row=row)

    def enable(self) -> None:
        self.toggled = True
        self.style = discord.ButtonStyle.primary

    def disable(self) -> None:
        self.toggled = False
        self.style = discord.ButtonStyle.secondary

    async def callback(self, interaction: discord.Interaction) -> None:
        if self.toggled:
            return await interaction.response.defer()

        self.view.save_button.disabled = False

        for button in self.view.children:
            if isinstance(button, self.__class__) and button.key == self.key and button.toggled:
                button.disable()

        self.enable()

        self.view.modifications[self.key] = self.choice
        await interaction.response.edit_message(view=self.view)


class RustSettingsView(discord.ui.View):
    def __init__(self, ctx: Context, entry: SettingsEntry) -> None:
        self.ctx: Context = ctx
        self.entry: SettingsEntry = entry
        self.modifications: dict[str, RustEnum] = {}

        super().__init__(timeout=None)
        self._add_buttons()

    @property
    def bot(self) -> RustPy:
        return self.ctx.bot

    def _add_buttons(self) -> None:
        _disabled_button = functools.partial(discord.ui.Button, disabled=True)

        def fill(*, label: str, key: str, row: int, enum: RustEnum) -> None:
            self.add_item(_disabled_button(label=label, row=row))

            for entry in enum._member_map_.values():
                self.add_item(button := RustSettingsButton(entry, key=key, row=row))

                if getattr(self.entry, 'rust_' + key) is entry:
                    button.enable()

        fill(label='Rust Channel', key='channel', row=0, enum=RustChannel)
        fill(label='Rust Edition', key='edition', row=1, enum=RustEdition)
        fill(label='Rust Mode', key='mode', row=2, enum=RustMode)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user == self.ctx.author

    def _disable_all_buttons(self) -> None:
        for button in self.children:
            if isinstance(button, discord.ui.Button) and not button.disabled:
                button.disabled = True

    @discord.ui.button(label='Save', style=discord.ButtonStyle.success, row=3, disabled=True)
    async def save_button(self, _, interaction: discord.Interaction) -> None:
        self._disable_all_buttons()
        await self.ctx.db.update_rust_settings(self.ctx.author.id, **self.modifications)
        await interaction.response.edit_message(content='Saved!', view=self)
        self.stop()

    @discord.ui.button(label='Cancel', style=discord.ButtonStyle.danger, row=3)
    async def cancel_button(self, _, interaction: discord.Interaction) -> None:
        self._disable_all_buttons()
        await interaction.response.edit_message(content='Cancelled', view=self)
        self.stop()


class MiscCommands(Cog, name='Miscellaneous'):
    """Miscellaneous commands that don't really belong anywhere else."""

    @commands.group('settings', aliases=('config', 'cfg'), **DEFAULT_GROUP_KWARGS)
    async def settings(self, ctx: Context) -> None:
        """Configure your settings for this bot.

        Currently, only Rust settings exist (See `{PREFIX}settings rust`).
        """

    @settings.command('rust', aliases=('rs', 'ferris'))
    @commands.max_concurrency(1, commands.BucketType.user)
    async def settings_rust(self, ctx: Context) -> None:
        """Configure Rust-related settings for this bot.

        ``Rust Channel``: The channel/build of rust you want to use.
        ``Rust Edition``: The rust edition you want to use.
        ``Rust Mode``: The optimization/release mode you want to use.

        These settings will apply to following commands:
        - `rust`
        - `rustfmt`
        - `expand-macros`
        """
        entry = await ctx.db.get_settings(ctx.author.id)
        view = RustSettingsView(ctx, entry=entry)

        await ctx.reply(content='Press "Save" to save your changes.', view=view)
        await view.wait()


def setup(bot: RustPy) -> None:
    bot.add_cog(MiscCommands(bot))
