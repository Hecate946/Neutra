import asyncio
import math
import os
import random
import textwrap
from collections import namedtuple

import discord
from discord.ext import menus
from discord.ext.commands import Paginator as CommandPaginator

from settings import constants

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
                "<:backward2:816457785167314987>",
                menus.First(0),
                "Goes to the first page.",
            ),
            "\N{BLACK LEFT-POINTING TRIANGLE}\ufe0f": EmojiB(
                "<:backward:816458218145579049>",
                menus.First(1),
                "Goes to the previous page.",
            ),
            "\N{BLACK RIGHT-POINTING TRIANGLE}\ufe0f": EmojiB(
                "<:forward:816458167835820093>", menus.Last(0), "Goes to the next page."
            ),
            "\N{BLACK RIGHT-POINTING DOUBLE TRIANGLE WITH VERTICAL BAR}\ufe0f": EmojiB(
                "<:forward2:816457685905440850>",
                menus.Last(1),
                "Goes to the last page.",
            ),
            "\N{BLACK SQUARE FOR STOP}\ufe0f": EmojiB(
                "<:trash:816463111958560819>", menus.Last(4), "Remove this message."
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

    @menus.button("<:info:827428282001260544>", position=menus.Last(5))
    async def show_help(self, payload):
        """`shows this message`"""
        embed = discord.Embed(title="Menu Help", color=constants.embed)
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

    @menus.button("<:1234:816460247777411092>", position=menus.Last(3))
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
        return (value[: max - 3] + "...") if len(value) > max else value

    async def format_page(self, menu, entries):
        self.embed.clear_fields()
        self.embed.description = discord.Embed.Empty

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
        if self.desc_head and self.desc_foot and self.desc is not discord.Embed.Empty:
            self.embed.description = f"{self.desc_head}\n{self.enforce_limit(self.desc, DESC_LIMIT)}\n{self.desc_foot}"
        else:
            self.embed.description = self.enforce_limit(self.desc, DESC_LIMIT)
        return self.embed


class TextPageSource(menus.ListPageSource):
    def __init__(self, text, *, prefix="```", suffix="```", max_size=2000):
        pages = CommandPaginator(prefix=prefix, suffix=suffix, max_size=max_size - 200)
        for line in text.split("\n"):
            pages.add_line(line)

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

        formatted_pages = []
        for i in pages:
            formatted_pages.append(
                str(i).replace("[", "").replace("]", "").replace("'", "")
            )

        if self.desc_head and self.desc_foot:
            menu.embed.description = (
                self.desc_head + "\n".join(formatted_pages) + self.desc_foot
            )
        else:
            menu.embed.description = "\n".join(formatted_pages)
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
        self.embed = discord.Embed(color=kwargs.get("color", constants.embed))


class Confirmation(menus.Menu):
    def __init__(self, msg):
        super().__init__(timeout=30.0, delete_message_after=True)
        self.msg = msg
        self.result = None

    async def send_initial_message(self, ctx, channel):
        return await channel.send(self.msg)

    @menus.button(constants.emotes["success"])
    async def do_confirm(self, payload):
        self.result = True
        self.stop()

    @menus.button(constants.emotes["failed"])
    async def do_deny(self, payload):
        self.result = False
        self.stop()

    async def prompt(self, ctx):
        await self.start(ctx, wait=True)
        return self.result


class Message:
    def __init__(self, **kwargs):
        # Creates a new message - with an optional setup dictionary
        self.max_chars = 2000
        self.pm_after = kwargs.get("pm_after", 1)  # -1 to disable, 0 to always pm
        self.force_pm = kwargs.get("force_pm", False)
        self.header = kwargs.get("header", "")
        self.footer = kwargs.get("footer", "")
        self.pm_react = kwargs.get("pm_react", "📬")
        self.message = kwargs.get("message", None)
        self.file = kwargs.get("file", None)  # Accepts a file path
        self.max_pages = 0
        self.delete_after = kwargs.get("delete_after", None)

    def _get_file(self, file_path):
        if not os.path.exists(file_path):
            return None
        # Path exists, let's get the extension if there is one
        ext = file_path.split(".")
        fname = "Upload." + ext[-1] if len(ext) > 1 else "Upload"
        file_handle = discord.File(fp=file_path, filename=fname)
        return (file_handle, fname)

    async def _send_message(self, ctx, message, pm=False, file_path=None):
        # Helper method to send embeds to their proper location
        send_file = None
        if not file_path is None:
            dfile = self._get_file(file_path)
            if not dfile:
                # File doesn't exist...
                try:
                    await ctx.send_or_reply(
                        "An error occurred!\nThe file specified couldn't be sent :("
                    )
                except Exception:
                    # We tried...
                    pass
                return None
            else:
                # Setup our file
                send_file = dfile[0]
        if (
            pm is True
            and type(ctx) is discord.ext.commands.Context
            and not ctx.channel == ctx.author.dm_channel
        ):
            # More than 2 pages - try to dm
            try:
                message = await ctx.author.send(
                    message, file=send_file, delete_after=self.delete_after
                )
                await ctx.message.add_reaction(self.pm_react)
                return message
            except discord.Forbidden:
                if self.force_pm:
                    # send an error message
                    try:
                        await ctx.send_or_reply(
                            "An error occurred!\nCould not dm this message to you :("
                        )
                    except Exception:
                        # We tried...
                        pass
                    return None
                pass
        return await ctx.send_or_reply(
            message, file=send_file, delete_after=self.delete_after
        )

    async def send(self, ctx):
        if not ctx or not self.message or not len(self.message):
            return
        text_list = textwrap.wrap(
            self.message,
            self.max_chars - len(self.header) - len(self.footer),
            break_long_words=True,
            replace_whitespace=False,
        )

        # Only pm if our self.pm_after is above -1
        to_pm = len(text_list) > self.pm_after if self.pm_after > -1 else False
        page_count = 1
        for m in text_list:
            if self.max_pages > 0 and page_count > self.max_pages:
                break
            message = await self._send_message(
                ctx, self.header + m + self.footer, to_pm
            )
            # Break if things didn't work
            if not message:
                return None
            page_count += 1
        return message


class Embed:
    def __init__(self, **kwargs):
        # Set defaults
        self.title_max = kwargs.get("title_max", 256)
        self.desc_max = kwargs.get("desc_max", 2048)
        self.field_max = kwargs.get("field_max", 25)
        self.fname_max = kwargs.get("fname_max", 256)
        self.fval_max = kwargs.get("fval_max", 1024)
        self.foot_max = kwargs.get("foot_max", 2048)
        self.auth_max = kwargs.get("auth_max", 256)
        self.total_max = kwargs.get("total_max", 6000)
        # Creates a new embed - with an option setup dictionary
        self.pm_after = kwargs.get("pm_after", 10)
        self.force_pm = kwargs.get("force_pm", False)
        self.pm_react = kwargs.get("pm_react", "📬")
        self.title = kwargs.get("title", None)
        self.page_count = kwargs.get("page_count", False)
        self.url = kwargs.get("url", None)
        self.description = kwargs.get("description", None)
        self.image = kwargs.get("image", None)
        self.footer = kwargs.get("footer", None)
        # self.footer_text = kwargs.get("footer_text", discord.Embed.Empty)
        # self.footer_icon = kwargs.get("footer_icon", discord.Embed.Empty)
        self.thumbnail = kwargs.get("thumbnail", None)
        self.author = kwargs.get("author", None)
        self.fields = kwargs.get("fields", [])
        self.file = kwargs.get("file", None)  # Accepts a file path
        self.delete_after = kwargs.get("delete_after", None)
        self.colors = [
            discord.Color.teal(),
            discord.Color.dark_teal(),
            discord.Color.green(),
            discord.Color.dark_green(),
            discord.Color.blue(),
            discord.Color.dark_blue(),
            discord.Color.purple(),
            discord.Color.dark_purple(),
            discord.Color.magenta(),
            discord.Color.dark_magenta(),
            discord.Color.gold(),
            discord.Color.dark_gold(),
            discord.Color.orange(),
            discord.Color.dark_orange(),
            discord.Color.red(),
            discord.Color.dark_red(),
            discord.Color.lighter_grey(),
            discord.Color.dark_grey(),
            discord.Color.light_grey(),
            discord.Color.darker_grey(),
            discord.Color.blurple(),
            discord.Color.greyple(),
            discord.Color.default(),
        ]
        self.color = kwargs.get("color", None)

    def add_field(self, **kwargs):
        self.fields.append(
            {
                "name": kwargs.get("name", "None"),
                "value": kwargs.get("value", "None"),
                "inline": kwargs.get("inline", False),
            }
        )

    def clear_fields(self):
        self.fields = []

    def _get_file(self, file_path):
        if not os.path.exists(file_path):
            return None
        # Path exists, let's get the extension if there is one
        ext = file_path.split(".")
        fname = "Upload." + ext[-1] if len(ext) > 1 else "Upload"
        file_handle = discord.File(fp=file_path, filename=fname)
        # Check if self.url = "attachment" and react
        # if self.url and self.url.lower() == "attachment":
        #    self.url = "attachment://" + fname
        return (file_handle, fname)

    # Embed stuff!
    async def _send_embed(self, ctx, embed, pm=False, file_path=None):
        # Helper method to send embeds to their proper location
        send_file = None
        if not file_path is None:
            dfile = self._get_file(file_path)
            if not dfile:
                # File doesn't exist...
                try:
                    await Embed(
                        title="An error occurred!",
                        description="The file specified couldn't be sent :(",
                        color=self.color,
                    ).send(ctx)
                except Exception:
                    # We tried...
                    pass
                return None
            else:
                # Setup our file
                send_file = dfile[0]
                embed.set_image(url="attachment://" + str(dfile[1]))
        if (
            pm is True
            and type(ctx) is discord.ext.commands.Context
            and not ctx.channel == ctx.author.dm_channel
        ):
            # More than 2 pages and targeting context - try to dm
            try:
                if send_file:
                    message = await ctx.author.send(
                        embed=embed, file=send_file, delete_after=self.delete_after
                    )
                else:
                    message = await ctx.author.send(
                        embed=embed, delete_after=self.delete_after
                    )
                await ctx.message.add_reaction(self.pm_react)
                return message
            except discord.Forbidden:
                if self.force_pm:
                    # send an error embed
                    try:
                        await Embed(
                            title="An error occurred!",
                            description="Could not dm this message to you :(",
                            color=self.color,
                        ).send(ctx)
                    except Exception:
                        # We tried...
                        pass
                    return None
                pass
        if send_file:
            return await ctx.send_or_reply(
                embed=embed, file=send_file, delete_after=self.delete_after
            )
        else:
            return await ctx.send_or_reply(
                embed=embed,
                delete_after=self.delete_after,
            )

    def _truncate_string(self, value, max_chars):
        if not type(value) is str:
            return value
        # Truncates the string to the max chars passed
        return (value[: max_chars - 3] + "...") if len(value) > max_chars else value

    def _total_chars(self, embed):
        # Returns how many chars are in the embed
        tot = 0
        if embed.title:
            tot += len(embed.title)
        if embed.description:
            tot += len(embed.description)
        if not embed.footer is discord.Embed.Empty:
            tot += len(embed.footer)
        for field in embed.fields:
            tot += len(field.name) + len(field.value)
        return tot

    def _embed_with_self(self):
        if self.color is None:
            self.color = random.choice(self.colors)
        elif type(self.color) is discord.Member:
            self.color = self.color.color
        elif type(self.color) is discord.User:
            self.color = random.choice(self.colors)
        elif type(self.color) is tuple or type(self.color) is list:
            if len(self.color) == 3:
                try:
                    r, g, b = [int(a) for a in self.color]
                    self.color = discord.Color.from_rgb(r, g, b)
                except Exception:
                    self.color = random.choice(self.colors)
            else:
                self.color = random.choice(self.colors)

        # Sends the current embed
        em = discord.Embed(color=self.color)
        em.title = self._truncate_string(self.title, self.title_max)
        em.url = self.url
        em.description = self._truncate_string(self.description, self.desc_max)
        if self.image:
            em.set_image(url=self.image)
        if self.thumbnail:
            em.set_thumbnail(url=self.thumbnail)
        if self.author:
            if type(self.author) is discord.Member or type(self.author) is discord.User:
                name = (
                    self.author.nick
                    if hasattr(self.author, "nick") and self.author.nick
                    else self.author.name
                )
                em.set_author(
                    name=self._truncate_string(name, self.auth_max),
                    # Ignore the url here
                    icon_url=self.author.avatar_url,
                )
            elif type(self.author) is dict:
                if any(item in self.author for item in ["name", "url", "icon"]):
                    em.set_author(
                        name=self._truncate_string(
                            self.author.get("name", discord.Embed.Empty), self.auth_max
                        ),
                        url=self.author.get("url", discord.Embed.Empty),
                        icon_url=self.author.get("icon_url", discord.Embed.Empty),
                    )
                else:
                    em.set_author(
                        name=self._truncate_string(str(self.author), self.auth_max)
                    )
            else:
                # Cast to string and hope for the best
                em.set_author(
                    name=self._truncate_string(str(self.author), self.auth_max)
                )
        return em

    def _get_footer(self):
        # Get our footer if we have one
        footer_text = footer_icon = discord.Embed.Empty
        if type(self.footer) is str:
            footer_text = self.footer
        elif type(self.footer) is dict:
            footer_text = self.footer.get("text", discord.Embed.Empty)
            footer_icon = self.footer.get("icon_url", discord.Embed.Empty)
        elif self.footer is None:
            # Never setup
            pass
        else:
            # Try to cast it
            footer_text = str(self.footer)
        return (footer_text, footer_icon)

    async def edit(self, ctx, message):
        # Edits the passed message - and sends any remaining pages
        # check if we can steal the color from the message
        if self.color is None and len(message.embeds):
            self.color = message.embeds[0].color
        em = self._embed_with_self()
        footer_text, footer_icon = self._get_footer()

        to_pm = len(self.fields) > self.pm_after if self.pm_after > -1 else False

        if len(self.fields) <= self.pm_after and not to_pm:
            # Edit in place, nothing else needs to happen
            for field in self.fields:
                em.add_field(
                    name=self._truncate_string(
                        field.get("name", "None"), self.fname_max
                    ),
                    value=self._truncate_string(
                        field.get("value", "None"), self.fval_max
                    ),
                    inline=field.get("inline", False),
                )
            em.set_footer(
                text=self._truncate_string(footer_text, self.foot_max),
                icon_url=footer_icon,
            )
            # Get the file if one exists
            send_file = None
            if self.file:
                m = await self._send_embed(ctx, em, to_pm, self.file)
                await message.delete()
                # await message.edit(content=" ", embed=None, delete_after=self.delete_after)
                return m
            await message.edit(content=None, embed=em, delete_after=self.delete_after)
            return message
        # Now we need to edit the first message to just a space - then send the rest
        new_message = await self.send(ctx)
        if (
            new_message.channel == ctx.author.dm_channel
            and not ctx.channel == ctx.author.dm_channel
        ):
            em = Embed(
                title=self.title, description="📬 Check your dm's", color=self.color
            )._embed_with_self()
            await message.edit(content=None, embed=em, delete_after=self.delete_after)
        else:
            await message.delete()
            # await message.edit(content=" ", embed=None, delete_after=self.delete_after)
        return new_message

    async def send(self, ctx):
        if not ctx:
            return

        em = self._embed_with_self()
        footer_text, footer_icon = self._get_footer()

        # First check if we have any fields at all - and try to send
        # as one page if not
        if not len(self.fields):
            em.set_footer(
                text=self._truncate_string(footer_text, self.foot_max),
                icon_url=footer_icon,
            )
            return await self._send_embed(ctx, em, False, self.file)

        # Only pm if our self.pm_after is above -1
        to_pm = len(self.fields) > self.pm_after if self.pm_after > -1 else False

        page_count = 1
        page_total = math.ceil(len(self.fields) / self.field_max)

        if page_total > 1 and self.page_count and self.title:
            add_title = " (Page {:,} of {:,})".format(page_count, page_total)
            em.title = (
                self._truncate_string(self.title, self.title_max - len(add_title))
                + add_title
            )
        for field in self.fields:
            em.add_field(
                name=self._truncate_string(field.get("name", "None"), self.fname_max),
                value=self._truncate_string(field.get("value", "None"), self.fval_max),
                inline=field.get("inline", False),
            )
            # 25 field max - send the embed if we get there
            if len(em.fields) >= self.field_max:
                if page_count > 1 and not self.page_count:
                    # Clear the title
                    em.title = None
                if page_total == page_count:
                    em.set_footer(
                        text=self._truncate_string(footer_text, self.foot_max),
                        icon_url=footer_icon,
                    )
                if page_count == 1 and self.file:
                    message = await self._send_embed(ctx, em, to_pm, self.file)
                else:
                    # Clear any image if needed
                    # em.set_image(url="")
                    message = await self._send_embed(ctx, em, to_pm)
                # Break if things didn't work
                if not message:
                    return None
                em.clear_fields()
                page_count += 1
                if page_total > 1 and self.page_count and self.title:
                    add_title = " (Page {:,} of {:,})".format(page_count, page_total)
                    em.title = (
                        self._truncate_string(
                            self.title, self.title_max - len(add_title)
                        )
                        + add_title
                    )

        if len(em.fields):
            em.set_footer(
                text=self._truncate_string(footer_text, self.foot_max),
                icon_url=footer_icon,
            )
            if page_total == 1 and self.file:
                message = await self._send_embed(ctx, em, to_pm, self.file)
            else:
                # Clear any image if needed
                # em.set_image(url="")
                message = await self._send_embed(ctx, em, to_pm)
        return message


class EmbedText(Embed):
    def __init__(self, **kwargs):
        Embed.__init__(self, **kwargs)
        # Creates a new embed - with an option setup dictionary
        self.pm_after = kwargs.get("pm_after", 1)
        self.max_pages = kwargs.get("max_pages", 0)
        self.desc_head = kwargs.get("desc_head", "")  # Header for description markdown
        self.desc_foot = kwargs.get("desc_foot", "")  # Footer for description markdown

    async def edit(self, ctx, message):
        # Edits the passed message - and sends any remaining pages
        # check if we can steal the color from the message
        if self.color is None and len(message.embeds):
            self.color = message.embeds[0].color
        em = self._embed_with_self()
        footer_text, footer_icon = self._get_footer()

        if self.description is None or not len(self.description):
            text_list = []
        else:
            text_list = textwrap.wrap(
                self.description,
                self.desc_max - len(self.desc_head) - len(self.desc_foot),
                break_long_words=True,
                replace_whitespace=False,
            )
        to_pm = len(text_list) > self.pm_after if self.pm_after > -1 else False
        if len(text_list) <= 1 and not to_pm:
            # Edit in place, nothing else needs to happen
            if len(text_list):
                em.description = self.desc_head + text_list[0] + self.desc_foot
            em.set_footer(
                text=self._truncate_string(footer_text, self.foot_max),
                icon_url=footer_icon,
            )
            # Get the file if one exists
            send_file = None
            if self.file:
                m = await self._send_embed(ctx, em, to_pm, self.file)
                await message.delete()
                # await message.edit(content=" ", embed=None, delete_after=self.delete_after)
                return m
            await message.edit(content=None, embed=em, delete_after=self.delete_after)
            return message
        # Now we need to edit the first message to just a space - then send the rest
        new_message = await self.send(ctx)
        if (
            new_message.channel == ctx.author.dm_channel
            and not ctx.channel == ctx.author.dm_channel
        ):
            em = Embed(
                title=self.title, description="📬 Check your dm's", color=self.color
            )._embed_with_self()
            await message.edit(content=None, embed=em, delete_after=self.delete_after)
        else:
            await message.delete()
            # await message.edit(content=" ", embed=None, delete_after=self.delete_after)
        return new_message

    async def send(self, ctx):
        if not ctx:
            return

        em = self._embed_with_self()
        footer_text, footer_icon = self._get_footer()

        # First check if we have any fields at all - and try to send
        # as one page if not
        if self.description is None or not len(self.description):
            em.set_footer(
                text=self._truncate_string(footer_text, self.foot_max),
                icon_url=footer_icon,
            )
            return await self._send_embed(ctx, em, False, self.file)

        text_list = textwrap.wrap(
            self.description,
            self.desc_max - len(self.desc_head) - len(self.desc_foot),
            break_long_words=True,
            replace_whitespace=False,
        )

        # Only pm if our self.pm_after is above -1
        to_pm = len(text_list) > self.pm_after if self.pm_after > -1 else False
        page_count = 1
        page_total = len(text_list)

        if len(text_list) > 1 and self.page_count and self.title:
            add_title = " (Page {:,} of {:,})".format(page_count, page_total)
            em.title = (
                self._truncate_string(self.title, self.title_max - len(add_title))
                + add_title
            )

        i = 0
        for i in range(len(text_list)):
            m = text_list[i]
            if self.max_pages > 0 and i >= self.max_pages:
                break
            # Strip the title if not the first page and not counting
            if i > 0 and not self.page_count:
                em.title = None
            if i == len(text_list) - 1:
                # Last item - apply footer
                em.set_footer(
                    text=self._truncate_string(footer_text, self.foot_max),
                    icon_url=footer_icon,
                )
            em.description = (
                self.desc_head.strip("\n") + "\n" + m.strip("\n") + self.desc_foot
            )
            if i == 0 and self.file != None:
                message = await self._send_embed(ctx, em, to_pm, self.file)
            else:
                # Clear any image if needed
                # em.set_image(url="")
                message = await self._send_embed(ctx, em, to_pm)
            # Break if things didn't work
            if not message:
                return None
            page_count += 1
            if len(text_list) > 1 and self.page_count and self.title:
                add_title = " (Page {:,} of {:,})".format(page_count, page_total)
                em.title = (
                    self._truncate_string(self.title, self.title_max - len(add_title))
                    + add_title
                )
        return message


class Picker:
    def __init__(self, **kwargs):
        self.list = kwargs.get("list", [])
        self.title = kwargs.get("title", None)
        self.timeout = kwargs.get("timeout", 60)
        self.ctx = kwargs.get("ctx", None)
        self.message = kwargs.get("message", None)  # message to edit
        self.self_message = None
        self.max = 10  # Don't set programmatically - as we don't want this overridden
        self.reactions = [constants.emotes["stop"]]
        self.color = kwargs.get("color", constants.embed)
        self.footer = kwargs.get("footer", discord.Embed.Empty)
        self.embed_title = kwargs.get("embed_title", discord.Embed.Empty)

    async def _add_reactions(self, message, react_list):
        for r in react_list:
            await message.add_reaction(r)

    async def _remove_reactions(self, react_list=[]):
        # Try to remove all reactions - if that fails, iterate and remove our own
        try:
            await self.self_message.clear_reactions()
        except Exception:
            pass
            # The following "works", but is super slow - and if we can't clear
            # all reactions, it's probably just best to leave them there and bail.
            """for r in react_list:
                await message.remove_reaction(r,message.author)"""

    async def pick(self, embed=False, syntax=None):
        # This actually brings up the pick list and handles the nonsense
        # Returns a tuple of (return_code, message)
        # The return code is -1 for cancel, -2 for timeout, -3 for error, 0+ is index
        # Let's check our prerequisites first
        if self.ctx is None or not len(self.list) or len(self.list) > self.max:
            return (-3, None)
        msg = ""
        if self.title:
            msg += self.title + "\n"
        if syntax:
            msg += f"```{syntax}\n"
        else:
            msg += "```\n"
        # Show our list items
        current = 0
        # current_reactions = [self.reactions[0]]
        current_reactions = []
        for item in self.list:
            current += 1
            current_number = current if current < 10 else 0
            current_reactions.append(constants.emotes[f"num{current_number}"])
            msg += "{}. {}\n".format(current, item)
        msg += "```"
        if embed is True:
            msg = discord.Embed(
                title=self.embed_title, description=msg, color=self.color
            )
            msg.set_footer(text=self.footer)
        # Add the stop reaction
        current_reactions.append(self.reactions[0])
        if self.message:
            self.self_message = self.message
            await self.self_message.edit(content=msg, embed=None)
        else:
            if type(msg) is discord.Embed:
                self.self_message = await self.ctx.send_or_reply(embed=msg)
            else:
                self.self_message = await self.ctx.send_or_reply(msg)
        # Add our reactions
        await self._add_reactions(self.self_message, current_reactions)
        # Now we would wait...
        def check(reaction, user):
            return (
                reaction.message.id == self.self_message.id
                and user == self.ctx.author
                and str(reaction.emoji) in current_reactions
            )

        try:
            reaction, user = await self.ctx.bot.wait_for(
                "picklist_reaction", timeout=self.timeout, check=check
            )
        except Exception:
            # Didn't get a reaction
            await self._remove_reactions(current_reactions)
            return (-2, self.self_message)

        await self._remove_reactions(current_reactions)
        # Get the adjusted index
        ind = current_reactions.index(str(reaction.emoji))
        if ind == len(current_reactions) - 1:
            ind = -1
        return (ind, self.self_message)


class PagePicker(Picker):
    def __init__(self, **kwargs):
        Picker.__init__(self, **kwargs)
        # Expects self.list to contain the fields needed - each a dict with {"name":name,"value":value,"inline":inline}
        self.max = kwargs.get("max", 10)  # Must be between 1 and 25
        self.max = 1 if self.max < 1 else 10 if self.max > 10 else self.max
        self.reactions = [
            "⏪",
            "◀",
            "▶",
            "⏩",
            "🔢",
            "🛑",
        ]  # These will always be in the same order
        self.url = kwargs.get(
            "url", None
        )  # The URL the title of the embed will link to
        self.description = kwargs.get("description", None)

    def _get_page_contents(self, page_number):
        # Returns the contents of the page passed
        start = self.max * page_number
        return self.list[start : start + self.max]

    async def pick(self):
        # This brings up the page picker and handles the events
        # It will return a tuple of (last_page_seen, message)
        # The return code is -1 for cancel, -2 for timeout, -3 for error, 0+ is index
        # Let's check our prerequisites first
        if self.ctx is None or not len(self.list):
            return (-3, None)
        page = 0  # Set the initial page index
        pages = int(math.ceil(len(self.list) / self.max))
        # Setup the embed
        embed = {
            "title": self.title,
            "url": self.url,
            "description": self.description,
            "color": self.ctx.author,
            "pm_after": 25,
            "fields": self._get_page_contents(page),
            "footer": "Page {} of {}".format(page + 1, pages),
        }
        if self.message:
            self.self_message = self.message
            await Embed(**embed).edit(self.ctx, self.message)
        else:
            self.self_message = await Embed(**embed).send(self.ctx)
        # First verify we have more than one page to display
        if pages <= 1:
            return (0, self.self_message)
        # Add our reactions
        await self._add_reactions(self.self_message, self.reactions)
        # Now we would wait...
        def check(reaction, user):
            return (
                reaction.message.id == self.self_message.id
                and user == self.ctx.author
                and str(reaction.emoji) in self.reactions
            )

        while True:
            try:
                reaction, user = await self.ctx.bot.wait_for(
                    "picklist_reaction", timeout=self.timeout, check=check
                )
            except Exception:
                # Didn't get a reaction
                await self._remove_reactions(self.reactions)
                return (page, self.self_message)
            # Got a reaction - let's process it
            ind = self.reactions.index(str(reaction.emoji))
            if ind == 5:
                # We bailed - let's clear reactions and close it down
                await self._remove_reactions(self.reactions)
                return (page, self.self_message)
            page = (
                0
                if ind == 0
                else page - 1
                if ind == 1
                else page + 1
                if ind == 2
                else pages
                if ind == 3
                else page
            )
            if ind == 4:
                # User selects a page
                page_instruction = await self.ctx.send_or_reply(
                    "Type the number of that page to go to from {} to {}.".format(
                        1, pages
                    )
                )

                def check_page(message):
                    try:
                        num = int(message.content)
                    except Exception:
                        return False
                    return (
                        message.channel == self.self_message.channel
                        and user == message.author
                    )

                try:
                    page_message = await self.ctx.bot.wait_for(
                        "message", timeout=self.timeout, check=check_page
                    )
                    page = int(page_message.content) - 1
                except Exception:
                    # Didn't get a message
                    pass
                # Delete the instruction
                await page_instruction.delete()
                # Try to delete the user's page message too
                try:
                    await page_message.delete()
                except Exception:
                    pass
            page = 0 if page < 0 else pages - 1 if page > pages - 1 else page
            embed["fields"] = self._get_page_contents(page)
            embed["footer"] = "Page {} of {}".format(page + 1, pages)
            await Embed(**embed).edit(self.ctx, self.self_message)
        await self._remove_reactions(self.reactions)
        # Get the adjusted index
        return (page, self.self_message)


class EmbedLimits:
    Field = 1024
    Name = 256
    Title = 256
    Description = 2048
    Fields = 25
    Total = 6000


class Paginator:
    def __init__(
        self,
        title=None,
        description=None,
        page_count=True,
        init_page=True,
        color=constants.embed,
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
        color=constants.embed,
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
                description_ = description[: EmbedLimits.Description]
                overflow = description[EmbedLimits.Description :]
                description = description_
            else:
                description = description[: EmbedLimits.Description]

        self._pages.append(
            discord.Embed(title=title, description=description, color=constants.embed)
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

        name = name[: EmbedLimits.Title]
        leftovers = value[EmbedLimits.Field :]
        value = value[: EmbedLimits.Field]
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

        self._current_field = {"name": name, "value": value, "inline": inline}

        if leftovers:
            self.add_field(name, leftovers, inline=inline)

    def add_to_field(self, value):
        v = self._current_field["value"]
        if len(v) + len(value) > EmbedLimits.Field:
            self.add_field(self._current_field["name"], value)
        else:
            self._current_field["value"] += value
