import base64
import random
import codecs
import discord
import json
import math
import operator
import pprint
import re
import os
import copy
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

from utilities import converters, pagination, permissions, utils


def setup(bot):
    bot.add_cog(Utility(bot))

# Thanks goes to Stella bot for some of these features.

class Utility(commands.Cog):
    """
    Module for general utilities.
    """

    def __init__(self, bot):
        self.bot = bot
        self.emote_dict = bot.emote_dict


    def parse_date(self, token):
        token_epoch = 1293840000
        bytes_int = base64.standard_b64decode(token + "==")
        decoded = int.from_bytes(bytes_int, "big")
        timestamp = datetime.utcfromtimestamp(decoded)

        # sometime works
        if timestamp.year < 2015:
            timestamp = datetime.utcfromtimestamp(decoded + token_epoch)
        return timestamp

    @commands.command(aliases=["pt", "parsetoken"], brief="Decode a discord token.")
    async def ptoken(self, ctx, token = None):
        """
        Usage: -ptoken <token>
        Aliases: -pt, -parsetoken
        Output:
            Decodes the token by splitting the token into 3 parts.
        Notes:
            First part is a user id where it was decoded from base 64 into str. The second part
            is the creation of the token, which is converted from base 64 into int. The last part
            cannot be decoded due to discord encryption.
        """
        if token is None:
            return await ctx.send_or_reply(f"Usage: `{ctx.prefix}ptoken <token>`")
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
                        f"**Token Created:** `{timestamp}`"
        )
        embed.color = self.bot.constants.color
        embed.set_thumbnail(url=member.avatar_url)
        await ctx.send_or_reply(embed=embed)

    @commands.command(aliases=["gt", "generatetoken"],
                      brief="Generate a discord token for a user.")
    async def gtoken(self, ctx, member: Union[discord.Member, discord.User] = None):
        """
        Usage: -gtoken <user>
        Aliases: -gt, -generatetoken
        Output:
            Generates a discord token for a user
        Notes:
            Defaults to command author
        """
        if not member:
            member = ctx.author
        byte_first = str(member.id).encode('ascii')
        first_encode = base64.b64encode(byte_first)
        first = first_encode.decode('ascii')
        time_rn = datetime.utcnow()
        epoch_offset = int(time_rn.timestamp())
        bytes_int = int(epoch_offset).to_bytes(10, "big")
        bytes_clean = bytes_int.lstrip(b"\x00")
        unclean_middle = base64.standard_b64encode(bytes_clean)
        middle = unclean_middle.decode('utf-8').rstrip("==")
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
            title=f"{member.display_name}'s token",
            description=f"**User:** `{member}`\n"
                        f"**ID:** `{member.id}`\n"
                        f"**Bot:** `{member.bot}`\n"
                        f"**Token created:** `{time_rn}`\n"
                        f"**Generated token:** `{complete}`\n"
        )
        embed.color = self.bot.constants.embed
        embed.set_thumbnail(url=member.avatar_url)
        await ctx.send_or_reply(embed=embed)

    @commands.command(brief="Find the first message of a reply thread.")
    async def replies(self, ctx, message: discord.Message):
        """
        Usage: -replies <message>
        Output:
            The author, replies, message
            and jump_url to the message.
        """
        if message is None:
            return await ctx.send_or_reply(f"Usage: `{ctx.prefix}replies <message>`")
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
        em.description =   (
            f"**Original:** `{msg.author}`\n"
            f"**Message:** {msg.clean_content}\n"
            f"**Replies:** `{count}`\n"
            f"**Origin:** [`jump`]({msg.jump_url})"
        )
        
        await ctx.send_or_reply(embed=em)

    @commands.command(name="type",
                      aliases=["objtype", "findtype"],
                      brief="Find the type of a discord object.")
    async def type_(self, ctx, obj_id: discord.Object = None):
        """
        Usage: -type <discord object>
        Aliases: -findtype, -objtype
        Output:
            Attemps to find the type of the object presented.
        """
        if obj_id is None:
            return await ctx.send_or_reply(f"Usage: `{ctx.prefix}findtype <discord object>`")
        async def found_message(type_id):
            embed = discord.Embed(title="Result")
            embed.description=(
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

        m = await self.bot.http._HTTPClient__session.get(f"https://cdn.discordapp.com/emojis/{obj_id.id}")
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
            return await ctx.send_or_reply(f"{self.bot.emote_dict['failed']} I could not find that object.")

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


    @commands.command(brief="Show a given color and its values.")
    async def color(self, ctx, *, value=None):
        """
        Usage: -color <value>
        Output:
            View info on a rgb, hex or cmyk color and their
            values in other formats
        Examples:
            -color #3399cc
            -color rgb(3, 4, 5)
            -color cmyk(1, 2, 3, 4)
            -color 0xFF00FF
        Notes:
            Will try to convert value into role
            and return role color before searching
            for hex, decimal, rgb, and cmyk
        """
        async with ctx.channel.typing():
            if not value:
                return await ctx.send_or_reply(
                    content="Usage: `{}color [value]`".format(ctx.prefix),
                )
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
                        content=f"{self.bot.emote_dict['failed']} Incorrect number of color values!  Hex takes 1, RGB takes 3, CMYK takes 4.",
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
                        content="Value out of range!  Valid ranges are from `#000000` to `#FFFFFF` for Hex, `0` to `255` for RGB, and `0` to `100` for CMYK.",
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
            file_path = "././data/wastebin/color.png"
            try:
                image = Image.new(
                    mode="RGB", size=(256, 256), color=self._hex_int_to_tuple(color)
                )
                image.save(file_path)
                ext = file_path.split(".")
                fname = "Upload." + ext[-1] if len(ext) > 1 else "Upload"
                dfile = discord.File(file_path, filename=fname)
                em.set_image(url="attachment://" + fname)
                await ctx.send_or_reply(embed=em, file=dfile)
            except Exception as e:
                raise
            if os.path.exists(file_path):
                os.remove(file_path)


    @commands.command(brief="Dehoist a specified user.")
    @permissions.bot_has_permissions(manage_nicknames=True)
    @permissions.has_permissions(manage_nicknames=True)
    async def dehoist(self, ctx, user: discord.Member = None):
        """
        Usage: -dehoist <user>
        Permission: Manage Nicknames
        Output:
            Re nicknames a single user who hoists
            themselves at the top of the member
            list by using special characters
        Notes:
            To dehoist all users, use -massdehoist
            instead.
        """
        if user is None:
            return await ctx.send_or_reply(f"Usage: `{ctx.prefix}dehoist <user>`")
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
            await ctx.send_or_reply(content=f"{self.bot.emote_dict['failed']} User `{user}` is not hoisting.",
            )

    @commands.command(brief="Convert special characters to ascii.")
    async def ascify(self, ctx, *, str_or_member=None):
        """
        Usage: -ascify <string/member>
        Aliases: -ascii, -normalize
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
            member = await commands.MemberConverter().convert(ctx, str_or_member)
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
                ascified = unidecode(str_or_member)
        except commands.MemberNotFound:
            ascified = unidecode(str_or_member)
        await ctx.send_or_reply(
            content=f"{self.bot.emote_dict['success']} Result: **{ascified}**",
        )

    @commands.command(brief="Show information on a character.")
    async def charinfo(self, ctx, *, characters: str):
        """Shows you information about a number of characters.

        Only up to 25 characters at a time.
        """

        def to_string(c):
            digit = f"{ord(c):x}"
            name = unicodedata.name(c, "Name not found.")
            return f'{self.bot.emote_dict["success"]} `\\U{digit:>08}`: {name} - {c} \N{EM DASH} <http://www.fileformat.info/info/unicode/char/{digit}>'

        msg = "\n".join(map(to_string, characters))
        if len(msg) > 2000:
            return await ctx.send_or_reply("Output too long to display.")
        await ctx.send_or_reply(msg)

    @commands.command(brief="Show a user's avatar.", aliases=["av", "pfp"])
    async def avatar(self, ctx, *, user: converters.DiscordUser = None):
        """
        Usage:    -avatar [user]
        Aliases:  -av, -pfp
        Examples: -avatar 810377376269205546, -avatar Snowbot
        Output:   Shows an enlarged embed of a user's avatar.
        Notes:    Will default to yourself if no user is passed.
        """
        if user is None:
            user = ctx.author
        try:
            await self.bot.fetch_user(user.id)
        except AttributeError:
            return await ctx.send_or_reply(content=f"{self.bot.emote_dict['failed']} User `{user}` does not exist.",
            )
        await self.do_avatar(ctx, user, url=user.avatar_url)

    @commands.command(
        brief="Show a user's default avatar.", aliases=["dav", "dpfp", "davatar"]
    )
    async def defaultavatar(self, ctx, *, user: converters.DiscordUser = None):
        """
        Usage:    -defaultavatar [user]
        Aliases:  -dav, -dpfp, davatar
        Examples: -defaultavatar 810377376269205546, -davatar Snowbot
        Output:   Shows an enlarged embed of a user's default avatar.
        Notes:    Will default to yourself if no user is passed.
        """
        if user is None:
            user = ctx.author
        try:
            await self.bot.fetch_user(user.id)
        except AttributeError:
            return await ctx.send_or_reply(content=f"{self.bot.emote_dict['failed']} User `{user}` does not exist.",
            )
        await self.do_avatar(ctx, user, user.default_avatar_url)

    @commands.command(
        aliases=["nick", "setnick"], brief="Edit or reset a user's nickname"
    )
    @commands.guild_only()
    @permissions.has_permissions(manage_nicknames=True)
    async def nickname(self, ctx, user: discord.Member, *, nickname: str = None):
        """
        Usage:      -nickname <member> [nickname]
        Aliases:    -nick, -setnick
        Examples:   -nickname Snowbot NGC, -nickname Snowbot
        Permission: Manage Nicknames
        Output:     Edits a member's nickname on the server.
        Notes:      Nickname will reset if no member is passed.
        """
        if user is None:
            return await ctx.send_or_reply(content=f"Usage: `{ctx.prefix}nickname <user> <nickname>`",
            )
        if user.id == ctx.guild.owner.id:
            return await ctx.send_or_reply(content=f"{self.emote_dict['failed']} User `{user}` is the server owner. I cannot edit the nickname of the server owner.",
            )
        try:
            await user.edit(
                nick=nickname,
                reason=utils.responsible(
                    ctx.author, "Nickname edited by command execution"
                ),
            )
            message = f"{self.emote_dict['success']} Nicknamed `{user}: {nickname}`"
            if nickname is None:
                message = f"{self.emote_dict['success']} Reset nickname for `{user}`"
            await ctx.send_or_reply(message)
        except discord.Forbidden:
            await ctx.send_or_reply(content=f"{self.emote_dict['failed']} I do not have permission to edit `{user}'s` nickname.",
            )

    # command mostly from Alex Flipnote's discord_bot.py bot
    # I'll rewrite his "prettyresults" method to use a paginator later.
    # https://github.com/AlexFlipnote/discord_bot.py

    @commands.group(brief="Find any user using a search.", aliases=["search"])
    @commands.guild_only()
    @permissions.has_permissions(manage_messages=True)
    async def find(self, ctx):
        """
        Usage: -find <method> <search>
        Alias: -search
        Output: Users matching your search.
        Examples: 
            -find name Hecate
            -find id 70858400
        Methods:
            duplicates
            hardmention
            hash       (Ex: 3523)
            nickname   (Ex: Hecate)
            playing    (Ex: Visual Studio Code)
            snowflake  (Ex: 708584008065351681)
            username   (Ex: Hecate)
        """
        if ctx.invoked_subcommand is None:
            return await ctx.usage("<method> <search>")

    @find.command(name="playing", aliases=["status", "activity"], brief="Search for users by game.")
    async def find_playing(self, ctx, *, search: str):
        """
        Usage: -find playing <activity>
        Alias: -find status, -find activity
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

        await utils.prettyResults(
            ctx,
            "playing",
            f"Found **{len(loop)}** on your search for **{search}**",
            loop,
        )

    @find.command(name="username", aliases=["name","user"], brief="Search for users by username.")
    async def find_name(self, ctx, *, search: str):
        """
        Usage: -find username <search>
        Aliases:
            -find name
            -find user
        Output:
            A pagination session with all user's
            usernames that match your search
        """
        loop = [
            f"{i} ({i.id})"
            for i in ctx.guild.members
            if search.lower() in i.name.lower() and not i.bot
        ]
        await utils.prettyResults(
            ctx, "name", f"Found **{len(loop)}** on your search for **{search}**", loop
        )

    @find.command(name="nicknames", aliases=["nick", "nicks", "nickname"], brief="Search for users by nickname.")
    async def find_nickname(self, ctx, *, search: str):
        """
        Usage: -find nicknames <search>
        Aliases:
            -find nicks
            -find nick
            -find nickname
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
        stuff = "\r\n".join([f"[{str(num).zfill(2)}] {data}" for num, data in enumerate(loop, start=1)])
        await ctx.send_or_reply(f"Found **{len(loop)}** on your search for **{search}**")
        p = pagination.MainMenu(pagination.TextPageSource(text=str(stuff), prefix="```ini\n", max_size=800))
        try:
            await p.start(ctx)
        except menus.MenuError as e:
            await ctx.send(e)

    @find.command(name="id", aliases=['snowflake'], brief="Search for users by id.")
    async def find_id(self, ctx, *, search: int):
        """
        Usage: -find id <search>
        Alias: -find snowflake
        Output:
            Starts a pagination session
            showing all users who's IDs
            contain your search
        """
        loop = [
            f"{i} | {i} ({i.id})"
            for i in ctx.guild.members
            if (str(search) in str(i.id)) and not i.bot
        ]
        if not loop:
            return await ctx.fail(f"**No results.**")
        stuff = "\r\n".join([f"[{str(num).zfill(2)}] {data}" for num, data in enumerate(loop, start=1)])
        await ctx.send_or_reply(f"Found **{len(loop)}** on your search for **{search}**")
        p = pagination.MainMenu(pagination.TextPageSource(text=str(stuff), prefix="```ini\n", max_size=800))
        try:
            await p.start(ctx)
        except menus.MenuError as e:
            await ctx.send(e)

    @find.command(name="hash", aliases=["discriminator","discrim"], brief="Search for users by discriminator.")
    async def find_discrim(self, ctx, *, search: str):
        """
        Usage: -find hash <search>
        Aliases:
            -find discrim
            -find discriminator
        Output:
            Starts a pagination session
            showing all users who's hash
            (discriminator) contain your search
        """
        if not len(search) == 4 or not re.compile("^[0-9]*$").search(search):
            return await ctx.send_or_reply(content="You must provide exactly 4 digits",
            )

        loop = [f"{i} ({i.id})" for i in ctx.guild.members if search == i.discriminator]
        if not loop:
            return await ctx.fail(f"**No results.**")
        stuff = "\r\n".join([f"[{str(num).zfill(2)}] {data}" for num, data in enumerate(loop, start=1)])
        await ctx.send_or_reply(f"Found **{len(loop)}** on your search for **{search}**")
        p = pagination.MainMenu(pagination.TextPageSource(text=str(stuff), prefix="```ini\n", max_size=1250))
        try:
            await p.start(ctx)
        except menus.MenuError as e:
            await ctx.send(e)

    @find.command(name="duplicates", aliases=["dups"], brief="Find users with identical names.")
    async def find_duplicates(self, ctx):
        """
        Usage: -find duplicates
        Alias: -find dups
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
        stuff = "\r\n".join([f"[{str(num).zfill(2)}] {data}" for num, data in enumerate(loop, start=1)])
        await ctx.send_or_reply(f"Found **{len(loop)}** on your search for **duplicates**")
        p = pagination.MainMenu(pagination.TextPageSource(text=str(stuff), prefix="```ini\n", max_size=800))
        try:
            await p.start(ctx)
        except menus.MenuError as e:
            await ctx.send(e)

    def _is_hard_to_mention(self, name):
        """Determine if a name is hard to mention."""
        codecs.register_error("newreplace", lambda x: (b" " * (x.end - x.start), x.end))

        encoderes, chars = codecs.getwriter("ascii").encode(name, "newreplace")

        return re.search(br"[^ ][^ ]+", encoderes) is None

    @find.command(name="hardmentions", aliases=["weird", "special","hardmention"], brief="Find users with hard to mention names.")
    async def hardmentions(self, ctx, username:str = None):
        """
        Usage: -find hardmentions [username=False]
        Alias:
            -find weird
            -find special
            -find hardmention
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
        if username:
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
        stuff = "\r\n".join([f"[{str(num).zfill(2)}] {data}" for num, data in enumerate(loop, start=1)])
        await ctx.send_or_reply(f"Found **{len(loop)}** on your search for **hardmentions**")
        p = pagination.MainMenu(pagination.TextPageSource(text=str(stuff), prefix="```ini\n", max_size=800))
        try:
            await p.start(ctx)
        except menus.MenuError as e:
            await ctx.send(e)

    @commands.command(brief="Show info on a discord snowflake.", aliases=["id"])
    async def snowflake(self, ctx, *, sid=None):
        """
        Usage: -snowflake <id>
        Alias: -id
        Output:
            The exact date & time that the
            discord snowflake was created
        Examples:
            -snowflake 81037737626
            -id 810377376269205546
        Notes:
            Will calculate when the snowflake
            will be created if it does not exist
        """
        if not str(sid).isdigit():
            return await ctx.send_or_reply(
                content=f"Usage: `{ctx.prefix}snowflake <id>`"
            )

        sid = int(sid)
        timestamp = (
            (sid >> 22) + 1420070400000
        ) / 1000  # python uses seconds not milliseconds
        cdate = datetime.utcfromtimestamp(timestamp)
        msg = "Snowflake created {}".format(
            cdate.strftime("%A, %B %d, %Y at %H:%M:%S UTC")
        )
        return await ctx.send_or_reply(msg)


    @commands.command(brief="Shows the raw content of a message.")
    async def raw(self, ctx, *, message: discord.Message):
        """
        Usage: -raw [message id]
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

    @commands.command(brief="Snipe a deleted message.", aliases=["retrieve"])
    @commands.guild_only()
    async def snipe(self, ctx, *, member: discord.Member = None):
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
            return await ctx.send_or_reply(content=f"{self.bot.emote_dict['error']} There is nothing to snipe.",
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

    @commands.command(brief="Shorten URLs to a bitly links.")
    async def shorten(self, ctx, url=None):
        """
        Usage: -shorten <url>
        Output:
            A short url that will redirect to
            the url that was passed.
        """
        if url is None:
            return await ctx.send_or_reply(content=f"Usage: `{ctx.prefix}shorten <url>`",
            )
        params = {"access_token": self.bot.constants.bitly, "longUrl": url}

        response = await self.bot.get(
            "https://api-ssl.bitly.com/v3/shorten", params=params
        )
        resp = json.loads(response)
        if resp["status_code"] != 200:
            return await ctx.send_or_reply(content=f"{self.bot.emote_dict['failed']} Invalid URL received.",
            )
        else:
            await ctx.send_or_reply(content=f"{self.bot.emote_dict['success']} Successfully shortened URL:\t"
                "<{}>".format(resp["data"]["url"]),
            )

    @commands.command(aliases=["math", "calc"], brief="Calculate a math formula.")
    async def calculate(self, ctx, *, formula=None):
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
            sgn"""
        if formula is None:
            return await ctx.send_or_reply(content="Usage: `{}calculate <formula>`".format(ctx.prefix),
            )
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
        await ctx.send_or_reply( content="{} = {}".format(formula, answer)
        )


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