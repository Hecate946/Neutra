import discord
import base64
import datetime
import random
from discord.ext import commands
from collections import namedtuple
from typing import Union


def setup(bot):
    bot.add_cog(Misc(bot))


# Thanks goes to Stella bot for some of these features.
class Misc(commands.Cog):
    """
    Module for miscellaneous tools.
    """
    def __init__(self, bot):
        self.bot = bot

    def parse_date(self, token):
        token_epoch = 1293840000
        bytes_int = base64.standard_b64decode(token + "==")
        decoded = int.from_bytes(bytes_int, "big")
        timestamp = datetime.datetime.utcfromtimestamp(decoded)

        # sometime works
        if timestamp.year < 2015:
            timestamp = datetime.datetime.utcfromtimestamp(decoded + token_epoch)
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
            return await ctx.send(f"Usage: `{ctx.prefix}ptoken <token>`")
        token_part = token.split(".")
        if len(token_part) != 3:
            return await ctx.send("Invalid token")

        def decode_user(user):
            user_bytes = user.encode()
            user_id_decoded = base64.b64decode(user_bytes)
            return user_id_decoded.decode("ascii")
        str_id = decode_user(token_part[0])
        if not str_id or not str_id.isdigit():
            return await ctx.send("Invalid user")
        user_id = int(str_id)
        member = self.bot.get_user(user_id)
        if not member:
            return await ctx.send("Invalid user")
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
        await ctx.send(embed=embed)

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
        time_rn = datetime.datetime.utcnow()
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
        await ctx.send(embed=embed)

    @commands.command(brief="Find the first message of a reply thread.")
    async def replies(self, ctx, message: discord.Message):
        """
        Usage: -replies <message>
        Output:
            The author, replies, message
            and jump_url to the message.
        """
        if message is None:
            return await ctx.send(f"Usage: `{ctx.prefix}replies <message>`")
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
        
        await ctx.send(embed=em)

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
            return await ctx.send(f"Usage: `{ctx.prefix}findtype <discord object>`")
        async def found_message(type_id):
            embed = discord.Embed(title="Result")
            embed.description=(
                f"**ID**: `{obj_id.id}`\n"
                f"**Type:** `{type_id.capitalize()}`\n"
                f"**Created:** `{obj_id.created_at}`"
            )
            embed.color = self.bot.constants.embed
            await ctx.send(embed=embed)
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
            return await ctx.send(f"{self.bot.emote_dict['failed']} I could not find that object.")