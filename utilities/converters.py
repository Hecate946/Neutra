import re
import typing
import argparse

import discord
from discord.ext import commands

from utilities import checks
from utilities import formatting

EMOJI_REGEX = re.compile(r"<a?:.+?:([0-9]{15,21})>")
EMOJI_NAME_REGEX = re.compile(r"[0-9a-zA-Z\_]{2,32}")


tag_regex = re.compile(r"(.*)#(\d{4})")
lax_id_regex = re.compile(r"([0-9]{15,21})$")
mention_regex = re.compile(r"<@!?([0-9]+)>$")
ROLE_MENTION_REGEX = re.compile(r"<@&([0-9]+)>$")


async def prettify(ctx, arg):
    pretty_arg = await commands.clean_content().convert(ctx, str(arg))
    return pretty_arg


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
        lax_id_match = lax_id_regex.match(argument)
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

        lax_id_match = lax_id_regex.match(argument)
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
        lax_id_match = lax_id_regex.match(argument)
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

        lax_id_match = lax_id_regex.match(argument)
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
        tag_match = tag_regex.match(bot_name)

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
        mention_match = mention_regex.match(argument)
        if mention_match:
            return await self.get_by_id(ctx, int(mention_match.group(1)))

        lax_id_match = lax_id_regex.match(argument)
        if lax_id_match:
            result = await self.get_by_id(ctx, int(lax_id_match.group(1)))
            if result:
                return result

        results = await self.get_by_name(ctx, argument)
        if results:
            return results[0]

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
        tag_match = tag_regex.match(user_name)

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
        mention_match = mention_regex.match(argument)
        if mention_match:
            return await self.get_by_id(ctx, int(mention_match.group(1)))

        lax_id_match = lax_id_regex.match(argument)
        if lax_id_match:
            result = await self.get_by_id(ctx, int(lax_id_match.group(1)))
            if result:
                return result

        results = await self.get_by_name(ctx, argument)
        if results:
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
        lax_id_match = lax_id_regex.match(argument)
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
                    f"Member {await prettify(ctx, argument)} has not been previously banned."
                ) from None

        ban_list = await ctx.guild.bans()
        entity = discord.utils.find(lambda u: str(u.user) == argument, ban_list)

        if entity is None:
            raise commands.BadArgument(
                f"Member {await prettify(ctx, argument)} has not been previously banned."
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
        tag_match = tag_regex.match(user_name)

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
        mention_match = mention_regex.match(argument)
        if mention_match:
            return await self.get_by_id(ctx, int(mention_match.group(1)))

        lax_id_match = lax_id_regex.match(argument)
        if lax_id_match:
            result = await self.get_by_id(ctx, int(lax_id_match.group(1)))
            if result:
                return result

        results = await self.get_by_name(ctx, argument)
        if results:
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

        result = None
        if ctx.guild:
            result = discord.utils.find(
                lambda s: role_name.lower() == str(s.name).lower(), ctx.guild.roles
            )
            if not result:
                raise commands.BadArgument(
                    f"Role `{await prettify(ctx, role_name)}` not found."
                )
            if result:
                return [result]
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

        lax_id_match = lax_id_regex.match(argument)
        if lax_id_match:
            result = await self.get_by_id(ctx, int(lax_id_match.group(1)))
            if result:
                return result

        results = await self.get_by_name(ctx, argument)
        if results:
            return results[0]

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
