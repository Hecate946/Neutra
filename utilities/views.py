from os import name
import discord
import asyncio
from settings import constants


class MuteRoleView(discord.ui.View):
    def __init__(self, ctx):
        super().__init__(timeout=60)
        self.ctx = ctx
        self.overwrites = None
        self.message = None

    def create_msg(self, option):
        msg = f"{self.ctx.bot.emote_dict['loading']} **Creating mute system. "
        msg += f"Muted users will not be able to {option} messages. "
        msg += "This process may take several minutes...**"
        return msg

    async def interaction_check(self, interaction):
        if self.ctx.author.id == interaction.user.id:
            return True
        else:
            await interaction.response.send_message(
                "Only the command invoker can use this button.", ephemeral=True
            )

    async def on_timeout(self):
        self.stop()

    @discord.ui.button(
        label="Block (Cannot send messages)", style=discord.ButtonStyle.blurple
    )
    async def block(self, button: discord.ui.Button, interaction: discord.Interaction):
        await interaction.message.edit(
            content=self.create_msg("send"), embed=None, view=None
        )
        self.overwrites = {"send_messages": False}
        self.stop()

    @discord.ui.button(
        label="Blind (Cannot read messages)", style=discord.ButtonStyle.gray
    )
    async def blind(self, button: discord.ui.Button, interaction: discord.Interaction):
        await interaction.message.edit(
            content=self.create_msg("read"), embed=None, view=None
        )
        self.overwrites = {"send_messages": False, "read_messages": False}
        self.stop()

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red)
    async def cancel(self, button: discord.ui.Button, interaction: discord.Interaction):
        self.stop()


class Confirmation(discord.ui.View):
    def __init__(self, ctx, msg, **kwargs):
        super().__init__(timeout=10.0)
        self.ctx = ctx
        self.msg = msg
        self.kwargs = kwargs
        self.result = None

    async def prompt(self):
        self.message = await self.ctx.send(self.msg, view=self, **self.kwargs)
        await self.wait()
        return self.result

    async def on_timeout(self):
        if self.message:
            await self.message.edit("**Confirmation Cancelled.**", view=None)

    async def interaction_check(self, interaction):
        if self.ctx.author.id == interaction.user.id:
            return True
        else:
            await interaction.response.send_message(
                "Only the command invoker can use this button.", ephemeral=True
            )

    @discord.ui.button(
        emoji=constants.emotes["success"], style=discord.ButtonStyle.gray
    )
    async def _confirm(
        self, button: discord.ui.Button, interaction: discord.Interaction
    ):
        await interaction.message.delete()
        self.result = True
        self.stop()

    @discord.ui.button(emoji=constants.emotes["failed"], style=discord.ButtonStyle.gray)
    async def _deny(self, button: discord.ui.Button, interaction: discord.Interaction):
        await interaction.message.edit(content="**Confirmation Cancelled.**", view=None)
        self.result = False
        self.stop()


class ButtonPages(discord.ui.View):
    async def __init__(self, ctx, pages, *, content="", compact=True):
        super().__init__(timeout=60)
        self.ctx = ctx
        self.pages = pages
        self.content = content
        self.page_number = 1
        self.max_pages = len(self.pages)
        self.current_page = pages[0]
        self.input_lock = asyncio.Lock()
        self.compact = compact

        self.clear_items()
        self.fill_items()

        self.message = await self.send_message()

    def fill_items(self, _help=None):
        if _help:
            self.add_item(self._delete)
            self.add_item(self._return)
            return

        self.add_item(self._first)
        self.add_item(self._back)
        self.add_item(self._select)
        self.add_item(self._next)
        self.add_item(self._last)
        if not self.compact:
            self.add_item(self._delete)
            self.add_item(self._compact)
            self.add_item(self._help)

    async def send_message(self):
        if isinstance(self.pages[0], discord.Embed):
            if self.max_pages == 1:
                message = await self.ctx.send(
                    self.content, embed=self.pages[0], view=None
                )
            else:
                self.update_view(1)
                message = await self.ctx.send(
                    self.content, embed=self.pages[0], view=self
                )
        else:
            if self.max_pages == 1:
                message = await self.ctx.send(self.content + self.pages[0], view=None)
            else:
                self.update_view(1)
                message = await self.ctx.send(self.content + self.pages[0], view=self)
        return message

    async def interaction_check(self, interaction):
        if self.ctx.author.id == interaction.user.id:
            return True
        else:
            await interaction.response.send_message(
                "Only the command invoker can use this button.", ephemeral=True
            )

    async def on_timeout(self):
        try:
            await self.message.edit(view=None)
        except Exception:
            pass

    async def on_error(
        self, error: Exception, item: discord.ui.Item, interaction: discord.Interaction
    ):
        if interaction.response.is_done():
            await interaction.followup.send(str(error), ephemeral=True)
        else:
            await interaction.response.send_message(str(error), ephemeral=True)

    def update_view(self, page_number):
        self.page_number = page_number
        self._first.disabled = page_number == 1
        self._back.disabled = page_number == 1
        self._next.disabled = page_number == self.max_pages
        self._last.disabled = page_number == self.max_pages

    async def show_page(self, interaction):
        page = self.current_page = self.pages[self.page_number - 1]
        if isinstance(page, discord.Embed):
            await interaction.message.edit(embed=page, view=self)
        else:
            await interaction.message.edit(content=page, view=self)

    @discord.ui.button(
        emoji=constants.emotes["backward2"], style=discord.ButtonStyle.gray
    )
    async def _first(self, button: discord.ui.Button, interaction: discord.Interaction):
        self.update_view(1)
        await self.show_page(interaction)

    @discord.ui.button(
        emoji=constants.emotes["backward"], style=discord.ButtonStyle.gray
    )
    async def _back(self, button: discord.ui.Button, interaction: discord.Interaction):
        self.update_view(self.page_number - 1)
        await self.show_page(interaction)

    @discord.ui.button(
        emoji=constants.emotes["forward"], style=discord.ButtonStyle.gray
    )
    async def _next(self, button: discord.ui.Button, interaction: discord.Interaction):
        self.update_view(self.page_number + 1)
        await self.show_page(interaction)

    @discord.ui.button(
        emoji=constants.emotes["forward2"], style=discord.ButtonStyle.gray
    )
    async def _last(self, button: discord.ui.Button, interaction: discord.Interaction):
        self.update_view(self.max_pages)
        await self.show_page(interaction)

    @discord.ui.button(
        emoji=constants.emotes["1234button"], style=discord.ButtonStyle.grey
    )
    async def _select(
        self, button: discord.ui.Button, interaction: discord.Interaction
    ):
        """lets you type a page number to go to"""
        if self.input_lock.locked():
            await interaction.response.send_message(
                "Already waiting for your response...", ephemeral=True
            )
            return

        if self.message is None:
            return

        async with self.input_lock:
            channel = self.message.channel
            author_id = interaction.user and interaction.user.id
            await interaction.response.send_message(
                "What page do you want to go to?", ephemeral=True
            )

            def message_check(m):
                if not m.author.id == author_id:
                    return False
                if not channel == m.channel:
                    return False
                if not m.content.isdigit():
                    return False
                if not 1 <= int(m.content) <= self.max_pages:
                    raise IndexError(
                        f"Page number must be between 1 and {self.max_pages}"
                    )
                return True

            try:
                msg = await self.ctx.bot.wait_for(
                    "message", check=message_check, timeout=30.0
                )
            except asyncio.TimeoutError:
                await interaction.followup.send("Selection expired.", ephemeral=True)
                await asyncio.sleep(5)
            else:
                page = int(msg.content)
                try:
                    await msg.delete()
                except:
                    pass
                self.update_view(page)
                await self.show_page(interaction)

    @discord.ui.button(label="Delete session", style=discord.ButtonStyle.red)
    async def _delete(
        self, button: discord.ui.Button, interaction: discord.Interaction
    ):
        await interaction.message.delete()
        self.stop()

    @discord.ui.button(label="Compact view", style=discord.ButtonStyle.blurple)
    async def _compact(
        self, button: discord.ui.Button, interaction: discord.Interaction
    ):
        self.compact = True
        self.clear_items()
        self.fill_items()
        await interaction.message.edit(view=self)

    @discord.ui.button(label="Need help?", style=discord.ButtonStyle.green)
    async def _help(self, button: discord.ui.Button, interaction: discord.Interaction):
        self.clear_items()
        self.fill_items(_help=True)
        embed = discord.Embed(color=constants.embed)
        embed.set_author(
            name="Pagination Help Page", icon_url=self.ctx.bot.user.display_avatar.url
        )
        embed.description = (
            "Read below for a description of each button and it's function."
        )
        embed.add_field(
            name=constants.emotes["backward2"] + "  Jump to the first page",
            value="This button shows the first page of the pagination session.",
            inline=False,
        )
        embed.add_field(
            name=constants.emotes["backward"] + "  Show the previous page",
            value="This button shows the previous page of the pagination session.",
            inline=False,
        )
        embed.add_field(
            name=constants.emotes["1234button"] + "  Input a page number",
            value="This button shows a page after you input a page number.",
            inline=False,
        )
        embed.add_field(
            name=constants.emotes["forward"] + "  Show the next page",
            value="This button shows the next page of the pagination session",
            inline=False,
        )
        embed.add_field(
            name=constants.emotes["forward2"] + "  Jump to the last page.",
            value="This button shows the last page of the pagination session",
            inline=False,
        )
        embed.set_footer(
            text=f"Previously viewing page {self.page_number} of {self.max_pages}"
        )
        # embed.add_field(name="Delete session", value="This button ends the pagination session and deletes the message", inline=False)
        # embed.add_field(name="Compact view", value="This button removes the three colored buttons for a more \"compact\" view", inline=False)
        # embed.add_field(name="Need help?", value="This button shows this help page.", inline=False)
        await interaction.message.edit(embed=embed, view=self)

    @discord.ui.button(label="Return to main page", style=discord.ButtonStyle.blurple)
    async def _return(
        self, button: discord.ui.Button, interaction: discord.Interaction
    ):
        self.clear_items()
        self.fill_items()
        if isinstance(self.current_page, discord.Embed):
            await interaction.message.edit(embed=self.current_page, view=self)
        else:
            await interaction.message.edit(content=self.current_page, view=self)


class SimpleView(ButtonPages):
    """
    Simple button page session that turns
    a list of strings into a pagination session
    by splitting them up and adding them to the
    description of an embed.
    Parameters:
        ctx: The context of a command
        entries: The list of strings
        per_page: How many entries per embed
        index: Whether or not to prepend numbers to each entry
        desc_head: Prefix the description with a string
        desc_foot: Suffix the description with a string
    """

    def __init__(
        self,
        ctx,
        entries,
        *,
        per_page: int = 10,
        index: bool = True,
        desc_head: str = "",
        desc_foot: str = "",
        content="",
    ):
        self.ctx = ctx
        self.entries = entries

        self.per_page = per_page
        self.index = index
        self.desc_head = desc_head
        self.desc_foot = desc_foot
        self.content = content

        self.embed = discord.Embed(color=ctx.bot.constants.embed)

    async def start(self):
        self.pages = self.create_pages(self.entries, self.per_page)
        await super().__init__(self.ctx, self.pages, content=self.content)

    def create_pages(self, entries, per_page):
        embeds = []
        index = 0
        while entries:
            embed = self.embed.copy()
            embed.description = self.desc_head
            if self.index:
                for entry in entries[:per_page]:
                    index += 1
                    embed.description += f"{index}. {entry}\n"
            else:
                embed.description += "\n".join(entries[:per_page])
            embed.description += self.desc_foot
            del entries[:per_page]

            embeds.append(embed)

        for count, embed in enumerate(embeds, start=1):
            embed.set_footer(text=f"Page {count} of {len(embeds)}")
        return embeds


class CodeView(ButtonPages):
    """
    Simple button page session that turns
    a block of text into a pagination session
    by splitting them and creating a codeblock.
    Parameters:
        ctx: The context of a command
        lines: The text block or list of lines.
        per_page: How many entries per codeblock
        index: Whether or not to prepend numbers to each entry
        syntax: The syntax highlighting.
        content: Some content to prefix the text with.
    """

    def __init__(
        self,
        ctx,
        lines,
        *,
        per_page: int = 10,
        index: bool = True,
        syntax="",
        content="",
    ):
        self.ctx = ctx
        self.lines = lines
        self.per_page = per_page
        self.index = index
        self.syntax = syntax
        self.content = content

    async def start(self):
        self.pages = self.create_pages(self.lines, self.per_page)
        await super().__init__(self.ctx, self.pages, content=self.content)

    def create_pages(self, lines, per_page):
        pages = []
        index = 0
        if not isinstance(lines, list):
            lines = lines.split("\n")

        while lines:
            page = f"```{self.syntax}\n"
            if self.index:
                for line in lines[:per_page]:
                    index += 1
                    page += f"{index}. {line}\n"
            else:
                page += "\n".join(lines[:per_page])

            del lines[:per_page]
            pages.append(page)
        pages = self.suffix_pages(pages)

        return pages

    def suffix_pages(self, pages):
        suffixed = []
        for count, page in enumerate(pages, start=1):
            suffix = f"\n\nPage {count} of {len(pages)}```"
            if len(page + suffix) > 2000:
                page = page[: 2000 - 3 - len(suffix)] + "..." + suffix
            else:
                page = page + suffix
            suffixed.append(page)
        return suffixed


class ImageView(ButtonPages):
    """
    Button page session that turns a list of image
    urls into a pagination session by assigning
    each url to the thumbnail or image of an embed.
    Parameters:
        ctx: The context of a command
        entries: The list of urls
        thumbnail: Show the images as thumbnails.
        content: Prefix the embed with some content.
    """

    def __init__(self, ctx, entries, *, thumbnail=False, content=""):
        self.ctx = ctx
        self.entries = entries
        self.thumbnail = thumbnail
        self.content = content

        self.embed = discord.Embed(color=ctx.bot.constants.embed)

    async def start(self):
        self.embeds = self.create_embeds(self.entries)
        await super().__init__(self.ctx, self.embeds, content=self.content)

    def create_embeds(self, entries):
        embeds = []
        for url in entries:
            embed = self.embed.copy()
            if self.thumbnail:
                embed.set_thumbnail(url=url)
            else:
                embed.set_image(url=url)
            embeds.append(embed)
        embeds[0].set_footer(text=f"Page 1 of {len(embeds)}")
        return embeds
