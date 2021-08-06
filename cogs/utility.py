import io
import re
import copy
from discord.member import M
import pytz
import json
import math
import base64
import random
import typing
import asyncio
import discord
import operator
import itertools
import pyparsing
import unicodedata

from collections import Counter, namedtuple
from datetime import datetime
from discord.ext import commands, menus
from functools import cmp_to_key
from geopy import geocoders
from PIL import Image
from unidecode import unidecode

from utilities import utils
from utilities import checks
from utilities import cleaner
from utilities import helpers
from utilities import converters
from utilities import decorators
from utilities import formatting
from utilities import pagination


def setup(bot):
    bot.add_cog(Utility(bot))


# Token commands taken and edited from Stella#2000's bot
# https://github.com/InterStella0/stella_bot


class Utility(commands.Cog):
    """
    Module for general utilities.
    """

    def __init__(self, bot):
        self.bot = bot
        self.geo = geocoders.Nominatim(user_agent="Neutra")
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
        aliases=["worldclock", "worldtime"],
        brief="Get the time of any location",
        implemented="2021-04-15 06:20:17.433895",
        updated="2021-05-06 21:28:57.052612",
        examples="""
                {0}clock Los Angeles
                {0}clock Netherlands
                {0}worldtime Los Angeles
                {0}worldtime Netherlands
                {0}worldclock Los Angeles
                {0}worldclock Netherlands
                """,
    )
    async def clock(self, ctx, *, place):
        """
        Usage: {0}clock <place>
        Aliases: {0}worldclock, {0}worldtime
        Output:
            Shows the current time of day
            it is in the specified location.
        Notes:
            Can accept cities, states, provinces,
            and countries as valid locations.
        """
        try:
            if place.lower() == "la":
                city_name = "Los Angeles"
            else:
                city_name = re.sub(r"([^\s\w]|_)+", "", place)
            location = self.geo.geocode(city_name)
            if location is None:
                return await ctx.send_or_reply(
                    content=f"{self.bot.emote_dict['failed']} Invalid location.",
                )

            r = await self.bot.get(
                "http://api.timezonedb.com/v2.1/get-time-zone?key={}&format=json&by=position&lat={}&lng={}".format(
                    self.bot.constants.timezonedb, location.latitude, location.longitude
                )
            )
            request = json.loads(r)

            if request["status"] != "OK":
                await ctx.send_or_reply(
                    content=f"{self.bot.emote_dict['failed']} An API error occurred. Please try again later.",
                )
            else:
                zone = pytz.timezone(request["zoneName"])
                time = datetime.now(zone)
                time_fmt = time.strftime("%a %I:%M %p")
                clock = utils.getClockForTime(time_fmt)
                msg = f"{self.bot.emote_dict['clock']} `It is {clock} in {city_name.title()} ({request['zoneName']})`"
                await ctx.send_or_reply(content=msg)
        except Exception as e:
            await ctx.send_or_reply(e)

    @decorators.command(
        aliases=["flags"],
        brief="Show all the badges a user has",
        implemented="2021-06-04 01:06:21.329396",
        updated="2021-06-04 01:06:21.329396",
        examples="""
                {0}badges @Hecate
                {0}flags 708584008065351681
                """,
    )
    async def badges(self, ctx, *, user: converters.DiscordUser = None):
        """
        Usage: {0}badges [user]
        Alias: {0}flags
        Output: Shows all the badges a user has
        Notes: Will default to you if no user is passed.
        """
        user = user or ctx.author
        if user.bot:
            raise commands.BadArgument(f"User `{user}` is a bot account.")

        badges = []
        if user.public_flags.staff:
            badges.append(self.bot.emote_dict["staff"])
        if user.public_flags.partner:
            badges.append(self.bot.emote_dict["partner"])
        if user.public_flags.hypesquad:
            badges.append(self.bot.emote_dict["hypesquad"])
        if user.public_flags.hypesquad_balance:
            badges.append(self.bot.emote_dict["balance"])
        if user.public_flags.hypesquad_bravery:
            badges.append(self.bot.emote_dict["bravery"])
        if user.public_flags.hypesquad_brilliance:
            badges.append(self.bot.emote_dict["brilliance"])
        if user.public_flags.bug_hunter:
            badges.append(self.bot.emote_dict["bughunter"])
        if user.public_flags.bug_hunter_level_2:
            badges.append(self.bot.emote_dict["bughuntergold"])
        if user.public_flags.discord_certified_moderator:
            badges.append(self.bot.emote_dict["moderator"])
        if (
            user.public_flags.verified_bot_developer
            or user.public_flags.early_verified_bot_developer
        ):
            badges.append(self.bot.emote_dict["dev"])
        if user.public_flags.early_supporter:
            badges.append(self.bot.emote_dict["supporter"])
        if hasattr(user, "premium_since") and user.premium_since is not None:
            badges.append(self.bot.emote_dict["nitro"])
            badges.append(self.bot.emote_dict["boost"])
        else:
            if user.avatar.is_animated():
                badges.append(self.bot.emote_dict["nitro"])
        if not badges:
            return await ctx.fail(f"User `{user}` has no badges.")
        await ctx.success(f"`{user}'s` badges: {' '.join(badges)}")

    @decorators.command(
        aliases=["reactions"],
        brief="Get react info on a message.",
        implemented="2021-05-28 20:09:52.796946",
        updated="2021-05-28 20:09:52.796946",
        examples="""
                {0}reactinfo 847929402116669482
                {0}reactions 847929402116669482
                """,
    )
    @checks.cooldown()
    async def reactinfo(self, ctx, message: discord.Message = None):
        """
        Usage: {0}reactinfo [message id]
        Alias: {0}reactions
        Output:
            Shows all the users who reacted
            to the given message in an rst
            tabular format.
        Notes:
            Will send a file object if the
            table length is greater than
            discord's character limit.
        """
        if not message:
            message = await converters.DiscordMessage().convert(ctx)

        if not len(message.reactions):
            raise commands.BadArgument(f"Message `{message.id}` has no reactions.")
        await ctx.trigger_typing()
        table = formatting.TabularData()
        headers = []
        formats = {}
        total = []
        for reaction in message.reactions:
            users = [
                str(user)
                for user in await reaction.users().flatten()
                if user is not None
            ]
            headers.append(f"{str(reaction.emoji)} [{len(users)}]")
            formats[str(reaction.emoji)] = [
                str(user)
                for user in await reaction.users().flatten()
                if user is not None
            ]
            total.extend(users)
        count = len(Counter(total))
        rows = list(itertools.zip_longest(*formats.values(), fillvalue=""))
        pluralize = "" if count == 1 else "s"
        table.set_columns(headers)
        table.add_rows(rows)
        render = table.render()
        completed = f"```sml\n{render}```"
        emote = self.bot.emote_dict["graph"]
        await ctx.bold(
            f"{emote} {count} user{pluralize} reacted to the message `{message.id}`."
        )
        if len(completed) > 2000:
            fp = io.BytesIO(completed.encode("utf-8"))
            await ctx.send_or_reply(file=discord.File(fp, "reactinfo.sml"))
        else:
            await ctx.send_or_reply(completed)

    @decorators.command(
        aliases=["vcusers"],
        brief="Show all the users in a vc.",
        implemented="2021-05-28 20:09:52.796946",
        updated="2021-05-28 20:09:52.796946",
        examples="""
                {0}voiceusers 847929402116669482
                {0}vcusers #music
                """,
    )
    @checks.cooldown()
    async def voiceusers(self, ctx, channel: discord.VoiceChannel):
        """
        Usage: {0}voiceusers [voice channel]
        Alias: {0}vcusers
        Output:
            Shows all the users in a voice
            channel in tabular format.
        Notes:
            Will send a file object if the
            table length is greater than
            discord's character limit.
        """
        if not len(channel.members):
            raise commands.BadArgument(f"Voice channel {channel.mention} has no users.")
        await ctx.trigger_typing()
        table = formatting.TabularData()
        headers = ["INDEX", "USERS"]
        users = [
            (idx, user)
            for idx, user in enumerate(
                sorted(channel.members, key=lambda m: str(m)), start=1
            )
            if user is not None
        ]

        count = len(users)
        pluralize = "" if count == 1 else "s"
        table.set_columns(headers)
        table.add_rows(users)
        render = table.render()
        completed = f"```sml\n{render}```"
        emote = self.bot.emote_dict["graph"]
        await ctx.bold(
            f"{emote} Voice channel {channel.mention} currently has {count} user{pluralize}."
        )
        if len(completed) > 2000:
            fp = io.BytesIO(completed.encode("utf-8"))
            await ctx.send_or_reply(file=discord.File(fp, "vcusers.sml"))
        else:
            await ctx.send_or_reply(completed)

    @decorators.command(
        aliases=["genoauth", "oauth2", "genbotoauth"],
        brief="Generate a bot invite link.",
        implemented="2021-05-05 17:59:12.441533",
        updated="2021-05-05 17:59:12.441533",
        examples="""
                {0}oauth
                {0}oauth2 810377376269205546 8
                {0}genoauth Neutra#7630 359867
                {0}genbotoauth @Neutra 34985
                """,
    )
    @checks.cooldown()
    async def oauth(
        self,
        ctx,
        bot: typing.Optional[converters.DiscordBot] = None,
        permissions: int = None,
    ):
        """
        Usage: {0}oauth [bot] [permissions]
        Aliases:
            {0}oauth2
            {0}genoauth
            {0}genbotoauth
        Output:
            Generates a bot invite oauth URL
            with your specified permissions.
        Notes:
            Defaults to me if no bot is specified.
        """
        bot = bot or self.bot.user
        if not permissions:
            oauth_url = discord.utils.oauth_url(bot.id)
        else:
            perms = discord.Permissions(permissions=permissions)
            oauth_url = discord.utils.oauth_url(bot.id, permissions=perms)
        await ctx.rep_or_ref("<" + oauth_url + ">")

    @decorators.command(  # For anyone looking here, these tokens are not valid.
        aliases=["pt", "parsetoken"],
        brief="Decode a discord token.",
        implemented="2021-05-06 01:09:46.734485",
        updated="2021-05-07 05:47:26.758031",
        writer=591135329117798400,
        examples="""
                {0}pt NzA4NTg0MDA4MDY1MzUxNjgx.YJU29g.K8lush3e6flT9Of7d7bp4rj6aU2
                {0}ptoken NzA4NTg0MDA4MDY1MzUxNjgx.YJU29g.K8lush3e6flT9Of7d7bp4rj6aU2
                {0}parsetoken NzA4NTg0MDA4MDY1MzUxNjgx.YJU29g.K8lush3e6flT9Of7d7bp4rj6aU2
                """,
    )
    @checks.bot_has_perms(embed_links=True)
    @checks.cooldown()
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
            raise commands.BadArgument("Invalid token")

        def decode_user(user):
            user_bytes = user.encode()
            user_id_decoded = base64.b64decode(user_bytes)
            return user_id_decoded.decode("ascii")

        str_id = decode_user(token_part[0])
        if not str_id or not str_id.isdigit():
            raise commands.BadArgument("Invalid token")
        user_id = int(str_id)
        user = await self.bot.fetch_user(user_id)
        if not user:
            raise commands.BadArgument("Invalid token")
        timestamp = self.parse_date(token_part[1]) or "Invalid date"

        embed = discord.Embed(
            title=f"{user.display_name}'s token",
            description=f"**User:** `{user}`\n"
            f"**ID:** `{user.id}`\n"
            f"**Bot:** `{user.bot}`\n"
            f"**Created:** `{user.created_at}`\n"
            f"**Token Created:** `{timestamp}`",
        )
        embed.color = self.bot.constants.embed
        embed.set_thumbnail(url=user.avatar.url)
        await ctx.send_or_reply(embed=embed)

    @decorators.command(
        aliases=["gt", "generatetoken"],
        brief="Generate a discord token.",
        implemented="2021-05-06 02:26:12.925925",
        updated="2021-05-07 05:49:40.401151",
        writer=591135329117798400,
        examples="""
                {0}gt
                {0}gtoken 708584008065351681
                {0}generatetoken Hecate
                """,
    )
    @checks.bot_has_perms(embed_links=True)
    @checks.cooldown()
    async def gtoken(self, ctx, user: converters.DiscordUser = None):
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
        embed.set_thumbnail(url=user.avatar.url)
        await ctx.send_or_reply(embed=embed)

    @decorators.command(
        brief="Convert special characters to ascii.",
        implemented="2021-04-21 05:14:23.747367",
        updated="2021-05-24 16:13:50.890038",
        examples="""
                {0}ascify H̷̗́̊ẻ̵̩̚ċ̷͎̖̚a̴̛͎͊t̸̳̭̂͌ȇ̴̲̯
                {0}ascify 708584008065351681
                """,
    )
    @checks.cooldown()
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
            member = await converters.DiscordMember().convert(ctx, string_or_member)
            if member:
                current_name = copy.copy(member.display_name)
                ascified = unidecode(member.display_name)
                if ctx.guild and ctx.author.guild_permissions.manage_nicknames:
                    try:
                        await member.edit(nick=ascified)
                        return await ctx.success(
                            f"Ascified **{current_name}** to **{ascified}**"
                        )
                    except Exception:
                        ascified = unidecode(string_or_member)
                else:
                    ascified = unidecode(string_or_member)
            else:
                ascified = unidecode(string_or_member)
        except commands.BadArgument:
            ascified = unidecode(string_or_member)
        await ctx.success(f"Result: **{ascified}**")

    @decorators.command(
        brief="Dehoist a specified user.",
        implemented="2021-05-06 02:22:00.614849",
        updated="2021-05-24 16:13:50.890038",
        examples="""
                {0}dehoist Hecate
                {0}dehoist @Hecate
                {0}dehoist Hecate#3523
                {0}dehoist 708584008065351681
                """,
    )
    @commands.guild_only()
    @checks.cooldown()
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
            use {0}massdehoist. If the bot or the command
            author lack permissions to edit a nickname,
            the bot will output a dehoisted version of
            the target user's name.
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
            bot_perms = ctx.guild.me.guild_permissions.manage_nicknames
            user_perms = ctx.author.guild_permissions.manage_nicknames
            if user_perms and bot_perms:
                try:
                    await user.edit(
                        nick=name,
                        reason=utils.responsible(
                            ctx.author, "Nickname edited by dehoist command."
                        ),
                    )
                    await ctx.success(f"Dehoisted user `{user}` to `{name.strip()}`")
                    return
                except Exception as e:
                    await helpers.error_info(ctx, [(str(user), e)])
                    return
            else:
                await ctx.success(
                    f"The dehoisted version of `{user}` is `{name.strip()}`"
                )
        else:
            await ctx.fail(f"User `{user}` is not hoisting.")

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
    @checks.bot_has_perms(embed_links=True, attach_files=True)
    @checks.cooldown()
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
    @checks.cooldown()
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
            return f"`\\U{digit:>08}`: {name} - {c} \N{EM DASH} <http://www.fileformat.info/info/unicode/char/{digit}>"

        msg = "\n".join(map(to_string, characters))
        await ctx.success(msg)

    # Helper function to format and send the given image url.
    async def do_avatar(self, ctx, name, url, default=False, option="avatar"):
        embed = discord.Embed(
            title=f"**{name}'s {'default' if default else ''} {option}.**",
            description=f"Links to `{name}'s` {option}:  "
            f"[webp]({(str(url))}) | "
            f'[png]({(str(url).replace("webp", "png"))}) | '
            f'[jpeg]({(str(url).replace("webp", "jpg"))})  ',
            color=self.bot.constants.embed,
        )
        embed.set_image(url=url)
        await ctx.send_or_reply(embed=embed)

    @decorators.command(
        aliases=["av", "pfp", "icon"],
        brief="Show a user's avatar.",
        implemented="",
        updated="",
        examples="""
                {0}avatar
                {0}av @Hecate
                {0}icon Hecate#3523
                {0}pfp 708584008065351681
                """,
    )
    @checks.cooldown()
    async def avatar(self, ctx, *, user: converters.DiscordUser = None):
        """
        Usage: {0}avatar [user]
        Aliases: {0}av, {0}pfp, {0}icon
        Examples: {0}avatar 810377376269205546, {0}avatar Neutra
        Output: Shows an enlarged embed of a user's avatar.
        Notes: Will default to you if no user is passed.
        """
        user = user or ctx.author
        await self.do_avatar(ctx, user.display_name, url=user.avatar.url)

    @decorators.command(
        brief="Show a user's banner.",
        examples="""
                {0}banner
                {0}banner @Hecate
                {0}banner Hecate#3523
                {0}banner 708584008065351681
                """,
    )
    @checks.cooldown()
    async def banner(self, ctx, *, user: converters.DiscordUser = None):
        """
        Usage: {0}avatar [user]
        Aliases: {0}av, {0}pfp, {0}icon
        Examples: {0}avatar 810377376269205546, {0}avatar Neutra
        Output: Shows an enlarged embed of a user's avatar.
        Notes: Will default to you if no user is passed.
        """
        user = user or ctx.author
        user = await self.bot.fetch_user(user.id)
        if not user.banner:
            await ctx.fail(f"User **{user}** `{user.id}` has no banner.")
            return
        await self.do_avatar(ctx, str(user), user.banner.url, option="banner")

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
    @checks.cooldown()
    async def defaultavatar(self, ctx, *, user: converters.DiscordUser = None):
        """
        Usage: {0}defaultavatar [user]
        Aliases: {0}dav, {0}dpfp, {0}davatar
        Output:
            Shows an enlarged embed of a user's default avatar.
        Notes:
            Will default to you if no user is passed.
        """
        user = user or ctx.author
        await self.do_avatar(
            ctx, user.display_name, user.default_avatar.url, default=True
        )

    @decorators.command(
        aliases=["mobile", "web", "desktop", "device"],
        brief="Show a user's discord platform.",
        implemented="2021-03-25 05:56:35.053930",
        updated="2021-05-06 23:25:08.685407",
        examples="""
                {0}web @Hecate Neutra 708584008065351681
                {0}mobile @Hecate Neutra 708584008065351681
                {0}desktop @Hecate Neutra 708584008065351681
                {0}platform @Hecate Neutra 708584008065351681
                """,
    )
    @checks.guild_only()
    @checks.cooldown()
    async def platform(self, ctx, *, user: converters.DiscordMember = None):
        """
        Usage:  {0}platform [user]
        Alias:  {0}mobile, {0}desktop, {0}web, {0}device
        Output:
            Shows which discord platform a user
            is currently on. Can be discord desktop,
            discord mobile, or discord web.
        Notes:
            The bot cannot determine platform
            when users are offline or if their
            status is invisible.
        """
        user = user or ctx.author
        statuses = []

        if str(user.status) == "offline":
            await ctx.send_or_reply(
                f"{self.bot.emote_dict['offline']} User `{user}` is offline."
            )
            return

        if str(user.desktop_status) != "offline":
            statuses.append("desktop")  # Member is on desktop :)
        if str(user.mobile_status) != "offline":  # Member is on discord mobile. :(
            statuses.append("mobile")
        if str(user.web_status) != "offline":  # Member is on web :(((
            statuses.append("web")

        def word_fmt(statuses):
            statuses = ["discord " + status for status in statuses]
            if len(statuses) == 3:
                return f"{statuses[0]}, {statuses[1]}, and {statuses[2]}"
            elif len(statuses) == 2:
                return f"{statuses[0]} and {statuses[1]}"
            else:
                return f"{statuses[0]}"

        emoji_fmt = " ".join(self.bot.emote_dict[key] for key in statuses)
        await ctx.send_or_reply(
            f"{emoji_fmt} User `{user}` is on {word_fmt(statuses)}."
        )

    @decorators.command(
        aliases=["sav", "savatar"],
        brief="Show the server's icon.",
        implemented="2021-03-25 17:11:21.634209",
        updated="2021-05-07 05:21:05.999642",
        examples="""
                {0}dav
                {0}dpfp 810377376269205546
                {0}davatar Hecate
                {0}defaultavatar @Hecate
                """,
    )
    @checks.cooldown()
    async def serveravatar(self, ctx, *, server: converters.DiscordGuild = None):
        """
        Usage: {0}serveravatar
        Aliases: {0}sav, {0}savatar
        Output:
            Shows an enlarged embed of a server's icon.
        Notes:
            Will default to the current server
            if no server is passed.
        """
        server = server or ctx.guild
        if not server.icon:
            await ctx.fail(f"Server **{server.name}** has no icon.")
            return
        await self.do_avatar(ctx, server, server.icon.url, option="icon")

    @decorators.command(
        aliases=["nick", "setnick"],
        brief="Edit or reset a user's nickname",
        implemented="2021-03-14 04:33:34.557509",
        updated="2021-05-24 16:13:50.890038",
        examples="""
            {0}nick Neutra
            {0}setnick @Tester Tester2
            {0}nickname Neutra Tester
            """,
    )
    @commands.guild_only()
    @checks.bot_has_perms(manage_nicknames=True)
    @checks.has_perms(manage_nicknames=True)
    @checks.cooldown()
    async def nickname(
        self,
        ctx,
        user: typing.Optional[converters.DiscordMember],
        *,
        nickname: str = None,
    ):
        """
        Usage: {0}nickname <user> [nickname]
        Aliases: {0}nick, {0}setnick
        Permission: Manage Nicknames
        Output:
            Edits a member's nickname on the server.
        Notes:
            Nickname will be reset if no new nickname is passed.
        """
        user = user or ctx.author

        res = await checks.nick_priv(ctx, user)
        if res:
            raise commands.BadArgument(res)
        try:
            await user.edit(
                nick=nickname,
                reason=utils.responsible(
                    ctx.author, "Nickname edited by command execution"
                ),
            )
            message = f"Nicknamed `{user}: {nickname}`"
            if nickname is None:
                message = f"Reset nickname for `{user}`"
            await ctx.success(message)
        except discord.Forbidden:
            await ctx.fail(f"I do not have permission to edit `{user}'s` nickname.")
        except Exception as e:
            await helpers.error_info(ctx, [(str(user), e)])

    @decorators.command(
        aliases=["id", "age"],
        brief="Show info on a discord snowflake.",
        implemented="2021-04-05 18:28:55.338390",
        updated="2021-05-07 05:05:13.464282",
        examples="""
                {0}snowflake 81037737626
                {0}id 810377376269205546
                {0}age 81037737626920554
                """,
    )
    async def snowflake(self, ctx, *, snowflake):
        """
        Usage: {0}snowflake <id>
        Aliases: {0}id, {0}age
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
        msg = "{} Snowflake `{}` created **{}**".format(
            self.bot.emote_dict["snowflake"],
            snowflake,
            cdate.strftime("%A, %B %d, %Y at %H:%M:%S UTC"),
        )
        await ctx.send_or_reply(msg)

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
    async def raw(self, ctx, *, message: discord.Message = None):
        """
        Usage: raw [message id]
        Alias: {0}content
        Output: Raw message content
        """
        if not message:
            message = await converters.DiscordMessage().convert(ctx)

        raw_data = await self.bot.http.get_message(message.channel.id, message.id)
        string = json.dumps(raw_data, indent=2)
        string = cleaner.clean_all(string)
        if len(string) < 1990:
            msg = "```json\n" + str(string) + "```"
            await ctx.send_or_reply(msg)
            return
        p = pagination.MainMenu(pagination.TextPageSource(string, prefix="```json"))
        try:
            await p.start(ctx)
        except menus.MenuError as e:
            await ctx.send_or_reply(str(e))

    @decorators.command(
        aliases=["epost"],
        brief="Sends all server emojis to your dms.",
        implemented="2021-05-10 20:14:33.223405",
        updated="2021-05-10 20:14:33.223405",
    )
    @checks.has_perms(manage_emojis=True)
    @checks.cooldown()
    async def emojipost(self, ctx, dm: converters.Flag = None):
        """
        Usage: {0}emojipost [nodm]
        Alias: {0}epost
        Output:
            Sends a formatted list of
            emojis and their IDs.
            Specify the nodm bool argument
            to avoid the bot from DMing you.
        """
        emojis = sorted(
            [e for e in ctx.guild.emojis if len(e.roles) == 0 and e.available],
            key=lambda e: e.name.lower(),
        )
        paginator = commands.Paginator(suffix="", prefix="")

        for emoji in emojis:
            paginator.add_line(f"{emoji} ➔ `{emoji}`")

        for page in paginator.pages:
            if dm:
                try:
                    await ctx.author.send(page)
                except Exception:
                    await ctx.send_or_reply(page)
            else:
                await ctx.send_or_reply(page)

    @decorators.command(
        aliases=["bitly"],
        brief="Shorten URLs to bitly links.",
        implemented="2021-04-15 05:17:23.532870",
        updated="2021-05-07 05:02:01.750279",
        examples="""
                {0}shorten https://discord.gg/947ramn
                {0}bitly https://discord.gg/5n696us4Tf
                """,
    )
    @checks.cooldown()
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
    @checks.cooldown(2, 60)
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

        m = await ctx.send_or_reply(
            "Enter your embed's image URL (must be a valid http(s) URL):"
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
                        "Invalid URL schema.\nEnter your embed's image URL (must be a valid http/https url):"
                    )
                    self.msg_collection.append(m.id)
                    msg = await self.do_msg_check(ctx, embed)
                    if msg is None or isinstance(msg, discord.embeds._EmptyEmbed):
                        break
                    if self.uregex.fullmatch(msg):
                        check = True
            if msg is None:
                return
            image_icon = msg

            embed.set_image(url=image_icon)

        m = await ctx.send_or_reply(
            "Enter your embed's thumbnail URL (must be a valid http(s) URL):"
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
                        "Invalid URL schema.\nEnter your embed's thumbnail URL (must be a valid http/https url):"
                    )
                    self.msg_collection.append(m.id)
                    msg = await self.do_msg_check(ctx, embed)
                    if msg is None or isinstance(msg, discord.embeds._EmptyEmbed):
                        break
                    if self.uregex.fullmatch(msg):
                        check = True
            if msg is None:
                return
            image_icon = msg

            embed.set_thumbnail(url=image_icon)

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
        try:
            await ctx.send_or_reply(embed=embed)
        except discord.HTTPException:
            raise commands.BadArgument(
                f"The embed provided was either invalid or too long to send. Please try again."
            )

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
    @checks.cooldown()
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
            msg += "```yaml\n" + ctx.command.help.format(ctx.clean_prefix) + "```"
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
        point = pyparsing.Literal(".")
        e = pyparsing.CaselessLiteral("E")
        fnumber = pyparsing.Combine(
            pyparsing.Word("+-" + pyparsing.nums, pyparsing.nums)
            + pyparsing.Optional(
                point + pyparsing.Optional(pyparsing.Word(pyparsing.nums))
            )
            + pyparsing.Optional(
                e + pyparsing.Word("+-" + pyparsing.nums, pyparsing.nums)
            )
        )
        ident = pyparsing.Word(
            pyparsing.alphas, pyparsing.alphas + pyparsing.nums + "_$"
        )
        plus = pyparsing.Literal("+")
        minus = pyparsing.Literal("-")
        mult = pyparsing.Literal("x")
        div = pyparsing.Literal("/")
        lpar = pyparsing.Literal("(").suppress()
        rpar = pyparsing.Literal(")").suppress()
        addop = plus | minus
        multop = mult | div
        expop = pyparsing.Literal("^")
        pi = pyparsing.CaselessLiteral("PI")
        expr = pyparsing.Forward()
        atom = (
            (
                pyparsing.Optional(pyparsing.oneOf("- +"))
                + (pi | e | fnumber | ident + lpar + expr + rpar).setParseAction(
                    self.pushFirst
                )
            )
            | pyparsing.Optional(pyparsing.oneOf("- +"))
            + pyparsing.Group(lpar + expr + rpar)
        ).setParseAction(self.pushUMinus)
        # by defining exponentiation as "atom [ ^ factor ]..." instead of
        # "atom [ ^ atom ]...", we get right-to-left exponents, instead of left-to-right
        # that is, 2^3^2 = 2^(3^2), not (2^3)^2.
        factor = pyparsing.Forward()
        factor << atom + pyparsing.ZeroOrMore(
            (expop + factor).setParseAction(self.pushFirst)
        )
        term = factor + pyparsing.ZeroOrMore(
            (multop + factor).setParseAction(self.pushFirst)
        )
        expr << term + pyparsing.ZeroOrMore(
            (addop + term).setParseAction(self.pushFirst)
        )
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
