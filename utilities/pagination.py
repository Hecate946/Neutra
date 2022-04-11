import asyncio
from collections import namedtuple

import discord
from discord.ext import menus
from discord.ext.commands import Paginator as CommandPaginator

from settings import constants
from utilities import cleaner

from core import bot

EMBED_COLOR = bot.mode.EMBED_COLOR

# Embed limits
TITLE_LIMIT = 256
DESC_LIMIT = 2048
AUTHOR_LIMIT = 256
FOOTER_LIMIT = 2048
FIELDS_LIMIT = 25
FIELD_NAME_LIMIT = 256
FIELD_VALUE_LIMIT = 1024
TOTAL_lIMIT = 6000


class MainMenu(menus.MenuPages):
    def __init__(self, source):
        super().__init__(source=source, check_embeds=False)
        EmojiB = namedtuple("EmojiB", "emoji position explain")
        def_dict_emoji = {
            "\N{BLACK LEFT-POINTING DOUBLE TRIANGLE WITH VERTICAL BAR}\ufe0f": EmojiB(
                constants.emotes["backward2"],
                menus.First(0),
                "Goes to the first page.",
            ),
            "\N{BLACK LEFT-POINTING TRIANGLE}\ufe0f": EmojiB(
                constants.emotes["backward"],
                menus.First(1),
                "Goes to the previous page.",
            ),
            "\N{BLACK RIGHT-POINTING TRIANGLE}\ufe0f": EmojiB(
                constants.emotes["forward"], menus.Last(0), "Goes to the next page."
            ),
            "\N{BLACK RIGHT-POINTING DOUBLE TRIANGLE WITH VERTICAL BAR}\ufe0f": EmojiB(
                constants.emotes["forward2"],
                menus.Last(1),
                "Goes to the last page.",
            ),
            "\N{BLACK SQUARE FOR STOP}\ufe0f": EmojiB(
                constants.emotes["trash"], menus.Last(4), "Remove this message."
            ),
        }
        self.dict_emoji = def_dict_emoji
        for emoji in self.buttons:
            callback = self.buttons[emoji].action
            if emoji.name not in self.dict_emoji:
                continue
            new_but = self.dict_emoji[emoji.name]
            new_button = menus.Button(
                new_but.emoji, callback, position=new_but.position
            )
            del self.dict_emoji[emoji.name]
            self.dict_emoji[new_but.emoji] = new_but
            self.add_button(new_button)
            self.remove_button(emoji)

    async def finalize(self, timed_out):
        try:
            if timed_out:
                await self.message.clear_reactions()
            else:
                await self.message.delete()
        except discord.HTTPException:
            pass

    @menus.button(constants.emotes["info"], position=menus.Last(5))
    async def show_help(self, payload):
        """`shows this message`"""
        embed = discord.Embed(title="Menu Help", color=EMBED_COLOR)
        messages = []
        for (emoji, button) in self.buttons.items():
            messages.append(f"{emoji}: `{button.action.__doc__}`")

        embed.add_field(
            name="Reaction Functions", value="\n".join(messages), inline=False
        )
        # embed.set_footer(text=f'Previously viewed page: {self.current_page + 1}')
        await self.message.edit(content=None, embed=embed)

        async def go_back_to_current_page():
            await asyncio.sleep(60.0)
            await self.show_page(self.current_page)

        self.bot.loop.create_task(go_back_to_current_page())

    @menus.button(constants.emotes["1234button"], position=menus.Last(3))
    async def numbered_page(self, payload):
        """`type a page number to jump to`"""
        channel = self.message.channel
        author_id = payload.user_id
        to_delete = []
        to_delete.append(await channel.send("Enter the page number to jump to."))

        def message_check(m):
            return (
                m.author.id == author_id
                and channel == m.channel
                and m.content.isdigit()
            )

        try:
            msg = await self.bot.wait_for("message", check=message_check, timeout=30.0)
        except asyncio.TimeoutError:
            to_delete.append(await channel.send("Timer ended."))
            await asyncio.sleep(5)
        else:
            page = int(msg.content)
            to_delete.append(msg)
            await self.show_checked_page(page - 1)

        try:
            await channel.delete_messages(to_delete)
        except Exception:
            pass


class FieldPageSource(menus.ListPageSource):
    """A page source that requires (field_name, field_value) tuple items."""

    def __init__(self, entries, **kwargs):
        per_page = kwargs.get("per_page", 12)
        self.title = kwargs.get("title", None)
        self.desc = kwargs.get("description", None)
        self.desc_head = kwargs.get("desc_head", None)
        self.desc_foot = kwargs.get("desc_foot", None)
        self.color = kwargs.get("color", EMBED_COLOR)
        super().__init__(entries, per_page=per_page)
        self.embed = discord.Embed()

    def enforce_limit(self, value, max):
        if not type(value) is str:
            return value
        return (value[: max - 3] + "...") if len(value) > max else value

    async def format_page(self, menu, entries):
        self.embed.clear_fields()
        self.embed.description = None

        for key, value in entries:
            self.embed.add_field(name=key, value=value, inline=False)

        maximum = self.get_max_pages()
        if maximum > 1:
            text = (
                f"Page {menu.current_page + 1}/{maximum} ({len(self.entries)} entries)"
            )
            self.embed.set_footer(text=text)

        self.embed.title = self.title
        self.embed.color = self.color
        if self.desc_head and self.desc_foot and self.desc is not None:
            self.embed.description = f"{self.desc_head}\n{self.enforce_limit(self.desc, DESC_LIMIT)}\n{self.desc_foot}"
        else:
            self.embed.description = self.enforce_limit(self.desc, DESC_LIMIT)
        return self.embed


class TextPageSource(menus.ListPageSource):
    def __init__(self, text, *, prefix="```", suffix="```", max_size=2000):
        pages = CommandPaginator(prefix=prefix, suffix=suffix, max_size=max_size - 200)
        text = cleaner.clean_all(text)
        for line in text.split("\n"):
            try:
                pages.add_line(line)
            except RuntimeError:  # Line too long
                continue

        super().__init__(entries=pages.pages, per_page=1)

    async def format_page(self, menu, content):
        maximum = self.get_max_pages()
        if maximum > 1:
            return f"{content}\nPage {menu.current_page + 1}/{maximum}"
        return content


class LinePageSource(menus.ListPageSource):
    def __init__(self, text, *, prefix="```", suffix="```", max_size=2000, lines=2000):
        pages = CommandPaginator(prefix=prefix, suffix=suffix, max_size=max_size - 200)
        text = cleaner.clean_all(text)
        index = 0
        for line in text.split("\n"):
            index += 1
            try:
                pages.add_line(line)
            except RuntimeError:  # Line too long
                continue
            if index == lines:
                index = 0
                pages.close_page()

        super().__init__(entries=pages.pages, per_page=1)

    async def format_page(self, menu, content):
        maximum = self.get_max_pages()
        if maximum > 1:
            return f"{content}\nPage {menu.current_page + 1}/{maximum}"
        return content


class SimplePageSource(menus.ListPageSource):
    def __init__(self, entries, **kwargs):
        super().__init__(entries, per_page=kwargs.get("per_page", 12))
        self.initial_page = True
        self.desc_head = kwargs.get("desc_head", None)
        self.desc_foot = kwargs.get("desc_foot", None)
        self.index = kwargs.get("index", True)

    async def format_page(self, menu, entries):
        pages = []
        if self.index is False:
            for entry in entries:
                pages.append(f"{entry}")
        else:
            for index, entry in enumerate(
                entries, start=menu.current_page * self.per_page
            ):
                pages.append(f"{index + 1}. {entry}")

        maximum = self.get_max_pages()
        if maximum > 1:
            footer = (
                f"Page {menu.current_page + 1}/{maximum} ({len(self.entries)} entries)"
            )
            menu.embed.set_footer(text=footer)

        if self.initial_page and self.is_paginating():
            pages.append("")
            menu.embed.add_field(
                name="Need help?",
                value="React with <:info:827428282001260544> for more info.",
            )
            self.initial_page = False

        if self.desc_head and self.desc_foot:
            menu.embed.description = self.desc_head + "\n".join(pages) + self.desc_foot
        else:
            menu.embed.description = "\n".join(pages)
        return menu.embed


class SimplePages(MainMenu):
    def __init__(self, entries, **kwargs):
        super().__init__(
            SimplePageSource(
                entries,
                per_page=kwargs.get("per_page", 12),
                desc_head=kwargs.get("desc_head", None),
                desc_foot=kwargs.get("desc_foot", None),
                index=kwargs.get("index", True),
            )
        )
        self.embed = discord.Embed(color=kwargs.get("color", EMBED_COLOR))


class TextPages(MainMenu):
    def __init__(self, text, *, prefix="```", suffix="```", max_size=2000):
        super().__init__(
            TextPageSource(text=text, prefix=prefix, suffix=suffix, max_size=max_size)
        )


class Paginator:
    def __init__(
        self,
        title=None,
        description=None,
        page_count=True,
        init_page=True,
        color=EMBED_COLOR,
    ):
        """
        Args:
            title: title of the embed
            description: description of the embed
            page_count: whether to show page count in the footer or not
            init_page: create a page in the init method
        """
        self.color = color
        self._fields = 0
        self._pages = []
        self.title = title
        self.description = description
        self.set_page_count = page_count
        self._current_page = -1
        self._char_count = 0
        self._current_field = None
        if init_page:
            self.add_page(title, description)

    @property
    def pages(self):
        return self._pages

    def finalize(self):
        self._add_field()
        if not self.set_page_count:
            return

        total = len(self.pages)
        for idx, embed in enumerate(self.pages):
            embed.set_footer(text=f"{idx+1}/{total}")

    def add_page(
        self,
        title=None,
        description=None,
        color=EMBED_COLOR,
        paginate_description=False,
    ):
        """
        Args:
            title:
            description:
            paginate_description:
                If set to true will split description based on max description length
                into multiple embeds
        """
        title = title or self.title
        description = description or self.description
        overflow = None
        if description:
            if paginate_description:
                description_ = description[:DESC_LIMIT]
                overflow = description[DESC_LIMIT:]
                description = description_
            else:
                description = description[:DESC_LIMIT]

        self._pages.append(
            discord.Embed(title=title, description=description, color=EMBED_COLOR)
        )
        self._current_page += 1
        self._fields = 0
        self._char_count = 0
        self._char_count += len(title) if title else 0
        self._char_count += len(description) if description else 0
        self.title = title
        self.description = description
        self.color = color

        if overflow:
            self.add_page(
                title=title,
                description=overflow,
                color=color,
                paginate_description=True,
            )

    def edit_page(self, title=None, description=None, color=EMBED_COLOR):
        page = self.pages[self._current_page]
        if title:
            self._char_count -= len(str(title))
            page.title = str(title)
            self.title = title
            self._char_count += len(title)
        if description:
            self._char_count -= len(str(description))
            page.description = str(description)
            self.description = description
            self._char_count += len(description)
        self.color = EMBED_COLOR

    def _add_field(self):
        if not self._current_field:
            return

        if not self._current_field["value"]:
            self._current_field["value"] = "Emptiness"

        self.pages[self._current_page].add_field(**self._current_field)
        self._fields += 1
        self._char_count += len(self._current_field["name"]) + len(
            self._current_field["value"]
        )
        self._current_field = None

    def add_field(self, name, value="", inline=False):
        if self._current_field is not None and self._fields < 25:
            self._add_field()

        name = name[:TITLE_LIMIT]
        leftovers = value[FIELD_VALUE_LIMIT:]
        value = value[:FIELD_VALUE_LIMIT]
        length = len(name) + len(value)

        if self._fields == 25:
            self._pages.append(discord.Embed(title=self.title))
            self._current_page += 1
            self._fields = 0
            self._char_count = len(self.title)
            if self._current_field is not None:
                self._add_field()

        elif length + self._char_count > TOTAL_lIMIT:
            self._pages.append(discord.Embed(title=self.title))
            self._current_page += 1
            self._fields = 0
            self._char_count = len(self.title)

        self._current_field = {"name": name, "value": value, "inline": inline}

        if leftovers:
            self.add_field(name, leftovers, inline=inline)

    def add_to_field(self, value):
        v = self._current_field["value"]
        if len(v) + len(value) > FIELD_VALUE_LIMIT:
            self.add_field(self._current_field["name"], value)
        else:
            self._current_field["value"] += value
