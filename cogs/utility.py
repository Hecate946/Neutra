import io
import re
import copy
import json
import math
import base64
import codecs
import pprint
import random
import asyncio
import discord
import operator
import unicodedata

from collections import Counter, namedtuple
from datetime import datetime
from discord.ext import commands, menus
from functools import cmp_to_key
from PIL import Image
from typing import Union
from unidecode import unidecode
from pyparsing import (
    CaselessLiteral,
    Combine,
    Forward,
    Group,
    Literal,
    Optional,
    Word,
    ZeroOrMore,
    alphas,
    nums,
    oneOf,
)

from utilities import utils
from utilities import checks
from utilities import converters
from utilities import decorators
from utilities import pagination


def setup(bot):
    bot.add_cog(Utility(bot))


# Couple of commands taken and edited from Stella#2000's bot
# https://github.com/InterStella0/stella_bot


class Utility(commands.Cog):
    """
    Module for general utilities.
    """

    def __init__(self, bot):
        self.bot = bot
        self.msg_collection = []
        self.uregex = re.compile(
            r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*(),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+"
        )
        self.color_dict = {
            "teal": discord.Color.teal(),
            "dark_teal": discord.Color.dark_teal(),
            "green": discord.Color.green(),
            "dark_green": discord.Color.dark_green(),
            "blue": discord.Color.blue(),
            "dark_blue": discord.Color.dark_blue(),
            "purple": discord.Color.purple(),
            "dark_purple": discord.Color.dark_purple(),
            "pink": discord.Color.magenta(),
            "dark_pink": discord.Color.dark_magenta(),
            "gold": discord.Color.gold(),
            "dark_gold": discord.Color.dark_gold(),
            "orange": discord.Color.orange(),
            "dark_orange": discord.Color.dark_orange(),
            "red": discord.Color.red(),
            "dark_red": discord.Color.dark_red(),
            "lighter_gray": discord.Color.lighter_grey(),
            "dark_gray": discord.Color.dark_grey(),
            "light_gray": discord.Color.light_grey(),
            "darker_gray": discord.Color.darker_grey(),
            "blurple": discord.Color.blurple(),
            "greyple": discord.Color.greyple(),
        }

    def parse_date(self, token):
        token_epoch = 1293840000
        bytes_int = base64.standard_b64decode(token + "==")
        decoded = int.from_bytes(bytes_int, "big")
        timestamp = datetime.utcfromtimestamp(decoded)

        # sometime works
        if timestamp.year < 2015:
            timestamp = datetime.utcfromtimestamp(decoded + token_epoch)
        return timestamp

    @decorators.command(
        aliases=["genoauth", "oauth2", "genbotoauth"],
        brief="Generate a bot invite link.",
        implemented="2021-05-05 17:59:12.441533",
        updated="2021-05-05 17:59:12.441533",
        examples="""
                {0}oauth
                {0}oauth2 810377376269205546 8
                {0}genoauth Snowbot#7630 359867
                {0}genbotoauth @Snowbot 34985
                """,
    )
    async def oauth(
        self, ctx, bot: converters.DiscordBot = None, permissions: int = None
    ):
        if not bot:
            await ctx.reply(f"<{self.bot.oauth}>")
            return
        if permissions:
            permissions = discord.Permissions(permissions)
        oauth_url = discord.utils.oauth_url(bot.id, permissions=permissions)
        await ctx.reply("<" + oauth_url + ">")

    @decorators.command(  # For anyone looking here, these tokens are not valid.
        aliases=["pt", "parsetoken"],
        brief="Decode a discord token.",
        implemented="2021-05-06 01:09:46.734485",
        updated="2021-05-07 05:47:26.758031",
        examples="""
                {0}pt NzA4NTg0MDA4MDY1MzUxNjgx.YJU29g.K8lush3e6flT9Of7d7bp4rj6aU2
                {0}ptoken NzA4NTg0MDA4MDY1MzUxNjgx.YJU29g.K8lush3e6flT9Of7d7bp4rj6aU2
                {0}parsetoken NzA4NTg0MDA4MDY1MzUxNjgx.YJU29g.K8lush3e6flT9Of7d7bp4rj6aU2
                """,
    )
    @checks.bot_has_perms(embed_links=True)
    async def ptoken(self, ctx, token):
        """
        Usage: {0}ptoken <token>
        Aliases: {0}pt, {0}parsetoken
        Output:
            Decodes the token by splitting the token into 3 parts.
        Notes:
            First part is a user id where it was decoded from base 64 into str. The second part
            is the creation of the token, which is converted from base 64 into int. The last part
            cannot be decoded due to discord encryption.
        """
        token_part = token.split(".")
        if len(token_part) != 3:
            return await ctx.send_or_reply("Invalid token")

        def decode_user(user):
            user_bytes = user.encode()
            user_id_decoded = base64.b64decode(user_bytes)
            return user_id_decoded.decode("ascii")

        str_id = decode_user(token_part[0])
        if not str_id or not str_id.isdigit():
            return await ctx.send_or_reply("Invalid user")
        user_id = int(str_id)
        member = self.bot.get_user(user_id)
        if not member:
            return await ctx.send_or_reply("Invalid user")
        timestamp = self.parse_date(token_part[1]) or "Invalid date"

        embed = discord.Embed(
            title=f"{member.display_name}'s token",
            description=f"**User:** `{member}`\n"
            f"**ID:** `{member.id}`\n"
            f"**Bot:** `{member.bot}`\n"
            f"**Created:** `{member.created_at}`\n"
            f"**Token Created:** `{timestamp}`",
        )
        embed.color = self.bot.constants.embed
        embed.set_thumbnail(url=member.avatar_url)
        await ctx.send_or_reply(embed=embed)

    @decorators.command(
        aliases=["gt", "generatetoken"],
        brief="Generate a discord token.",
        implemented="2021-05-06 02:26:12.925925",
        updated="2021-05-07 05:49:40.401151",
        examples="""
                {0}gt
                {0}gtoken 708584008065351681
                {0}generatetoken Hecate
                """,
    )
    @checks.bot_has_perms(embed_links=True)
    async def gtoken(self, ctx, user: Union[discord.Member, discord.User] = None):
        """
        Usage: {0}gtoken <user>
        Aliases: {0}gt, {0}generatetoken
        Output:
            Generates a discord token for a user
        Notes:
            Defaults to you if no user is passed.
        """
        if not user:
            user = ctx.author
        byte_first = str(user.id).encode("ascii")
        first_encode = base64.b64encode(byte_first)
        first = first_encode.decode("ascii")
        time_rn = datetime.utcnow()
        epoch_offset = int(time_rn.timestamp())
        bytes_int = int(epoch_offset).to_bytes(10, "big")
        bytes_clean = bytes_int.lstrip(b"\x00")
        unclean_middle = base64.standard_b64encode(bytes_clean)
        middle = unclean_middle.decode("utf-8").rstrip("==")
        Pair = namedtuple("Pair", "min max")
        num = Pair(48, 57)  # 0 - 9
        cap_alp = Pair(65, 90)  # A - Z
        cap = Pair(97, 122)  # a - z
        select = (num, cap_alp, cap)
        last = ""
        for each in range(27):
            pair = random.choice(select)
            last += str(chr(random.randint(pair.min, pair.max)))

        complete = ".".join((first, middle, last))

        embed = discord.Embed(
            title=f"{user.display_name}'s token",
            description=f"**User:** `{user}`\n"
            f"**ID:** `{user.id}`\n"
            f"**Bot:** `{user.bot}`\n"
            f"**Token created:** `{time_rn}`\n"
            f"**Generated token:** `{complete}`\n",
        )
        embed.color = self.bot.constants.embed
        embed.set_thumbnail(url=user.avatar_url)
        await ctx.send_or_reply(embed=embed)

    @decorators.command(
        brief="Find the first message of a reply thread.",
        implemented="2021-05-06 01:10:04.331672",
        updated="2021-05-07 05:49:40.401151",
        examples="""
                {0}replies 840103070402740274
                """,
    )
    @checks.bot_has_perms(embed_links=True)
    async def replies(self, ctx, message: discord.Message):
        """
        Usage: {0}replies <message>
        Output:
            The author, replies, message
            and jump_url to the message.
        """

        def count_reply(m, replies=0):
            if isinstance(m, discord.MessageReference):
                return count_reply(m.cached_message, replies)
            if isinstance(m, discord.Message):
                if not m.reference:
                    return m, replies
                replies += 1
                return count_reply(m.reference, replies)

        msg, count = count_reply(message)
        em = discord.Embed()
        em.color = self.bot.constants.embed
        em.title = "Reply Count"
        em.description = (
            f"**Original:** `{msg.author}`\n"
            f"**Message:** {msg.clean_content}\n"
            f"**Replies:** `{count}`\n"
            f"**Origin:** [`jump`]({msg.jump_url})"
        )

        await ctx.send_or_reply(embed=em)

    @decorators.command(
        name="type",
        aliases=["objtype", "findtype"],
        brief="Find the type of a discord object.",
        implemented="",
        updated="",
        examples="""
                {0}type <:forward:816458167835820093>
                {0}objtype 708584008065351681
                {0}findtype 840103070402740274
                """,
    )
    async def type_(self, ctx, obj_id: discord.Object):
        """
        Usage: -type <discord object>
        Aliases: -findtype, -objtype
        Output:
            Attemps to find the type of the object presented.
        """

        async def found_message(type_id):
            embed = discord.Embed(title="Result")
            embed.description = (
                f"**ID**: `{obj_id.id}`\n"
                f"**Type:** `{type_id.capitalize()}`\n"
                f"**Created:** `{obj_id.created_at}`"
            )
            embed.color = self.bot.constants.embed
            await ctx.send_or_reply(embed=embed)
            return

        async def find(w, t):
            try:
                method = getattr(self.bot, f"{w}_{t}")
                if result := await discord.utils.maybe_coroutine(method, obj_id.id):
                    return result is not None
            except discord.Forbidden:
                return ("fetch", "guild") != (w, t)
            except (discord.NotFound, AttributeError):
                pass

        m = await self.bot.http._HTTPClient__session.get(
            f"https://cdn.discordapp.com/emojis/{obj_id.id}"
        )
        res = None
        if m.status == 200:
            return await found_message("emoji")
        try:
            await commands.MessageConverter().convert(ctx, str(obj_id.id))
            res = True
            return await found_message("message")
        except commands.MessageNotFound:
            pass

        try:
            await commands.MemberConverter().convert(ctx, str(obj_id.id))
            res = True
            return await found_message("member")
        except commands.MemberNotFound:
            pass

        try:
            await commands.UserConverter().convert(ctx, str(obj_id.id))
            res = True
            return await found_message("user")
        except commands.UserNotFound:
            pass

        try:
            await commands.RoleConverter().convert(ctx, str(obj_id.id))
            res = True
            return await found_message("role")
        except commands.RoleNotFound:
            pass

        try:
            await commands.TextChannelConverter().convert(ctx, str(obj_id.id))
            res = True
            return await found_message("text channel")
        except commands.ChannelNotFound:
            pass

        try:
            await commands.VoiceChannelConverter().convert(ctx, str(obj_id.id))
            res = True
            return await found_message("voice channel")
        except commands.ChannelNotFound:
            pass

        try:
            await commands.CategoryChannelConverter().convert(ctx, str(obj_id.id))
            res = True
            return await found_message("category")
        except commands.ChannelNotFound:
            pass

        try:
            await commands.InviteConverter().convert(ctx, str(obj_id.id))
            res = True
            return await found_message("invite")
        except commands.BadInviteArgument:
            pass
        if not res:
            return await ctx.send_or_reply(
                f"{self.bot.emote_dict['failed']} I could not find that object."
            )

    @decorators.command(
        brief="Show a given color and its values.",
        implemented="2021-04-16 00:19:02.842207",
        updated="2021-05-07 05:44:12.543100",
        examples="""
                {0}color #3399cc
                {0}color rgb(3, 4, 5)
                {0}color cmyk(1, 2, 3, 4)
                {0}color 0xFF00FF
                """,
    )
    async def color(self, ctx, *, value):
        """
        Usage: {0}color <value>
        Output:
            View info on a rgb, hex or cmyk color and their
            values in other formats
        Notes:
            Will try to convert value into role
            and return role color before searching
            for hex, decimal, rgb, and cmyk
        """
        async with ctx.channel.typing():
            try:
                role = await commands.RoleConverter().convert(ctx, value)
                color_values = [role.color.value]
                original_type = "hex"
            except Exception:
                # Let's replace commas, and parethesis with spaces, then split on whitespace
                values = (
                    value.replace(",", " ")
                    .replace("(", " ")
                    .replace(")", " ")
                    .replace("%", " ")
                    .split()
                )
                color_values = []
                for x in values:
                    if x.lower().startswith(("0x", "#")) or any(
                        (y in x.lower() for y in "abcdef")
                    ):
                        # We likely have a hex value
                        try:
                            color_values.append(
                                int(x.lower().replace("#", "").replace("0x", ""), 16)
                            )
                        except:
                            pass  # Bad value - ignore
                    else:
                        # Try to convert it to an int
                        try:
                            color_values.append(int(x))
                        except:
                            pass  # Bad value - ignore
                original_type = (
                    "hex"
                    if len(color_values) == 1
                    else "rgb"
                    if len(color_values) == 3
                    else "cmyk"
                    if len(color_values) == 4
                    else None
                )
                if original_type is None:
                    return await ctx.send_or_reply(
                        content=f"{self.bot.emote_dict['failed']} "
                        "Incorrect number of color values! "
                        "Hex takes 1, RGB takes 3, CMYK takes 4.",
                    )
                # Verify values
                max_val = (
                    int("FFFFFF", 16)
                    if original_type == "hex"
                    else 255
                    if original_type == "rgb"
                    else 100
                )
                if not all((0 <= x <= max_val for x in color_values)):
                    return await ctx.send_or_reply(
                        content="Value out of range! "
                        "Valid ranges are from `#000000` to `#FFFFFF` for Hex, "
                        "`0` to `255` for RGB, and `0` to `100` for CMYK.",
                    )
            em = discord.Embed()
            # Organize the data into the Message format expectations
            if original_type == "hex":
                hex_value = (
                    "#" + hex(color_values[0]).replace("0x", "").rjust(6, "0").upper()
                )
                color = color_values[0]
            elif original_type == "rgb":
                hex_value = self._rgb_to_hex(*color_values)
                color = int(self._rgb_to_hex(*color_values).replace("#", ""), 16)
            else:
                hex_value = self._cmyk_to_hex(*color_values)
                color = int(self._cmyk_to_hex(*color_values).replace("#", ""), 16)

            em.add_field(name="HEX", value=hex_value, inline=False)
            em.add_field(
                name="DECIMAL",
                value=int(self._check_hex(hex_value), 16),
                inline=False,
            )
            em.add_field(
                name="RGB",
                value="rgb({}, {}, {})".format(*self._hex_to_rgb(hex_value)),
                inline=False,
            )
            em.add_field(
                name="CMYK",
                value="cmyk({}, {}, {}, {})".format(*self._hex_to_cmyk(hex_value)),
                inline=False,
            )
            em.color = color
            # Create the image
            image = Image.new(
                mode="RGB", size=(256, 256), color=self._hex_int_to_tuple(color)
            )
            buffer = io.BytesIO()
            image.save(buffer, "png")  # 'save' function for PIL
            buffer.seek(0)
            dfile = discord.File(fp=buffer, filename="color.png")
            em.set_image(url="attachment://color.png")
            await ctx.send_or_reply(embed=em, file=dfile)

    @decorators.command(brief="Send an image with some hex codes.")
    async def colors(self, ctx):
        """
        Usage: {0}colors
        Output:
            An image showing a few
            hex colors and codes
        """
        await ctx.send_or_reply(
            file=discord.File("./data/assets/colors.png", filename="colors.png")
        )

    @decorators.command(
        brief="Dehoist a specified user.",
        implemented="2021-05-06 02:22:00.614849",
        updated="2021-05-07 05:42:25.333804",
        examples="""
                {0}dehoist Hecate
                {0}dehoist @Hecate
                {0}dehoist Hecate#3523
                {0}dehoist 708584008065351681
                """,
    )
    @checks.bot_has_perms(manage_nicknames=True)
    @checks.has_perms(manage_nicknames=True)
    async def dehoist(self, ctx, user: converters.DiscordMember):
        """
        Usage: {0}dehoist <user>
        Permission: Manage Nicknames
        Output:
            Re nicknames a single user who hoists
            themselves at the top of the member
            list by using special characters
        Notes:
            To dehoist all users with a single command,
            use {0}massdehoist instead.
        """
        characters = [
            "!",
            '"',
            "#",
            "$",
            "%",
            "&",
            "'",
            "(",
            ")",
            "*",
            "+",
            ",",
            "-",
            ".",
            "/",
        ]
        if user.display_name.startswith(tuple(characters)):
            name = copy.copy(user.display_name)
            while name.startswith(tuple(characters)):
                name = name[1:]
            if name.strip() == "":
                name = "Dehoisted"
            try:
                await user.edit(
                    nick=name,
                    reason=utils.responsible(
                        ctx.author, "Nickname edited by dehoist command."
                    ),
                )
                return await ctx.send_or_reply(
                    content=f"{self.bot.emote_dict['success']} Successfully dehoisted `{user}`",
                )
            except Exception:
                await ctx.send_or_reply(
                    content=f"{self.bot.emote_dict['failed']} Failed to dehoist `{user}`",
                )

        else:
            await ctx.send_or_reply(
                content=f"{self.bot.emote_dict['failed']} User `{user}` is not hoisting.",
            )

    @decorators.command(
        brief="Convert special characters to ascii.",
        implemented="2021-04-21 05:14:23.747367",
        updated="2021-05-07 05:34:35.645870",
        examples="""
                {0}ascify H̷̗́̊ẻ̵̩̚ċ̷͎̖̚a̴̛͎͊t̸̳̭̂͌ȇ̴̲̯
                {0}ascify 708584008065351681
                """,
    )
    async def ascify(self, ctx, *, string_or_member):
        """
        Usage: {0}ascify <string/member>
        Aliases: {0}ascii, {0}normalize
        Output:
            Attempts to convert a string or member's
            nickname to ascii by replacing special
            characters.
        Notes:
            If the passed argument is a user and both the
            command executor and the bot have
            the required permissions, the bot will
            set the user's nickname to the ascified
            version of the word. Otherwise, it will
            simply return the ascified version. If
            the passed string is already in ASCII,
            it will return the same result.
        """
        try:
            member = await commands.MemberConverter().convert(ctx, string_or_member)
            if member:
                current_name = copy.copy(member.display_name)
                ascified = unidecode(member.display_name)
                try:
                    if ctx.guild:
                        if ctx.author.guild_permissions.manage_nicknames:
                            await member.edit(nick=ascified)
                            return await ctx.send_or_reply(
                                content=f"{self.bot.emote_dict['success']} Ascified **{current_name}** to **{ascified}**",
                            )
                except Exception:
                    pass
            else:
                ascified = unidecode(string_or_member)
        except commands.MemberNotFound:
            ascified = unidecode(string_or_member)
        await ctx.send_or_reply(
            content=f"{self.bot.emote_dict['success']} Result: **{ascified}**",
        )

    @decorators.command(  # R. Danny https://github.com/Rapptz/RoboDanny/
        aliases=["unicode"],
        brief="Show information on a character.",
        implemented="2021-04-21 17:56:54.079348",
        updated="2021-05-07 05:25:52.622127",
        examples="""
                {0}charinfo hello
                {0}unicode :emoji:
                """,
    )
    async def charinfo(self, ctx, *, characters: str):
        """
        Usage: {0}charinfo <characters>
        Alias: {0}unicode
        Output:
            Shows information on the passed characters.
        Notes:
            Maximum of 25 characters per command.
        """

        def to_string(c):
            digit = f"{ord(c):x}"
            name = unicodedata.name(c, "Name not found.")
            return f'{self.bot.emote_dict["success"]} `\\U{digit:>08}`: {name} - {c} \N{EM DASH} <http://www.fileformat.info/info/unicode/char/{digit}>'

        msg = "\n".join(map(to_string, characters))
        if len(msg) > 2000:
            return await ctx.send_or_reply("Output too long to display.")
        await ctx.send_or_reply(msg)

    async def do_avatar(self, ctx, user, url):
        embed = discord.Embed(
            title=f"**{user.display_name}'s avatar.**",
            description=f"Links to `{user}'s` avatar:  "
            f"[webp]({(str(url))}) | "
            f'[png]({(str(url).replace("webp", "png"))}) | '
            f'[jpeg]({(str(url).replace("webp", "jpg"))})  ',
            color=self.bot.constants.embed,
        )
        embed.set_image(url=url)
        await ctx.send_or_reply(embed=embed)

    @decorators.command(
        aliases=["av", "pfp"],
        brief="Show a user's avatar.",
        implemented="",
        updated="",
        examples="""
                {0}avatar
                {0}av @Hecate
                {0}pfp 708584008065351681
                """,
    )
    async def avatar(self, ctx, *, user: converters.DiscordUser = None):
        """
        Usage: {0}avatar [user]
        Aliases: {0}av, {0}pfp
        Examples: {0}avatar 810377376269205546, {0}avatar Snowbot
        Output: Shows an enlarged embed of a user's avatar.
        Notes: Will default to you if no user is passed.
        """
        if user is None:
            user = ctx.author
        try:
            await self.bot.fetch_user(user.id)
        except AttributeError:
            return await ctx.send_or_reply(
                content=f"{self.bot.emote_dict['failed']} User `{user}` does not exist.",
            )
        await self.do_avatar(ctx, user, url=user.avatar_url)

    @decorators.command(
        aliases=["dav", "dpfp", "davatar"],
        brief="Show a user's default avatar.",
        implemented="2021-03-25 17:11:21.634209",
        updated="2021-05-07 05:21:05.999642",
        examples="""
                {0}dav
                {0}dpfp 810377376269205546
                {0}davatar Hecate
                {0}defaultavatar @Hecate
                """,
    )
    async def defaultavatar(self, ctx, *, user: converters.DiscordUser = None):
        """
        Usage: {0}defaultavatar [user]
        Aliases: {0}dav, {0}dpfp, {0}davatar
        Output:
            Shows an enlarged embed of a user's default avatar.
        Notes:
            Will default to you if no user is passed.
        """
        if user is None:
            user = ctx.author
        try:
            await self.bot.fetch_user(user.id)
        except AttributeError:
            return await ctx.send_or_reply(
                content=f"{self.bot.emote_dict['failed']} User `{user}` does not exist.",
            )
        await self.do_avatar(ctx, user, user.default_avatar_url)

    @decorators.command(
        aliases=["nick", "setnick"],
        brief="Edit or reset a user's nickname",
        implemented="2021-03-14 04:33:34.557509",
        updated="2021-05-07 05:17:42.736370",
        examples="""
            {0}nick Snowbot
            {0}setnick @Tester Tester2
            {0}nickname Snowbot Tester
            """,
    )
    @commands.guild_only()
    @checks.has_perms(manage_nicknames=True)
    async def nickname(self, ctx, user: converters.DiscordMember, *, nickname: str = None):
        """
        Usage: {0}nickname <user> [nickname]
        Aliases: {0}nick, {0}setnick
        Permission: Manage Nicknames
        Output:
            Edits a member's nickname on the server.
        Notes:
            Nickname will be reset if no new nickname is passed.
        """
        if user.id == ctx.guild.owner.id:
            return await ctx.send_or_reply(
                content=f"{self.bot.emote_dict['failed']} User `{user}` is the server owner. I cannot edit the nickname of the server owner.",
            )
        try:
            await user.edit(
                nick=nickname,
                reason=utils.responsible(
                    ctx.author, "Nickname edited by command execution"
                ),
            )
            message = f"{self.bot.emote_dict['success']} Nicknamed `{user}: {nickname}`"
            if nickname is None:
                message = (
                    f"{self.bot.emote_dict['success']} Reset nickname for `{user}`"
                )
            await ctx.send_or_reply(message)
        except discord.Forbidden:
            await ctx.send_or_reply(
                content=f"{self.bot.emote_dict['failed']} I do not have permission to edit `{user}'s` nickname.",
            )

    # command idea from Alex Flipnote's discord_bot.py bot
    # https://github.com/AlexFlipnote/discord_bot.py
    # Subcommands added & converted to use a paginator.

    @decorators.group(
        aliases=["search"],
        brief="Find any user using a search.",
        implemented="2021-03-14 18:18:20.175991",
        updated="2021-05-07 05:13:20.340824",
    )
    @commands.guild_only()
    @checks.has_perms(manage_messages=True)
    async def find(self, ctx):
        """
        Usage: {0}find <option> <search>
        Alias: {0}search
        Output: Users matching your search.
        Examples:
            {0}find name Hecate
            {0}find id 708584008065351681
        Options:
            duplicates
            hardmention
            hash       (Ex: 3523)
            nickname   (Ex: Hecate)
            playing    (Ex: Visual Studio Code)
            snowflake  (Ex: 708584008065351681)
            username   (Ex: Hecate)
        """
        if ctx.invoked_subcommand is None:
            return await ctx.usage("<option> <search>")

    @find.command(
        name="playing",
        aliases=["status", "activity"],
        brief="Search for users by game.",
    )
    async def find_playing(self, ctx, *, search: str):
        """
        Usage: {0}find playing <search>
        Alias: {0}find status, {0}find activity
        Output:
            All the users currently playing
            the specified activity
        """
        loop = []
        for i in ctx.guild.members:
            if i.activities and (not i.bot):
                for g in i.activities:
                    if g.name and (search.lower() in g.name.lower()):
                        loop.append(f"{i} | {type(g).__name__}: {g.name} ({i.id})")

        if not loop:
            return await ctx.fail(f"**No results.**")
        stuff = "\r\n".join(
            [f"[{str(num).zfill(2)}] {data}" for num, data in enumerate(loop, start=1)]
        )
        await ctx.send_or_reply(
            f"Found **{len(loop)}** on your search for **{search}**"
        )
        p = pagination.MainMenu(
            pagination.TextPageSource(text=str(stuff), prefix="```ini\n", max_size=800)
        )
        try:
            await p.start(ctx)
        except menus.MenuError as e:
            await ctx.send(e)

    @find.command(
        name="username", aliases=["name", "user"], brief="Search for users by username."
    )
    async def find_name(self, ctx, *, search: str):
        """
        Usage: {0}find username <search>
        Aliases:
            {0}find name
            {0}find user
        Output:
            A pagination session with all user's
            usernames that match your search
        """
        loop = [
            f"{i} ({i.id})"
            for i in ctx.guild.members
            if search.lower() in i.name.lower() and not i.bot
        ]
        if not loop:
            return await ctx.fail(f"**No results.**")
        stuff = "\r\n".join(
            [f"[{str(num).zfill(2)}] {data}" for num, data in enumerate(loop, start=1)]
        )
        await ctx.send_or_reply(
            f"Found **{len(loop)}** on your search for **{search}**"
        )
        p = pagination.MainMenu(
            pagination.TextPageSource(text=str(stuff), prefix="```ini\n", max_size=800)
        )
        try:
            await p.start(ctx)
        except menus.MenuError as e:
            await ctx.send(e)

    @find.command(
        name="nicknames",
        aliases=["nick", "nicks", "nickname"],
        brief="Search for users by nickname.",
    )
    async def find_nickname(self, ctx, *, search: str):
        """
        Usage: {0}find nicknames <search>
        Aliases:
            {0}find nicks
            {0}find nick
            {0}find nickname
        Output:
            A pagination session with all user's
            nicknames that match your search
        """
        loop = [
            f"{i.nick} | {i} ({i.id})"
            for i in ctx.guild.members
            if i.nick
            if (search.lower() in i.nick.lower()) and not i.bot
        ]
        if not loop:
            return await ctx.fail(f"**No results.**")
        stuff = "\r\n".join(
            [f"[{str(num).zfill(2)}] {data}" for num, data in enumerate(loop, start=1)]
        )
        await ctx.send_or_reply(
            f"Found **{len(loop)}** on your search for **{search}**"
        )
        p = pagination.MainMenu(
            pagination.TextPageSource(text=str(stuff), prefix="```ini\n", max_size=800)
        )
        try:
            await p.start(ctx)
        except menus.MenuError as e:
            await ctx.send(e)

    @find.command(name="id", aliases=["snowflake"], brief="Search for users by id.")
    async def find_id(self, ctx, *, search: int):
        """
        Usage: {0}find id <search>
        Alias: {0}find snowflake
        Output:
            Starts a pagination session
            showing all users who's IDs
            contain your search.
        """
        loop = [
            f"{i} | {i} ({i.id})"
            for i in ctx.guild.members
            if (str(search) in str(i.id)) and not i.bot
        ]
        if not loop:
            return await ctx.fail(f"**No results.**")
        stuff = "\r\n".join(
            [f"[{str(num).zfill(2)}] {data}" for num, data in enumerate(loop, start=1)]
        )
        await ctx.send_or_reply(
            f"Found **{len(loop)}** on your search for **{search}**"
        )
        p = pagination.MainMenu(
            pagination.TextPageSource(text=str(stuff), prefix="```ini\n", max_size=800)
        )
        try:
            await p.start(ctx)
        except menus.MenuError as e:
            await ctx.send(e)

    @find.command(
        name="hash",
        aliases=["discriminator", "discrim"],
        brief="Search for users by discriminator.",
    )
    async def find_discrim(self, ctx, *, search: str):
        """
        Usage: {0}find hash <search>
        Aliases:
            {0}find discrim
            {0}find discriminator
        Output:
            Starts a pagination session
            showing all users who's hash
            (discriminator) contain your search
        """
        if not len(search) == 4 or not re.compile("^[0-9]*$").search(search):
            return await ctx.send_or_reply(
                content="You must provide exactly 4 digits",
            )

        loop = [f"{i} ({i.id})" for i in ctx.guild.members if search == i.discriminator]
        if not loop:
            return await ctx.fail(f"**No results.**")
        stuff = "\r\n".join(
            [f"[{str(num).zfill(2)}] {data}" for num, data in enumerate(loop, start=1)]
        )
        await ctx.send_or_reply(
            f"Found **{len(loop)}** on your search for **{search}**"
        )
        p = pagination.MainMenu(
            pagination.TextPageSource(text=str(stuff), prefix="```ini\n", max_size=1250)
        )
        try:
            await p.start(ctx)
        except menus.MenuError as e:
            await ctx.send(e)

    @find.command(
        name="duplicates", aliases=["dups"], brief="Find users with identical names."
    )
    async def find_duplicates(self, ctx):
        """
        Usage: {0}find duplicates
        Alias: {0}find dups
        Output:
            Starts a pagination session
            showing all users who's nicknames
            are not unique on the server
        """
        name_list = []
        for member in ctx.guild.members:
            name_list.append(member.display_name.lower())

        name_list = Counter(name_list)
        name_list = name_list.most_common()

        loop = []
        for name_tuple in name_list:
            if name_tuple[1] > 1:
                loop.append(
                    f"Duplicates: [{str(name_tuple[1]).zfill(2)}] {name_tuple[0]}"
                )

        if not loop:
            return await ctx.fail(f"**No results.**")
        stuff = "\r\n".join(
            [f"[{str(num).zfill(2)}] {data}" for num, data in enumerate(loop, start=1)]
        )
        await ctx.send_or_reply(
            f"Found **{len(loop)}** on your search for **duplicates**"
        )
        p = pagination.MainMenu(
            pagination.TextPageSource(text=str(stuff), prefix="```ini\n", max_size=800)
        )
        try:
            await p.start(ctx)
        except menus.MenuError as e:
            await ctx.send(e)

    def _is_hard_to_mention(self, name):
        """Determine if a name is hard to mention."""
        codecs.register_error("newreplace", lambda x: (b" " * (x.end - x.start), x.end))

        encoderes, chars = codecs.getwriter("ascii").encode(name, "newreplace")

        return re.search(br"[^ ][^ ]+", encoderes) is None

    @find.command(
        name="hardmentions",
        aliases=["weird", "special", "hardmention"],
        brief="Find users with hard to mention names.",
    )
    async def hardmentions(self, ctx, username: str = None):
        """
        Usage: {0}find hardmentions [username]
        Alias:
            {0}find weird
            {0}find special
            {0}find hardmention
        Output:
            Starts a pagination session showing
            all users who use special characters
            that make their name hard to mention
        Notes:
            Specify a username kwarg, as in
            -find hardmention username
            to search for hard to mention
            usernames instead of nicknames.
        """
        if str(username).lower() in "--username":
            loop = [
                member
                for member in ctx.message.guild.members
                if self._is_hard_to_mention(str(member.name))
            ]
        else:
            loop = [
                member
                for member in ctx.message.guild.members
                if self._is_hard_to_mention(member.display_name)
            ]
        if not loop:
            return await ctx.fail(f"**No results.**")
        stuff = "\r\n".join(
            [f"[{str(num).zfill(2)}] {data}" for num, data in enumerate(loop, start=1)]
        )
        await ctx.send_or_reply(
            f"Found **{len(loop)}** on your search for **hardmentions**"
        )
        p = pagination.MainMenu(
            pagination.TextPageSource(text=str(stuff), prefix="```ini\n", max_size=800)
        )
        try:
            await p.start(ctx)
        except menus.MenuError as e:
            await ctx.send(e)

    @decorators.command(
        aliases=["id"],
        brief="Show info on a discord snowflake.",
        implemented="2021-04-05 18:28:55.338390",
        updated="2021-05-07 05:05:13.464282",
        examples="""
                {0}snowflake 81037737626
                {0}id 810377376269205546
                """,
    )
    async def snowflake(self, ctx, *, snowflake):
        """
        Usage: {0}snowflake <id>
        Alias: {0}id
        Output:
            The exact date & time that the
            discord snowflake was created
        Notes:
            Will calculate when the snowflake will
            be created if it does not yet exist.
        """
        if not snowflake.isdigit():
            raise commands.BadArgument("The `snowflake` argument must be an integer.")
        sid = int(snowflake)
        timestamp = (
            (sid >> 22) + 1420070400000
        ) / 1000  # python uses seconds not milliseconds
        cdate = datetime.utcfromtimestamp(timestamp)
        msg = "Snowflake created {}".format(
            cdate.strftime("%A, %B %d, %Y at %H:%M:%S UTC")
        )
        return await ctx.send_or_reply(msg)

    @decorators.command(
        aliases=["content"],
        brief="Shows the raw content of a message.",
        implemented="2021-03-15 03:07:09.177084",
        updated="2021-05-07 05:05:13.464282",
        examples="""
                {0}raw 840091302532087838
                {0}content 840091302532087838
                """,
    )
    async def raw(self, ctx, *, message: discord.Message):
        """
        Usage: raw [message id]
        Alias: {0}content
        Output: Raw message content
        """
        raw_data = await self.bot.http.get_message(message.channel.id, message.id)

        if message.content:
            content = message.content
            for e in message.content:
                emoji_unicode = e.encode("unicode-escape").decode("ASCII")
                content = content.replace(e, emoji_unicode)
            return await ctx.send_or_reply(
                "```\n" + "Raw Content\n===========\n\n" + content + "\n```"
            )

        transformer = pprint.pformat
        desc = ""
        for field_name in ("embeds", "attachments"):
            data = raw_data[field_name]

            if not data:
                continue

            total = len(data)
            for current, item in enumerate(data, start=1):
                title = f"Raw {field_name} ({current}/{total})"
                desc += f"{title}\n\n{transformer(item)}\n"
        p = pagination.MainMenu(pagination.TextPageSource(desc, prefix="```"))

        try:
            await p.start(ctx)
        except menus.MenuError as e:
            await ctx.send_or_reply(str(e))

    @decorators.command(brief="Snipe a deleted message.", aliases=["retrieve"])
    @commands.guild_only()
    @checks.has_perms(manage_messages=True)
    async def snipe(self, ctx, *, member: converters.DiscordMember = None):
        """
        Usage: -snipe [user]
        Alias: -retrieve
        Output: Fetches a deleted message
        Notes:
            Will fetch a messages sent by a specific user if specified
        """
        if member is None:
            query = """SELECT author_id, message_id, content, timestamp FROM messages WHERE channel_id = $1 AND deleted = True ORDER BY unix DESC;"""
            result = await self.bot.cxn.fetchrow(query, ctx.channel.id) or None
        else:
            query = """SELECT author_id, message_id, content, timestamp FROM messages WHERE channel_id = $1 AND author_id = $2 AND deleted = True ORDER BY unix DESC;"""
            result = (
                await self.bot.cxn.fetchrow(query, ctx.channel.id, member.id) or None
            )

        if result is None:
            return await ctx.send_or_reply(
                content=f"{self.bot.emote_dict['warn']} There is nothing to snipe.",
            )

        author = result[0]
        message_id = result[1]
        content = result[2]
        timestamp = result[3]

        author = self.bot.get_user(author)

        if str(content).startswith("```"):
            content = f"**__Message Content__**\n {str(content)}"
        else:
            content = f"**__Message Content__**\n ```fix\n{str(content)}```"

        embed = discord.Embed(
            description=f"**Author:**  {author.mention}, **ID:** `{author.id}`\n"
            f"**Channel:** {ctx.channel.mention} **ID:** `{ctx.channel.id}`\n"
            f"**Server:** `{ctx.guild.name}` **ID:** `{ctx.guild.id},`\n\n"
            f"**Sent at:** `{timestamp}`\n\n"
            f"{content}",
            color=self.bot.constants.embed,
            timestamp=datetime.utcnow(),
        )
        embed.set_author(
            name="Deleted Message Retrieved",
            icon_url="https://media.discordapp.net/attachments/506838906872922145/603642595419357190/messagedelete.png",
        )
        embed.set_footer(text=f"Message ID: {message_id}")
        await ctx.send_or_reply(embed=embed)

    @decorators.command(
        aliases=["bitly"],
        brief="Shorten URLs to bitly links.",
        implemented="2021-04-15 05:17:23.532870",
        updated="2021-05-07 05:02:01.750279",
        examples="""
                {0}shorten https://discord.gg/947ramn
                {0}bitly https://discord.gg/947ramn
                """,
    )
    async def shorten(self, ctx, url):
        """
        Usage: {0}shorten <url>
        Alias: {0}bitly
        Output:
            A bitly url that will redirect to the
            destination of the url that was passed.
        """
        params = {"access_token": self.bot.constants.bitly, "longUrl": url}

        response = await self.bot.get(
            "https://api-ssl.bitly.com/v3/shorten", params=params
        )
        resp = json.loads(response)
        if resp["status_code"] != 200:
            return await ctx.send_or_reply(
                content=f"{self.bot.emote_dict['failed']} Invalid URL received.",
            )
        else:
            await ctx.send_or_reply(
                content=f"{self.bot.emote_dict['success']} Successfully shortened URL:\t"
                "<{}>".format(resp["data"]["url"]),
            )

    async def do_color(self, value):
        values = (
            value.replace(",", " ")
            .replace("(", " ")
            .replace(")", " ")
            .replace("%", " ")
            .split()
        )
        color_values = []
        for x in values:
            if x.lower().startswith(("0x", "#")) or any(
                (y in x.lower() for y in "abcdef")
            ):
                # We likely have a hex value
                try:
                    color_values.append(
                        int(x.lower().replace("#", "").replace("0x", ""), 16)
                    )
                except:
                    pass  # Bad value - ignore
            else:
                # Try to convert it to an int
                try:
                    color_values.append(int(x))
                except:
                    pass  # Bad value - ignore
        original_type = "hex" if len(color_values) == 1 else None
        if original_type is None:
            return False
        # Verify values
        max_val = int("FFFFFF", 16)

        if not all((0 <= x <= max_val for x in color_values)):
            return False
        if original_type == "hex":
            color = color_values[0]
        return color

    async def do_msg_check(self, ctx, embed):
        def message_check(m):
            return (
                m.author.id == ctx.author.id
                and m.channel == ctx.channel
                and m.content != ""
            )

        try:
            msg = await self.bot.wait_for("message", check=message_check, timeout=60.0)
            self.msg_collection.append(msg.id)
        except asyncio.TimeoutError:
            msg = await ctx.fail(f"Embed session timed out.")
            self.msg_collection.append(msg.id)
            await asyncio.sleep(5)
            return

        if msg.content.lower() == "none":
            msg = discord.Embed.Empty
            return msg
        elif msg.content.lower() == "cancel":
            msg = await ctx.success(f"Embed session cancelled.")
            self.msg_collection.append(msg.id)
            return
        elif msg.content.lower() == "end":
            msg = await ctx.success(f"Embed session ended.")
            self.msg_collection.append(msg.id)
            try:
                await ctx.send_or_reply(embed=embed)
                await self.do_cleanup(ctx)
            except discord.HTTPException:
                pass
            return
        else:
            msg = msg.content
        return msg

    @decorators.command(
        aliases=["embedder"],
        brief="Create an embed interactively.",
        description="============================================\n"
        "Hello there! Welcome to my interactive embed creating session.\n"
        "Type `cancel` at any time to cancel the session.\n"
        "Type `none` to leave any portion of the embed empty.\n"
        "Type `end` at any time to finalize the embed and end the session.\n"
        "============================================\n",
        implemented="2021-04-26 03:38:21.466614",
        updated="2021-05-07 04:58:48.454818",
        examples="""
                {0}embed
                {0}embedder
                """,
    )
    @checks.bot_has_perms(embed_links=True)
    @checks.has_perms(manage_messages=True, embed_links=True)
    async def embed(self, ctx):
        """
        Usage: {0}embed
        Alias: {0}embedder
        Permissions: Manage Messages, Embed Links
        Output:
            Starts an interactive embed
            creating session.
        Instructions:
            Use "cancel" at any time to cancel the session
            Use "none" at any time to skip the value
            Use "end" at any time to end the session and send the embed.
        Notes:
            If the bot has the Manage Messages permission,
            it will prompt you for a cleanup option after
            completion. This will purge all messages sent as
            a result of this embed session and leave the embed.
        """

        m = await ctx.send_or_reply(
            f"{ctx.command.description}\nEnter your embed title:"
        )
        self.msg_collection.append(m.id)
        embed = discord.Embed()

        msg = await self.do_msg_check(ctx, embed)
        if msg is None:
            return
        if len(str(msg)) > pagination.TITLE_LIMIT:
            check = False
            while check is False:
                m = await ctx.fail(
                    f"Title too long ({len(msg)}/{pagination.TITLE_LIMIT}).\nPlease re-enter a shorter embed title:"
                )
                self.msg_collection.append(m.id)
                msg = await self.do_msg_check(ctx, embed)
                if msg is None or isinstance(msg, discord.embeds._EmptyEmbed):
                    break
                if not len(msg) > pagination.TITLE_LIMIT:
                    check = True
        embed.title = msg
        if not isinstance(msg, discord.embeds._EmptyEmbed):
            m = await ctx.send_or_reply("Enter your embed's click url:")
            self.msg_collection.append(m.id)
            msg = await self.do_msg_check(ctx, embed)

            if msg is None:
                return
            if not isinstance(msg, discord.embeds._EmptyEmbed):
                if not self.uregex.fullmatch(msg):
                    check = False
                    while check is False:
                        m = await ctx.fail(
                            "Invalid URL schema.\nEnter your embed's click url:"
                        )
                        self.msg_collection.append(m.id)
                        msg = await self.do_msg_check(ctx, embed)
                        if msg is None or isinstance(msg, discord.embeds._EmptyEmbed):
                            break
                        if self.uregex.fullmatch(msg):
                            check = True
            if msg is None:
                return
            embed.url = msg

        m = await ctx.send_or_reply(
            "Enter your embed's color (Must be in HEX. Ex: #ff00ff. None for default):"
        )
        self.msg_collection.append(m.id)
        msg = await self.do_msg_check(ctx, embed)
        if msg is None:
            return
        if isinstance(msg, discord.embeds._EmptyEmbed):
            color = random.choice([x[1] for x in self.color_dict.items()])
        else:
            color = await self.do_color(msg)
            while color is False:
                m = await ctx.fail(
                    "Invalid color value.\nEnter your embed's color value:"
                )
                self.msg_collection.append(m.id)
                msg = await self.do_msg_check(ctx, embed)
                if msg is None or isinstance(msg, discord.embeds._EmptyEmbed):
                    break
                color = await self.do_color(msg)

        if msg is None:
            return
        embed.color = color

        m = await ctx.send_or_reply("Enter your embed author's name:")
        self.msg_collection.append(m.id)
        msg = await self.do_msg_check(ctx, embed)
        if msg is None:
            return
        author_name = msg
        if len(str(msg)) > pagination.AUTHOR_LIMIT:
            check = False
            while check is False:
                m = await ctx.fail(
                    f"Author name too long ({len(msg)}/{pagination.AUTHOR_LIMIT}).\nPlease re-enter a shorter author name:"
                )
                self.msg_collection.append(m.id)
                msg = await self.do_msg_check(ctx, embed)
                if msg is None or isinstance(msg, discord.embeds._EmptyEmbed):
                    break
                if not len(msg) > pagination.AUTHOR_LIMIT:
                    check = True

        if not isinstance(author_name, discord.embeds._EmptyEmbed):
            embed.set_author(name=author_name)

            m = await ctx.send_or_reply(
                "Enter your embed author's icon (must be an image url):"
            )
            self.msg_collection.append(m.id)
            msg = await self.do_msg_check(ctx, embed)
            if msg is None:
                return
            if not isinstance(msg, discord.embeds._EmptyEmbed):
                if not self.uregex.fullmatch(msg):
                    check = False
                    while check is False:
                        m = await ctx.fail(
                            "Invalid URL schema.\nEnter your embed author's icon (must be an image url):"
                        )
                        self.msg_collection.append(m.id)
                        msg = await self.do_msg_check(ctx, embed)
                        if msg is None or isinstance(msg, discord.embeds._EmptyEmbed):
                            break
                        if self.uregex.fullmatch(msg):
                            check = True
            if msg is None:
                return
            author_icon = msg
            embed.set_author(name=author_name, icon_url=author_icon)

            m = await ctx.send_or_reply("Enter your embed author's click URL:")
            self.msg_collection.append(m.id)
            msg = await self.do_msg_check(ctx, embed)
            if msg is None:
                return
            if not isinstance(msg, discord.embeds._EmptyEmbed):
                if not self.uregex.fullmatch(msg):
                    check = False
                    while check is False:
                        m = await ctx.fail(
                            "Invalid URL schema.\nEnter your embed author's click URL (must be a valid http(s) URL):"
                        )
                        self.msg_collection.append(m.id)
                        msg = await self.do_msg_check(ctx, embed)
                        if msg is None or isinstance(msg, discord.embeds._EmptyEmbed):
                            break
                        if self.uregex.fullmatch(msg):
                            check = True
            if msg is None:
                return
            author_url = msg
            embed.set_author(name=author_name, url=author_url, icon_url=author_icon)

        m = await ctx.send_or_reply("Enter your embed's description:")
        self.msg_collection.append(m.id)
        msg = await self.do_msg_check(ctx, embed)
        if msg is None:
            return
        embed.description = msg

        m = await ctx.send_or_reply("Enter your embed's footer:")
        self.msg_collection.append(m.id)
        msg = await self.do_msg_check(ctx, embed)
        if msg is None:
            return
        footer_text = msg
        if not isinstance(footer_text, discord.embeds._EmptyEmbed):
            embed.set_footer(text=footer_text)

            m = await ctx.send_or_reply(
                "Enter your embed footer's icon URL (must be a valid http(s) URL):"
            )
            self.msg_collection.append(m.id)
            msg = await self.do_msg_check(ctx, embed)
            if msg is None:
                return
            if not isinstance(msg, discord.embeds._EmptyEmbed):
                if not self.uregex.fullmatch(msg):
                    check = False
                    while check is False:
                        m = await ctx.fail(
                            "Invalid URL schema.\nEnter your embed footer's icon URL (must be a valid http/https url):"
                        )
                        self.msg_collection.append(m.id)
                        msg = await self.do_msg_check(ctx, embed)
                        if msg is None or isinstance(msg, discord.embeds._EmptyEmbed):
                            break
                        if self.uregex.fullmatch(msg):
                            check = True
            if msg is None:
                return
            footer_icon = msg

            embed.set_footer(text=footer_text, icon_url=footer_icon)

        m = await ctx.send_or_reply("Enter the number of fields to add to your embed:")
        self.msg_collection.append(m.id)
        msg = await self.do_msg_check(ctx, embed)
        if msg is None:
            return
        if not isinstance(msg, discord.embeds._EmptyEmbed):
            if not msg.isdigit():
                check = False
                while check is False:
                    m = await ctx.fail(
                        "Field count must be a positive integer.\nEnter the number of fields to add to your embed:"
                    )
                    self.msg_collection.append(m.id)
                    msg = await self.do_msg_check(ctx, embed)
                    if msg is None or isinstance(msg, discord.embeds._EmptyEmbed):
                        break
                    if msg.isdigit():
                        check = True
            if int(msg) > pagination.FIELDS_LIMIT:
                check = False
                while check is False:
                    m = await ctx.fail(
                        f"Field count too large ({int(msg)}/{pagination.FIELDS_LIMIT}).\nPlease re-enter a smaller number:"
                    )
                    self.msg_collection.append(m.id)
                    msg = await self.do_msg_check(ctx, embed)
                    if msg is None or isinstance(msg, discord.embeds._EmptyEmbed):
                        break
                    if not int(msg) > pagination.FIELDS_LIMIT:
                        check = True

            field_count = int(msg)
            current_fields = 0
            while current_fields < field_count:
                current_fields += 1
                m = await ctx.send_or_reply(
                    f"Enter the name for field #{current_fields}:"
                )
                self.msg_collection.append(m.id)
                msg = await self.do_msg_check(ctx, embed)
                if msg is None:
                    return
                if isinstance(msg, discord.embeds._EmptyEmbed):
                    msg = "‏‏‎‏‏‎\u200f\u200f\u200e \u200e"
                if len(str(msg)) > pagination.FIELD_NAME_LIMIT:
                    check = False
                    while check is False:
                        m = await ctx.fail(
                            f"Field name too long ({len(msg)}/{pagination.FIELD_NAME_LIMIT}).\nPlease re-enter a shorter field name:"
                        )
                        self.msg_collection.append(m.id)
                        msg = await self.do_msg_check(ctx, embed)
                        if msg is None or isinstance(msg, discord.embeds._EmptyEmbed):
                            break
                        if not len(msg) > pagination.FIELD_NAME_LIMIT:
                            check = True

                field_name = msg

                m = await ctx.send_or_reply(
                    f"Enter the value for field #{current_fields}:"
                )
                self.msg_collection.append(m.id)
                msg = await self.do_msg_check(ctx, embed)
                if msg is None:
                    return
                if isinstance(msg, discord.embeds._EmptyEmbed):
                    msg = "‏‏‏‏‎\u200f\u200f\u200e \u200e"
                if len(str(msg)) > pagination.FIELD_VALUE_LIMIT:
                    check = False
                    while check is False:
                        m = await ctx.fail(
                            f"Field name too long ({len(msg)}/{pagination.FIELD_VALUE_LIMIT}).\nPlease re-enter a shorter field value:"
                        )
                        self.msg_collection.append(m.id)
                        msg = await self.do_msg_check(ctx, embed)
                        if msg is None or isinstance(msg, discord.embeds._EmptyEmbed):
                            break
                        if not len(msg) > pagination.FIELD_VALUE_LIMIT:
                            check = True
                field_value = msg

                embed.add_field(name=field_name, value=field_value, inline=False)

        await ctx.send_or_reply(embed=embed)
        await self.do_cleanup(ctx)

    async def do_cleanup(self, ctx):
        if ctx.guild:
            if ctx.guild.me.permissions_in(ctx.channel).manage_messages:
                p = await pagination.Confirmation(
                    f"Do you want me to clean all messages from the embed session and leave only the resulting embed?"
                ).prompt(ctx)
                if p:
                    mess = await ctx.send_or_reply(
                        f"{self.bot.emote_dict['loading']} Deleting {len(self.msg_collection)} messages..."
                    )

                    def purge_checker(m):
                        return m.id in self.msg_collection

                    deleted = await ctx.channel.purge(limit=200, check=purge_checker)
                    await mess.edit(
                        content=f"{self.bot.emote_dict['trash']} Deleted {len(deleted)} messages."
                    )
                    self.msg_collection.clear()
                else:
                    await ctx.send_or_reply(f"Cancelled.")
            else:
                self.msg_collection.clear()
        else:
            self.msg_collection.clear()

    @decorators.command(
        aliases=["math", "calc"],
        brief="Calculate a math formula.",
        implemented="2021-04-19 03:04:41.003346",
        updated="2021-05-07 04:54:31.680310",
        examples="""
            {0}calc (2 + 2) - 4 / 5
            {0}math sqrt(532)
            {0}calculate log(2)
            {0}calc sin(PI * E)
            {0}math arctan(PI + 30)
            """,
    )
    async def calculate(self, ctx, *, formula):
        """
        Usage: calculate <formula>
        Aliases: {0}math, {0}calc
        Output:
            The caluculated result of your input formula
        Keys:
            exponentiation: '^'
            multiplication: 'x' | '*'
            division: '/'
            addition: '+' | '-'
            integer: ['+' | '-'] '0'..'9'+
            constants: PI | E
        Functions:  # To be used in the form {0}calc function(expression)
            sqrt, log, sin, cos, tan, arcsin, arccos,
            arctan, sinh, cosh, tanh, arcsinh, arccosh,
            arctanh, abs, trunc, round, sgn
        """
        formula = formula.replace("*", "x")
        try:
            answer = NumericStringParser().eval(formula)
            await ctx.message.add_reaction(self.bot.emote_dict["success"])
        except Exception:
            msg = '{} I couldn\'t parse "{}"\n'.format(
                self.bot.emote_dict["failed"],
                formula.replace("*", "\\*").replace("`", "\\`").replace("_", "\\_"),
            )
            msg += "```yaml\n" + ctx.command.help + "```"
            return await ctx.send_or_reply(msg)

        if int(answer) == answer:
            # Check if it's a whole number and cast to int if so
            answer = int(answer)

        # Say message
        await ctx.send_or_reply(content="{} = {}".format(formula, answer))

    # Color helper functions
    def _rgb_to_hex(self, r, g, b):
        return "#{:02x}{:02x}{:02x}".format(r, g, b).upper()

    def _hex_to_rgb(self, _hex):
        _hex = _hex.lower().replace("#", "").replace("0x", "")
        l_hex = len(_hex)
        return tuple(
            int(_hex[i : i + l_hex // 3], 16) for i in range(0, l_hex, l_hex // 3)
        )

    def _hex_to_cmyk(self, _hex):
        return self._rgb_to_cmyk(*self._hex_to_rgb(_hex))

    def _cmyk_to_hex(self, c, m, y, k):
        return self._rgb_to_hex(*self._cmyk_to_rgb(c, m, y, k))

    def _cmyk_to_rgb(self, c, m, y, k):
        c, m, y, k = [float(x) / 100.0 for x in tuple([c, m, y, k])]
        return tuple(
            [
                round(255.0 - ((min(1.0, x * (1.0 - k) + k)) * 255.0))
                for x in tuple([c, m, y])
            ]
        )

    def _rgb_to_cmyk(self, r, g, b):
        c, m, y = [1 - x / 255 for x in tuple([r, g, b])]
        min_cmy = min(c, m, y)
        return (
            tuple([0, 0, 0, 100])
            if all(x == 0 for x in [r, g, b])
            else tuple(
                [
                    round(x * 100)
                    for x in [(x - min_cmy) / (1 - min_cmy) for x in tuple([c, m, y])]
                    + [min_cmy]
                ]
            )
        )

    def _hex_int_to_tuple(self, _hex):
        return (_hex >> 16 & 0xFF, _hex >> 8 & 0xFF, _hex & 0xFF)

    def _check_hex(self, hex_string):
        # Remove 0x/0X
        hex_string = hex_string.replace("0x", "").replace("0X", "")
        hex_string = re.sub(r"[^0-9A-Fa-f]+", "", hex_string)
        return hex_string


class NumericStringParser(object):
    """
    Most of this code comes from the fourFn.py pyparsing example
    """

    def pushFirst(self, strg, loc, toks):
        self.exprStack.append(toks[0])

    def pushUMinus(self, strg, loc, toks):
        if toks and toks[0] == "-":
            self.exprStack.append("unary -")

    def __init__(self):
        """
        Usage: calculate <expression>
        Aliases: -math, -calc
        Output: The result of your input
        Examples:
            -calc 2 + 2 + 4 + 5
            -calc sqrt(532)
            -calc log(2)
            -calc sin(PI * E)
        exponentiation: '^'
        multiplication: 'x' | '*'
        division: '/'
        addition: '+' | '-'
        integer: ['+' | '-'] '0'..'9'+
        constants: PI | E
        Functions:  # To be used in the form -calc function(expression)
            sqrt
            log
            sin
            cos
            tan
            arcsin
            arccos
            arctan
            sinh
            cosh
            tanh
            arcsinh
            arccosh
            arctanh
            abs
            trunc
            round
            sgn
        """
        point = Literal(".")
        e = CaselessLiteral("E")
        fnumber = Combine(
            Word("+-" + nums, nums)
            + Optional(point + Optional(Word(nums)))
            + Optional(e + Word("+-" + nums, nums))
        )
        ident = Word(alphas, alphas + nums + "_$")
        plus = Literal("+")
        minus = Literal("-")
        mult = Literal("x")
        div = Literal("/")
        lpar = Literal("(").suppress()
        rpar = Literal(")").suppress()
        addop = plus | minus
        multop = mult | div
        expop = Literal("^")
        pi = CaselessLiteral("PI")
        expr = Forward()
        atom = (
            (
                Optional(oneOf("- +"))
                + (pi | e | fnumber | ident + lpar + expr + rpar).setParseAction(
                    self.pushFirst
                )
            )
            | Optional(oneOf("- +")) + Group(lpar + expr + rpar)
        ).setParseAction(self.pushUMinus)
        # by defining exponentiation as "atom [ ^ factor ]..." instead of
        # "atom [ ^ atom ]...", we get right-to-left exponents, instead of left-to-right
        # that is, 2^3^2 = 2^(3^2), not (2^3)^2.
        factor = Forward()
        factor << atom + ZeroOrMore((expop + factor).setParseAction(self.pushFirst))
        term = factor + ZeroOrMore((multop + factor).setParseAction(self.pushFirst))
        expr << term + ZeroOrMore((addop + term).setParseAction(self.pushFirst))
        # addop_term = ( addop + term ).setParseAction( self.pushFirst )
        # general_term = term + ZeroOrMore( addop_term ) | OneOrMore( addop_term)
        # expr <<  general_term
        self.bnf = expr
        # map operator symbols to corresponding arithmetic operations
        epsilon = 1e-12
        self.opn = {
            "+": operator.add,
            "-": operator.sub,
            "x": operator.mul,
            "/": operator.truediv,
            "^": operator.pow,
        }
        self.fn = {
            "sqrt": math.sqrt,
            "log": math.log,
            "sin": math.sin,
            "cos": math.cos,
            "tan": math.tan,
            "arcsin": math.asin,
            "arccos": math.acos,
            "arctan": math.atan,
            "sinh": math.sinh,
            "cosh": math.cosh,
            "tanh": math.tanh,
            "arcsinh": math.asinh,
            "arccosh": math.acosh,
            "arctanh": math.atanh,
            "abs": abs,
            "trunc": lambda a: int(a),
            "round": round,
            "sgn": lambda a: abs(a) > epsilon and cmp_to_key(a, 0) or 0,
        }

    def evaluateStack(self, s):
        op = s.pop()
        if op == "unary -":
            return -self.evaluateStack(s)
        if op in "+-x/^":
            op2 = self.evaluateStack(s)
            op1 = self.evaluateStack(s)
            return self.opn[op](op1, op2)
        elif op == "PI":
            return math.pi  # 3.1415926535
        elif op == "E":
            return math.e  # 2.718281828
        elif op in self.fn:
            return self.fn[op](self.evaluateStack(s))
        elif op[0].isalpha():
            return 0
        else:
            return float(op)

    def eval(self, num_string, parseAll=True):
        self.exprStack = []
        results = self.bnf.parseString(num_string, parseAll)
        val = self.evaluateStack(self.exprStack[:])
        return val
