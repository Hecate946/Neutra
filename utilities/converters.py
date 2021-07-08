import enum
import re
import typing
import asyncio
import argparse

import discord
from discord.ext import commands, menus

from utilities import checks
from utilities import exceptions
from utilities import formatting
from utilities import pagination

EMOJI_REGEX = re.compile(r"<a?:.+?:([0-9]{15,21})>")
EMOJI_NAME_REGEX = re.compile(r"[0-9a-zA-Z\_]{2,32}")
USERNAME_REGEX = re.compile(r"(.*)#(\d{4})")
SNOWFLAKE_REGEX = re.compile(r"([0-9]{15,21})$")
USER_MENTION_REGEX = re.compile(r"<@!?([0-9]+)>$")
ROLE_MENTION_REGEX = re.compile(r"<@&([0-9]+)>$")


async def prettify(ctx, arg):
    pretty_arg = await commands.clean_content().convert(ctx, str(arg))
    return pretty_arg


async def disambiguate(ctx, matches, sort=lambda m: str(m), timeout=30):
    if len(matches) == 1:
        return matches[0]

    matches = sorted(matches, key=sort)

    user_value = "**Nickname:** {0.display_name}\n**ID:** `{0.id}`"
    role_value = "**Mention:** {0.mention}\n**ID:** `{0.id}`"
    generic = "**ID:** `{0.id}`"

    def pred(match):
        if type(match) in [discord.User, discord.Member]:
            result = user_value.format(match)
        elif type(match) == discord.Role:
            result = role_value.format(match)
        else:
            result = generic.format(match)
        return result

    entries = [
        (f"{idx}. {str(match)}", pred(match))
        for idx, match in enumerate(matches, start=1)
    ]

    p = pagination.MainMenu(
        pagination.FieldPageSource(
            entries=entries,
            title=f"{len(matches):,} Matches Found {ctx.bot.emote_dict['search']}",
            description="Please enter the number corresponding to the desired entry.",
            per_page=10,
        )
    )

    messages = []  # List to store the message IDs for cleanup
    try:
        await p.start(ctx)
        messages.append(p.message.id)
    except menus.MenuError as e:
        m = await ctx.send(e)
        messages.append(m.id)

    try:
        msg = await ctx.bot.wait_for(
            "message",
            timeout=timeout,
            check=lambda m: m.author.id == ctx.author.id
            and m.channel.id == ctx.channel.id,
        )
    except asyncio.TimeoutError:
        m = await ctx.fail("**Disambiguation timer expired.**")
        messages.append(m.id)
        return
    else:
        messages.append(msg.id)
        if not msg.content.isdigit():
            m = await ctx.fail(
                f"**Disabiguation failed. `{msg.content}` is not a number.**"
            )
            messages.append(m.id)
            return
        index = int(msg.content)

        if index < 1 or index >= (len(matches) + 1):
            m = await ctx.fail("**Disabiguation failed. Invalid index provided.**")
            messages.append(m.id)
            return
        return matches[index - 1]
    finally:
        ctx.bot.loop.create_task(attempt_cleanup(ctx, messages))


async def attempt_cleanup(ctx, msg_ids):
    if ctx.channel.permissions_for(ctx.me).manage_messages:
        await ctx.channel.purge(check=lambda m: m.id in msg_ids)
    else:
        async for msg in ctx.history(limit=100, after=ctx.message):
            if msg.author == ctx.me and msg.id in msg_ids:
                await msg.delete()

class UniqueMember(commands.Converter):
    """
    Similar to DiscordMember, will raise
    AmbiguityError if multiple members are found.
    If mention or ID, return exact match.
    Try name#discrim then name, then nickname
    Finally fallback on case insensitivity.
    """

    async def get_by_id(self, ctx, member_id):
        """Ger member from ID."""
        result = None
        result = ctx.guild.get_member(member_id)
        if not result:
            raise commands.BadArgument(
                f"User `{await prettify(ctx, member_id)}` not found."
            )
        return result

    async def get_by_name(self, ctx, member_name):
        """
        Lookup a member by name. Username#Discriminator will decrease
        the chance of raising AmbiguityError. Case sensitivity is preserved
        to decrease the chances of raising AmbiguityError.
        Returns list of possible matches.
        """

        member_tags = [str(m) for m in ctx.guild.members]
        member_names = [m.name for m in ctx.guild.members]
        member_nicks = [m.display_name for m in ctx.guild.members]

        lower_member_tags = [str(m).lower() for m in ctx.guild.members]
        lower_member_names = [m.name.lower() for m in ctx.guild.members]
        lower_member_nicks = [m.display_name.lower() for m in ctx.guild.members]

        def pred(member):
            if member_name in member_tags:
                return str(member) == member_name
            if member_name in lower_member_tags:  # Case insensitive name#discrim
                return member.name.lower() == member_name.lower()
            if member_name in member_names:
                return member.name == member_name
            if member_name in lower_member_names:  # Case insensitive name
                return member.name.lower() == member_name.lower()
            if member_name in member_nicks:
                return member.display_name == member_name
            if member_name in lower_member_nicks:  # Case insensitive nickname
                return member.display_name.lower() == member_name.lower()

        results = [m for m in ctx.guild.members if pred(m)]
        if results:
            if len(results) > 1:
                raise exceptions.AmbiguityError(member_name, "User")
            return results[0]

    async def find_match(self, ctx, argument):
        """
        Get a match.
        If argument is a mention, try and get an exact match.
        If argument is  a number, try lookup by id.
        Fallback to lookup by name.
        """
        mention_match = USER_MENTION_REGEX.match(argument)
        if mention_match:
            return await self.get_by_id(ctx, int(mention_match.group(1)))

        lax_id_match = SNOWFLAKE_REGEX.match(argument)
        if lax_id_match:
            result = await self.get_by_id(ctx, int(lax_id_match.group(1)))
            if result:
                return result

        return await self.get_by_name(ctx, argument)

    async def convert(self, ctx, argument):
        if not ctx.guild:
            raise commands.NoPrivateMessage()
        match = await self.find_match(ctx, argument)

        if not match:
            raise commands.BadArgument(
                f"User `{await prettify(ctx, argument)}` not found."
            )

        failure = await checks.check_priv(ctx, match)
        if failure:
            raise exceptions.IntractabilityError(failure)
        return match


class UniqueRole(commands.Converter):
    """
    Similar to DiscordRole but will raise AmbiguityError
    if multiple results are found. Will also
    raise IntractabilityError if role cannot be manipulated.
    """

    async def get_by_id(self, ctx, user_id):
        """Exact role lookup by ID."""
        result = None
        result = ctx.guild.get_role(user_id)
        if not result:
            raise commands.BadArgument(
                f"Role `{await prettify(ctx, user_id)}` not found."
            )
        return result

    async def get_by_name(self, ctx, role_name):
        """
        Lookup by role name. If multiple roles are found,
        will raise ambiguous error. Retains case-sensitivity
        to reduce chance of exact name matches.
        """
        role_names = [r.name for r in ctx.guild.roles]

        def pred(role):
            if role_name in role_names:
                return role.name == role_name
            else:
                return role.name.lower() == role_name.lower()

        found = [r for r in ctx.guild.roles if pred(r)]
        if found:
            if len(found) > 1:
                raise exceptions.AmbiguityError(role_name, "Role")
            return found[0]

    async def find_match(self, ctx, argument):
        """
        If argument is a mention, try and get an exact match.
        If argument is a number, try lookup by id.
        Fallback to lookup by name.
        Raise AmbiguityError if multiple matches are found.
        """
        mention_match = ROLE_MENTION_REGEX.match(argument)
        if mention_match:
            return await self.get_by_id(ctx, int(mention_match.group(1)))

        lax_id_match = SNOWFLAKE_REGEX.match(argument)
        if lax_id_match:
            result = await self.get_by_id(ctx, int(lax_id_match.group(1)))
            if result:
                return result

        return await self.get_by_name(ctx, argument)

    async def convert(self, ctx, argument):
        if not ctx.guild:
            raise commands.NoPrivateMessage()
        match = await self.find_match(ctx, argument)

        if not match:
            raise commands.BadArgument(
                f"Role `{await prettify(ctx, argument)}` not found."
            )

        failure = await checks.role_priv(ctx, match)
        if failure:
            raise exceptions.IntractabilityError(failure)

        return match


class SearchEmojiConverter(commands.Converter):
    """Search for matching emoji."""

    async def get_by_id(self, ctx, emoji_id):
        """Exact emoji_id lookup."""
        if ctx.guild:
            result = discord.utils.get(ctx.guild.emojis, id=emoji_id)
        if not result:
            result = discord.utils.get(ctx.bot.emojis, id=emoji_id)
        return result

    async def get_by_name(self, ctx, emoji_name):
        """Lookup by name.
        Returns list of possible matches.
        Does a bot-wide case-insensitive match.
        """

        emoji_name = emoji_name.lower()

        def pred(emoji):
            return emoji.name.lower() == emoji_name

        return [e for e in ctx.bot.emojis if pred(e)]

    async def find_match(self, ctx, argument):
        """Get a match...
        If we have a number, try lookup by id.
        Fallback to lookup by name.
        Disambiguate in case we have multiple name results.
        """
        lax_id_match = SNOWFLAKE_REGEX.match(argument)
        if lax_id_match:
            result = await self.get_by_id(ctx, int(lax_id_match.group(1)))
            if result:
                return result

        results = await self.get_by_name(ctx, argument)
        if results:
            return results[0]

    async def convert(self, ctx, argument):
        match = await self.find_match(ctx, argument)

        if match:
            return match

        try:
            return await commands.converter.EmojiConverter().convert(ctx, argument)
        except commands.EmojiNotFound:
            pass

        try:
            return await commands.PartialEmojiConverter().convert(ctx, argument)
        except commands.PartialEmojiConversionFailure:
            pass

        lax_id_match = SNOWFLAKE_REGEX.match(argument)
        if lax_id_match:
            return discord.PartialEmoji(
                name="unknown", id=int(lax_id_match.group(1)), animated=False
            )

        raise commands.BadArgument(
            "Emoji `{}` not found".format(await prettify(ctx, argument))
        )


class GuildEmojiConverter(commands.Converter):
    """Search for matching emoji."""

    async def get_by_id(self, ctx, emoji_id):
        """Exact emoji_id lookup."""
        result = None
        if ctx.guild:
            result = discord.utils.get(ctx.guild.emojis, id=emoji_id)
        return result

    async def get_by_name(self, ctx, emoji_name):
        """Lookup by name.
        Returns list of possible matches.
        Does a bot-wide case-insensitive match.
        """

        def pred(emoji):
            return emoji.name.lower() == emoji_name.lower()

        return [e for e in ctx.guild.emojis if pred(e)]

    async def find_match(self, ctx, argument):
        """Get a match...
        If we have a number, try lookup by id.
        Fallback to lookup by name.
        Disambiguate in case we have multiple name results.
        """
        lax_id_match = SNOWFLAKE_REGEX.match(argument)
        if lax_id_match:
            result = await self.get_by_id(ctx, int(lax_id_match.group(1)))
            if result:
                return result

        results = await self.get_by_name(ctx, argument)
        if results:
            return results[0]

    async def convert(self, ctx, argument):
        match = await self.find_match(ctx, argument)

        if match:
            return match

        try:
            emoji = await commands.converter.EmojiConverter().convert(ctx, argument)
            if emoji.guild.id == ctx.guild.id:
                return emoji
        except commands.EmojiNotFound:
            pass

        try:
            emoji = await commands.PartialEmojiConverter().convert(ctx, argument)
            if emoji.guild.id == ctx.guild.id:
                return emoji
        except commands.PartialEmojiConversionFailure:
            pass

        lax_id_match = SNOWFLAKE_REGEX.match(argument)
        if lax_id_match:
            return discord.PartialEmoji(
                name="unknown", id=int(lax_id_match.group(1)), animated=False
            )

        raise commands.BadArgument(
            "Emoji `{}` not found".format(await prettify(ctx, argument))
        )


class DiscordCommand(commands.Converter):
    """
    Basic command converter.
    """

    async def convert(self, ctx, argument):
        command = ctx.bot.get_command(argument.lower())
        if not command:
            raise commands.BadArgument(
                f"Command `{await prettify(ctx, argument)}` not found."
            )
        return command


class DiscordBot(commands.Converter):
    """Resolve users/members.
    If given a username only checks current server. (Ease of use)
    If given a full DiscordTag or ID, will check current server for Member,
    fallback to bot for User.
    """

    async def get_by_id(self, ctx, bot_id):
        """Exact user_id lookup."""
        result = None
        if ctx.guild:
            result = ctx.guild.get_member(bot_id)
        if not result:
            try:
                result = await ctx.bot.fetch_user(bot_id)
            except discord.NotFound:
                raise commands.BadArgument(
                    f"Bot `{await prettify(ctx, bot_id)}` not found."
                )
        return result

    async def get_by_name(self, ctx, bot_name):
        """Lookup by name.
        Returns list of possible matches. For user#discrim will only give exact
        matches.
        Try doing an exact match.
        If within guild context, fall back to inexact match.
        If found in current guild, return Member, else User.
        (Will not do bot-wide inexact match)
        """
        tag_match = USERNAME_REGEX.match(bot_name)

        if tag_match:

            def pred(member):
                return member.name == tag_match.group(
                    1
                ) and member.discriminator == tag_match.group(2)

            result = None
            if ctx.guild:
                result = discord.utils.get(
                    ctx.guild.members,
                    name=tag_match.group(1),
                    discriminator=tag_match.group(2),
                )
            if not result:
                result = discord.utils.get(
                    ctx.bot.users,
                    name=tag_match.group(1),
                    discriminator=tag_match.group(2),
                )
            if result:
                return [result]

        if ctx.guild:
            user_name = bot_name.lower()

            def pred(member):
                return (
                    member.nick and member.nick.lower() == user_name
                ) or member.name.lower() == user_name

            return [m for m in ctx.guild.members if pred(m)]
        return []

    async def find_match(self, ctx, argument):
        mention_match = USER_MENTION_REGEX.match(argument)
        if mention_match:
            return await self.get_by_id(ctx, int(mention_match.group(1)))

        lax_id_match = SNOWFLAKE_REGEX.match(argument)
        if lax_id_match:
            result = await self.get_by_id(ctx, int(lax_id_match.group(1)))
            if result:
                return result

        results = await self.get_by_name(ctx, argument)
        if results:
            return await disambiguate(ctx, results)

    async def convert(self, ctx, argument):
        match = await self.find_match(ctx, argument)

        if not match:
            raise commands.BadArgument(
                f"Bot `{await prettify(ctx, argument)}` not found."
            )
        if match.bot:
            return match
        else:
            raise commands.BadArgument(
                f"User `{await prettify(ctx, argument)}` is not a bot."
            )


class DiscordUser(commands.Converter):
    """Resolve users/members.
    If given a username only checks current server. (Ease of use)
    If given a full DiscordTag or ID, will check current server for Member,
    fallback to bot for User.
    """

    def __init__(self, disambiguate=True) -> None:
        super().__init__()
        self.disambiguate = disambiguate

    async def get_by_id(self, ctx, user_id):
        """Exact user_id lookup."""
        result = None
        if ctx.guild:
            result = ctx.guild.get_member(user_id)
        if not result:
            try:
                result = await ctx.bot.fetch_user(user_id)
            except discord.NotFound:
                raise commands.BadArgument(
                    f"User `{await prettify(ctx, user_id)}` not found."
                )
        return result

    async def get_by_name(self, ctx, user_name):
        """Lookup by name.
        Returns list of possible matches. For user#discrim will only give exact
        matches.
        Try doing an exact match.
        If within guild context, fall back to inexact match.
        If found in current guild, return Member, else User.
        (Will not do bot-wide inexact match)
        """
        tag_match = USERNAME_REGEX.match(user_name)

        if tag_match:

            def pred(member):
                return member.name == tag_match.group(
                    1
                ) and member.discriminator == tag_match.group(2)

            result = None
            if ctx.guild:
                result = discord.utils.get(
                    ctx.guild.members,
                    name=tag_match.group(1),
                    discriminator=tag_match.group(2),
                )
            if not result:
                result = discord.utils.get(
                    ctx.bot.users,
                    name=tag_match.group(1),
                    discriminator=tag_match.group(2),
                )
            if result:
                return [result]

        if ctx.guild:
            user_name = user_name.lower()

            def pred(member):
                return (
                    member.nick and member.nick.lower() == user_name
                ) or member.name.lower() == user_name

            return [m for m in ctx.guild.members if pred(m)]
        return []

    async def find_match(self, ctx, argument):
        """Get a match...
        If we have a mention, try and get an exact match.
        If we have a number, try lookup by id.
        Fallback to lookup by name.
        Disambiguate in case we have multiple name results.
        """
        mention_match = USER_MENTION_REGEX.match(argument)
        if mention_match:
            return await self.get_by_id(ctx, int(mention_match.group(1)))

        lax_id_match = SNOWFLAKE_REGEX.match(argument)
        if lax_id_match:
            result = await self.get_by_id(ctx, int(lax_id_match.group(1)))
            if result:
                return result

        results = await self.get_by_name(ctx, argument)
        if results:
            if disambiguate:
                return await disambiguate(ctx, results)
            return results[0]

    async def convert(self, ctx, argument):
        match = await self.find_match(ctx, argument)

        if not match:
            raise commands.BadArgument(
                f"User `{await prettify(ctx, argument)}` not found."
            )
        return match


class DiscordGuild(commands.Converter):
    """Match guild_id, or guild name exact, only if author is in the guild."""

    def get_by_name(self, ctx, guild_name):
        """Lookup by name.
        Returns list of possible matches.
        Try doing an exact match.
        Fall back to inexact match.
        Will only return matches if ctx.author is in the guild.
        """
        if checks.is_admin(ctx):
            result = discord.utils.find(lambda g: g.name == guild_name, ctx.bot.guilds)
            if result:
                return [result]

            guild_name = guild_name.lower()

            return [g for g in ctx.bot.guilds if g.name.lower() == guild_name]
        else:
            result = discord.utils.find(
                lambda g: g.name == guild_name and g.get_member(ctx.author.id),
                ctx.bot.guilds,
            )
            if result:
                return [result]

            guild_name = guild_name.lower()

            return [
                g
                for g in ctx.bot.guilds
                if g.name.lower() == guild_name and g.get_member(ctx.author.id)
            ]

    async def find_match(self, ctx, argument):
        """Get a match...
        If we have a number, try lookup by id.
        Fallback to lookup by name.
        Only allow matches where ctx.author shares a guild.
        Disambiguate in case we have multiple name results.
        """
        lax_id_match = SNOWFLAKE_REGEX.match(argument)
        if lax_id_match:
            result = ctx.bot.get_guild(int(lax_id_match.group(1)))

            if checks.is_admin(ctx):
                if result:
                    return result
            else:
                if result and result.get_member(ctx.author.id):
                    return result

        results = self.get_by_name(ctx, argument)
        if results:
            return results[0]

    async def convert(self, ctx, argument):
        match = await self.find_match(ctx, argument)

        if not match:
            raise commands.BadArgument(
                f"Server `{await prettify(ctx, argument)}` not found."
            )
        return match


# converter from R.Danny
class BannedMember(commands.Converter):
    async def convert(self, ctx, argument):
        if argument.isdigit():
            member_id = int(argument, base=10)
            try:
                return await ctx.guild.fetch_ban(discord.Object(id=member_id))
            except discord.NotFound:
                raise commands.BadArgument(
                    f"User {await prettify(ctx, argument)} has not been previously banned."
                ) from None

        ban_list = await ctx.guild.bans()
        entity = discord.utils.find(lambda u: str(u.user) == argument, ban_list)

        if not entity:
            raise commands.BadArgument(
                f"User {await prettify(ctx, argument)} has not been previously banned."
            )
        return entity


class GlobalChannel(commands.Converter):
    async def convert(self, ctx, argument):
        try:
            return await commands.TextChannelConverter().convert(ctx, argument)
        except commands.BadArgument:
            # Not found... so fall back to ID + global lookup
            try:
                channel_id = int(argument, base=10)
            except ValueError:
                raise commands.BadArgument(
                    f"Could not find a channel by ID {argument!r}."
                )
            else:
                channel = ctx.bot.get_channel(channel_id)
                if channel is None:
                    raise commands.BadArgument(
                        f"Could not find a channel by ID {argument!r}."
                    )
                return channel


DiscordChannel = typing.Union[
    commands.converter.TextChannelConverter,
    commands.converter.VoiceChannelConverter,
    commands.converter.CategoryChannelConverter,
    commands.converter.StageChannelConverter,
    commands.converter.StoreChannelConverter,
]


class UserIDConverter(commands.Converter):
    async def convert(self, ctx, argument):
        if not argument.isdigit():
            raise commands.BadArgument("User IDs must be integers.")
        try:
            user = await ctx.guild.fetch_member(argument)
        except:
            try:
                user = await ctx.bot.fetch_user(argument)
            except discord.NotFound:
                raise commands.BadArgument("Invalid user.")
        return user


class DiscordMember(commands.Converter):
    """
    Basically the same as discord.Member
    Only difference is that this accepts
    case insensitive user inputs and
    resolves to member instances.
    """

    def __init__(self, disambiguate=True) -> None:
        super().__init__()
        self.disambiguate = disambiguate

    async def get_by_id(self, ctx, user_id):
        """Exact user_id lookup."""
        result = None
        result = ctx.guild.get_member(user_id)
        if not result:
            raise commands.BadArgument(
                f"User `{await prettify(ctx, user_id)}` not found."
            )
        return result

    async def get_by_name(self, ctx, user_name):
        """Lookup by name.
        Returns list of possible matches. For user#discrim will only give exact
        matches.
        Try doing an exact match.
        If within guild context, fall back to inexact match.
        If found in current guild, return Member, else User.
        (Will not do bot-wide inexact match)
        """
        tag_match = USERNAME_REGEX.match(user_name)

        if tag_match:

            def pred(member):
                return member.name == tag_match.group(
                    1
                ) and member.discriminator == tag_match.group(2)

            result = None
            if ctx.guild:
                result = discord.utils.get(
                    ctx.guild.members,
                    name=tag_match.group(1),
                    discriminator=tag_match.group(2),
                )
            if not result:
                raise commands.BadArgument(
                    f"User `{await prettify(ctx, user_name)}` not found."
                )
            if result:
                return [result]

        if ctx.guild:
            user_name = user_name.lower()

            def pred(member):
                return (
                    member.nick and member.nick.lower() == user_name
                ) or member.name.lower() == user_name

            return [m for m in ctx.guild.members if pred(m)]
        return []

    async def find_match(self, ctx, argument):
        """Get a match...
        If we have a mention, try and get an exact match.
        If we have a number, try lookup by id.
        Fallback to lookup by name.
        Disambiguate in case we have multiple name results.
        """
        mention_match = USER_MENTION_REGEX.match(argument)
        if mention_match:
            return await self.get_by_id(ctx, int(mention_match.group(1)))

        lax_id_match = SNOWFLAKE_REGEX.match(argument)
        if lax_id_match:
            result = await self.get_by_id(ctx, int(lax_id_match.group(1)))
            if result:
                return result

        results = await self.get_by_name(ctx, argument)
        if results:
            if self.disambiguate:
                return await disambiguate(ctx, results)
            return results[0]

    async def convert(self, ctx, argument):
        if not ctx.guild:
            raise commands.NoPrivateMessage()
        match = await self.find_match(ctx, argument)

        if not match:
            raise commands.BadArgument(
                f"User `{await prettify(ctx, argument)}` not found."
            )
        return match


class DiscordRole(commands.Converter):
    """
    Basically the same as discord.Role
    Only difference is that this accepts
    case insensitive user inputs and
    resolves to role instances.
    """

    async def get_by_id(self, ctx, user_id):
        """Exact role lookup."""
        result = None
        result = ctx.guild.get_role(user_id)
        if not result:
            raise commands.BadArgument(
                f"Role `{await prettify(ctx, user_id)}` not found."
            )
        return result

    async def get_by_name(self, ctx, role_name):
        """Lookup by name.
        Returns list of possible matches.
        Try doing an exact match.
        If within guild context, fall back to inexact match.
        If found in current guild, return Member, else User.
        (Will not do bot-wide inexact match)
        """
        if ctx.guild:
            role_name = role_name.lower()

            def pred(role):
                return role.name.lower() == role_name

            return [r for r in ctx.guild.roles if pred(r)]
        return []

    async def find_match(self, ctx, argument):
        """Get a match...
        If we have a mention, try and get an exact match.
        If we have a number, try lookup by id.
        Fallback to lookup by name.
        Disambiguate in case we have multiple name results.
        """
        mention_match = ROLE_MENTION_REGEX.match(argument)
        if mention_match:
            return await self.get_by_id(ctx, int(mention_match.group(1)))

        lax_id_match = SNOWFLAKE_REGEX.match(argument)
        if lax_id_match:
            result = await self.get_by_id(ctx, int(lax_id_match.group(1)))
            if result:
                return result

        results = await self.get_by_name(ctx, argument)
        if results:
            return await disambiguate(ctx, results)

    async def convert(self, ctx, argument):
        if not ctx.guild:
            raise commands.NoPrivateMessage()
        match = await self.find_match(ctx, argument)

        if not match:
            raise commands.BadArgument(
                f"Role `{await prettify(ctx, argument)}` not found."
            )
        return match


class BotServer(commands.Converter):
    async def convert(self, ctx, argument):
        if argument.isdigit():
            server_id = int(argument, base=10)
            try:
                server = ctx.bot.get_guild(server_id)
                if server is None:
                    raise commands.BadArgument(
                        f"Server `{await prettify(ctx, argument)}` not found."
                    )
                else:
                    return server
            except discord.HTTPException:
                raise commands.BadArgument(
                    f"Server `{await prettify(ctx, argument)}` not found."
                )
            except discord.Forbidden:
                raise commands.BadArgument(
                    f"Server `{await prettify(ctx, argument)}` not found."
                )
            except discord.NotFound:
                raise commands.BadArgument(
                    f"Server `{await prettify(ctx, argument)}` not found"
                )
            except Exception as e:
                await ctx.send_or_reply(e)
        options = [s for s in ctx.bot.guilds if argument.lower() in s.name.lower()]
        if options == []:
            raise commands.BadArgument(
                f"Server `{await prettify(ctx, argument)}` not found."
            )
        return options


class ActionReason(commands.Converter):
    async def convert(self, ctx, argument):
        ret = f"{ctx.author} (ID: {ctx.author.id}) in #{ctx.channel.name}: {argument}"

        if len(ret) > 512:
            reason_max = 512 - len(ret) + len(argument)
            raise commands.BadArgument(
                f"Reason is too long ({len(argument)}/{reason_max})"
            )
        return ret


class BotStatus(commands.Converter):
    async def convert(self, ctx, argument):
        online_options = ["online", "ready", "green"]
        idle_options = ["idle", "sleep", "yellow"]
        dnd_options = ["dnd", "do_not_disturb", "red"]
        offline_options = ["offline", "invisible", "gray"]
        if argument.lower() in online_options:
            status = "online"
        elif argument.lower() in idle_options:
            status = "idle"
        elif argument.lower() in dnd_options:
            status = "dnd"
        elif argument.lower() in offline_options:
            status = "offline"
        else:
            headers = ["ONLINE", "IDLE", "DND", "OFFLINE"]
            rows = tuple(
                zip(online_options, idle_options, dnd_options, offline_options)
            )
            table = formatting.TabularData()
            table.set_columns(headers)
            table.add_rows(rows)
            render = table.render()
            completed = f"```sml\nVALID STATUS OPTIONS:\n{render}```"
            raise commands.BadArgument(f"**Invalid Status.**{completed}")
        return status


class BotActivity(commands.Converter):
    async def convert(self, ctx, argument):
        playing_options = ["play", "playing", "game", "p"]
        listening_options = ["listen", "listening", "hearing", "l"]
        watching_options = ["watch", "watching", "looking", "w"]
        competing_options = ["comp", "competing", "compete", "c"]
        if argument.lower() in playing_options:
            activity = "playing"
        elif argument.lower() in listening_options:
            activity = "listening"
        elif argument.lower() in watching_options:
            activity = "watching"
        elif argument.lower() in competing_options:
            activity = "competing"
        else:
            headers = ["PLAYING", "LISTENING", "WATCHING", "COMPETING"]
            rows = tuple(
                zip(
                    playing_options,
                    listening_options,
                    watching_options,
                    competing_options,
                )
            )
            table = formatting.TabularData()
            table.set_columns(headers)
            table.add_rows(rows)
            render = table.render()
            completed = f"```sml\nVALID ACTIVITY OPTIONS:\n{render}```"
            raise commands.BadArgument(f"**Invalid Activity.**{completed}")
        return activity


class SingleOrQueue(commands.Converter):
    async def convert(self, ctx, argument):
        queue_options = ["playlist", "queue", "songs", "all", "q"]
        single_options = ["current", "single", "track", "song", "one"]
        if argument.lower() in queue_options:
            option = "queue"
        elif argument.lower() in single_options:
            option = "single"
        else:
            headers = ["LOOP QUEUE", "LOOP SONG"]
            rows = tuple(zip(queue_options, single_options))
            table = formatting.TabularData()
            table.set_columns(headers)
            table.add_rows(rows)
            render = table.render()
            completed = f"```sml\nVALID LOOP OPTIONS:\n{render}```"
            raise commands.BadArgument(f"**Invalid Option.**{completed}")
        return option


class Flag(commands.Converter):
    async def convert(self, ctx, argument):
        nodm_options = ["--nodm", "--nopm", "-nodm", "-nopm", " nodm", " nopm"]
        dm_options = ["--dm", "--pm", "-dm", "-pm", " dm", " pm"]
        if argument in ["--nodm", "--nopm", "-nodm", "-nopm", "nodm", "nopm"]:
            dm_bool = False
        elif argument in ["--dm", "--pm", "-dm", "-pm", "dm", "pm"]:
            dm_bool = True
        else:
            headers = ["SEND DM", "DO NOT DM"]
            rows = tuple(zip(dm_options, nodm_options))
            table = formatting.TabularData()
            table.set_columns(headers)
            table.add_rows(rows)
            render = table.render()
            completed = f"```sml\nVALID FLAGS:\n{render}```"
            raise commands.BadArgument(f"**Invalid flag.**{completed}")
        return dm_bool


class Arguments(argparse.ArgumentParser):
    def error(self, message):
        raise RuntimeError(message)


class Prefix(commands.Converter):
    async def convert(self, ctx, argument):
        user_id = ctx.bot.user.id
        if argument.startswith((f"<@{user_id}>", f"<@!{user_id}>")):
            raise commands.BadArgument("That prefix cannot be modified.")
        elif len(argument) > 20:
            raise commands.BadArgument("Max prefix length is 20 characters.")
        return argument


# Command Specific Converters


class MassRoleConverter(commands.Converter):
    """
    Converter for massrole command
    """

    async def convert(self, ctx, argument):
        role_options = ["must be a valid role.", "e.g. @Helper"]
        all_options = ["all", "everyone"]
        human_options = ["humans", "people"]
        bots_options = ["bots", "robots"]
        try:
            role = await DiscordRole().convert(ctx, argument)
            return role
        except Exception:
            if argument.lower() in all_options:
                option = "all"
            elif argument.lower() in human_options:
                option = "humans"
            elif argument.lower() in bots_options:
                option = "bots"
            else:
                headers = ["ROLE", "ALL", "HUMANS", "BOTS"]
                rows = tuple(
                    zip(
                        role_options,
                        all_options,
                        human_options,
                        bots_options,
                    )
                )
                table = formatting.TabularData()
                table.set_columns(headers)
                table.add_rows(rows)
                render = table.render()
                completed = (
                    f"```sml\nVALID {str(ctx.command).upper()} OPTIONS:\n{render}```"
                )
                raise commands.BadArgument(f"**Invalid Option.**{completed}")
            return option


class ChannelOrRoleOrMember(commands.Converter):
    """
    Converter for config command group
    """

    async def convert(self, ctx, argument):
        try:
            return await commands.TextChannelConverter().convert(ctx, argument)
        except commands.ChannelNotFound:
            try:
                return await DiscordRole().convert(ctx, argument)
            except Exception:
                try:
                    return await DiscordMember().convert(ctx, argument)
                except Exception:
                    raise commands.BadArgument(
                        f"Entity `{await prettify(ctx, argument)}` is an invalid input. Please specify a channel, role, or user."
                    )


class LoggingEvent(commands.Converter):
    async def convert(self, ctx, argument):
        log_types = {
            "all": "Enable all logging events.",
            "avatars": "Log when users change their avatar.",
            "channels": "Log when channels are created, deleted, and updated.",
            "emojis": "Log when emojis are added, removed, or edited.",
            "invites": "Log when discord invites are posted, created, and deleted.",
            "joins": "Log when users join the server.",
            "leaves": "Log when users leave the server.",
            "messages": "Log when messages are purged, deleted, and edited.",
            "moderation": "Log when a moderation action is performed using the bot.",
            "nicknames": "Log when users change their nickname.",
            "usernames": "Log when users change their username.",
            "roles": "Log when roles are created, deleted, updated, and added/removed from users.",
            "server": "Log when the server's icon, banner, name, or region is updated.",
            "voice": "Log when users join, leave and switch voice channels.",
        }

        if argument.lower() not in log_types.keys():
            headers = ["EVENT", "DESCRIPTION"]
            table = formatting.TabularData()
            table.set_columns(headers)
            table.add_rows([(event, desc) for event, desc in log_types.items()])
            render = table.render()
            completed = f"```yml\nVALID EVENTS:\n{render}```"
            raise commands.BadArgument(f"**Invalid Event.**{completed}")
        else:
            return argument.lower()


class ServerDataOption(commands.Converter):
    async def convert(self, ctx, argument):
        types = {
            "invites": "Delete all invite data recorded for a user on this server.",
            "messages": "Delete all message data recorded for a user on this server.",
            "nicknames": "Delete all recorded nicknames for a user on this server.",
        }

        if argument.lower() not in types.keys():
            headers = ["OPTION", "DESCRIPTION"]
            table = formatting.TabularData()
            table.set_columns(headers)
            table.add_rows([(event, desc) for event, desc in types.items()])
            render = table.render()
            completed = f"```yml\nVALID OPTIONS:\n{render}```"
            raise commands.BadArgument(f"**Invalid Option.**{completed}")
        else:
            return argument.lower()

class UserDataOption(commands.Converter):
    async def convert(self, ctx, argument):
        types = {
            "avatars": "Delete all recorded avatars.",
            "statuses": "Delete all recorded status data.",
            "usernames": "Delete all recorded usernames.",
        }

        if argument.lower() not in types.keys():
            headers = ["OPTION", "DESCRIPTION"]
            table = formatting.TabularData()
            table.set_columns(headers)
            table.add_rows([(event, desc) for event, desc in types.items()])
            render = table.render()
            completed = f"```yml\nVALID OPTIONS:\n{render}```"
            raise commands.BadArgument(f"**Invalid Option.**{completed}")
        else:
            return argument.lower()


class ChannelOrRoleOrMemberOption(commands.Converter):
    async def convert(self, ctx, argument):
        server_options = ["servers", "server", "guilds", "guild"]
        channel_options = ["channels", "channel", "textchannels", "textchannel"]
        member_options = ["users", "user", "members", "member"]
        role_options = ["roles", "role", "discordrole", "r"]
        if argument.lower() in channel_options:
            option = "channels"
        elif argument.lower() in member_options:
            option = "users"
        elif argument.lower() in role_options:
            option = "roles"
        elif argument.lower() in server_options:
            option = "servers"
        else:
            headers = ["SERVER", "CHANNEL", "ROLE", "USER"]
            rows = tuple(
                zip(
                    server_options,
                    channel_options,
                    role_options,
                    member_options,
                )
            )
            table = formatting.TabularData()
            table.set_columns(headers)
            table.add_rows(rows)
            render = table.render()
            completed = f"```sml\nVALID OPTIONS:\n{render}```"
            raise commands.BadArgument(f"**Invalid Option.**{completed}")
        return option
