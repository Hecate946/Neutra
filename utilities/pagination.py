import asyncio
import discord
from discord.ext.commands import Paginator as CommandPaginator
from discord.ext import menus
from utilities import default
from collections import namedtuple

from secret import constants

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
        def_dict_emoji = {'\N{BLACK LEFT-POINTING DOUBLE TRIANGLE WITH VERTICAL BAR}\ufe0f':
                          EmojiB("<:backward2:816457785167314987>", menus.First(0),
                                 "Goes to the first page."),

                          '\N{BLACK LEFT-POINTING TRIANGLE}\ufe0f':
                          EmojiB("<:backward:816458218145579049>", menus.First(1),
                                 "Goes to the previous page."),

                          '\N{BLACK RIGHT-POINTING TRIANGLE}\ufe0f':
                          EmojiB("<:forward:816458167835820093>", menus.Last(0),
                                 "Goes to the next page."),

                          '\N{BLACK RIGHT-POINTING DOUBLE TRIANGLE WITH VERTICAL BAR}\ufe0f':
                          EmojiB("<:forward2:816457685905440850>", menus.Last(1),
                                 "Goes to the last page."),

                          '\N{BLACK SQUARE FOR STOP}\ufe0f':
                          EmojiB("<:trash:816463111958560819>", menus.Last(4),
                                 "Remove this message.")
                          }
        self.dict_emoji = def_dict_emoji
        for emoji in self.buttons:
            callback = self.buttons[emoji].action
            if emoji.name not in self.dict_emoji:
                continue
            new_but = self.dict_emoji[emoji.name]
            new_button = menus.Button(new_but.emoji, callback, position=new_but.position)
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

    @menus.button('<:info:817625979014348830>', position=menus.Last(5))
    async def show_help(self, payload):
        """`shows this message`"""
        embed = discord.Embed(title='Menu Help', color=constants.embed)
        messages = []
        for (emoji, button) in self.buttons.items():
            messages.append(f'{emoji}: `{button.action.__doc__}`')

        embed.add_field(name='Reaction Functions', value='\n'.join(messages), inline=False)
        #embed.set_footer(text=f'Previously viewed page: {self.current_page + 1}')
        await self.message.edit(content=None, embed=embed)

        async def go_back_to_current_page():
            await asyncio.sleep(60.0)
            await self.show_page(self.current_page)

        self.bot.loop.create_task(go_back_to_current_page())

    @menus.button("<:1234:816460247777411092>", position=menus.Last(3))
    async def numbered_page(self, payload):
        """`type a page number to jump to`"""
        channel = self.message.channel
        author_id = payload.user_id
        to_delete = []
        to_delete.append(await channel.send('Enter the page number to jump to.'))

        def message_check(m):
            return m.author.id == author_id and \
                   channel == m.channel and \
                   m.content.isdigit()

        try:
            msg = await self.bot.wait_for('message', check=message_check, timeout=30.0)
        except asyncio.TimeoutError:
            to_delete.append(await channel.send('Timer ended.'))
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
    # TODO COME BACK TO THIS TOMORROW
    def __init__(self, entries, **kwargs):
        per_page = kwargs.get("per_page", 12)
        self.title = kwargs.get("title", discord.Embed.Empty)
        self.desc = kwargs.get("description", discord.Embed.Empty)
        self.desc_head = kwargs.get("desc_head", None)
        self.desc_foot = kwargs.get("desc_foot", None)
        self.color = kwargs.get("color", constants.embed)
        super().__init__(entries, per_page=per_page)
        self.embed = discord.Embed()

    def enforce_limit(self, value, max):
        if not type(value) is str:
            return value
        return (value[:max-3]+"...") if len(value) > max else value

    async def format_page(self, menu, entries):
        self.embed.clear_fields()
        self.embed.description = discord.Embed.Empty

        for key, value in entries:
            self.embed.add_field(name=key, value=value, inline=False)

        maximum = self.get_max_pages()
        if maximum > 1:
            text = f'Page {menu.current_page + 1}/{maximum} ({len(self.entries)} entries)'
            self.embed.set_footer(text=text)

        self.embed.title=self.title
        self.embed.color=self.color
        if self.desc_head and self.desc_foot and self.desc is not discord.Embed.Empty:
            self.embed.description=f"{self.desc_head}\n{self.enforce_limit(self.desc, DESC_LIMIT)}\n{self.desc_foot}"
        else:
            self.embed.description = self.enforce_limit(self.desc, DESC_LIMIT)
        return self.embed

class TextPageSource(menus.ListPageSource):
    def __init__(self, text, *, prefix="```", suffix='```', max_size=2000):
        pages = CommandPaginator(prefix=prefix, suffix=suffix, max_size=max_size - 200)
        for line in text.split('\n'):
            pages.add_line(line)

        super().__init__(entries=pages.pages, per_page=1)

    async def format_page(self, menu, content):
        maximum = self.get_max_pages()
        if maximum > 1:
            return f'{content}\nPage {menu.current_page + 1}/{maximum}'
        return content

class SimplePageSource(menus.ListPageSource):
    def __init__(self, entries, *, per_page=12):
        super().__init__(entries, per_page=per_page)
        self.initial_page = True

    async def format_page(self, menu, entries):
        pages = []
        if to_index is False:
            for entry in entries:
                pages.append(f'{entry}')
        else:
            for index, entry in enumerate(entries, start=menu.current_page * self.per_page):
                pages.append(f'{index + 1}. {entry}')

        maximum = self.get_max_pages()
        if maximum > 1:
            footer = f'Page {menu.current_page + 1}/{maximum} ({len(self.entries)} entries)'
            menu.embed.set_footer(text=footer)

        if self.initial_page and self.is_paginating():
            pages.append('')
            pages.append('Need help? React with <:info:817625979014348830> for more info.')
            self.initial_page = False

        formatted_pages = []
        for i in pages:
            formatted_pages.append(str(i).replace("[","").replace("]","").replace("'",""))

        menu.embed.description = '\n'.join(formatted_pages)
        return menu.embed

class SimplePages(MainMenu):
    """A simple pagination session reminiscent of the old Pages interface.
    Basically an embed with some normal formatting.
    """

    def __init__(self, entries, **kwargs):
        super().__init__(SimplePageSource(entries, per_page=kwargs.get("per_page", 12)))
        self.embed = discord.Embed(color=constants.embed)
        global to_index
        to_index = kwargs.get("index", True)


class EmbedLimits:
    Field = 1024
    Name = 256
    Title = 256
    Description = 2048
    Fields = 25
    Total = 6000


class Paginator:
    def __init__(self, title=None, description=None, page_count=True, init_page=True, color=constants.embed):
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
            embed.set_footer(text=f'{idx+1}/{total}')

    def add_page(self, title=None, description=None, color=constants.embed, paginate_description=False):
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
                description_ = description[:EmbedLimits.Description]
                overflow = description[EmbedLimits.Description:]
                description = description_
            else:
                description = description[:EmbedLimits.Description]
        

        self._pages.append(discord.Embed(title=title, description=description, color=constants.embed))
        self._current_page += 1
        self._fields = 0
        self._char_count = 0
        self._char_count += len(title) if title else 0
        self._char_count += len(description) if description else 0
        self.title = title
        self.description = description
        self.color = color

        if overflow:
            self.add_page(title=title, description=overflow, color=color, paginate_description=True)

    def edit_page(self, title=None, description=None, color=constants.embed):
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
        self.color = constants.embed

    def _add_field(self):
        if not self._current_field:
            return

        if not self._current_field['value']:
            self._current_field['value'] = 'Emptiness'

        self.pages[self._current_page].add_field(**self._current_field)
        self._fields += 1
        self._char_count += len(self._current_field['name']) + len(self._current_field['value'])
        self._current_field = None

    def add_field(self, name, value='', inline=False):
        if self._current_field is not None and self._fields < 25:
            self._add_field()

        name = name[:EmbedLimits.Title]
        leftovers = value[EmbedLimits.Field:]
        value = value[:EmbedLimits.Field]
        length = len(name) + len(value)

        if self._fields == 25:
            self._pages.append(discord.Embed(title=self.title))
            self._current_page += 1
            self._fields = 0
            self._char_count = len(self.title)
            if self._current_field is not None:
                self._add_field()

        elif length + self._char_count > EmbedLimits.Total:
            self._pages.append(discord.Embed(title=self.title))
            self._current_page += 1
            self._fields = 0
            self._char_count = len(self.title)

        self._current_field = {'name': name, 'value': value, 'inline': inline}

        if leftovers:
            self.add_field(name, leftovers, inline=inline)

    def add_to_field(self, value):
        v = self._current_field['value']
        if len(v) + len(value) > EmbedLimits.Field:
            self.add_field(self._current_field['name'], value)
        else:
            self._current_field['value'] += value