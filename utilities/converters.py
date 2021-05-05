import argparse
import re
import typing

import discord
from discord.ext import commands

EMOJI_REGEX = re.compile(r"<a?:.+?:([0-9]{15,21})>")
EMOJI_NAME_REGEX = re.compile(r"[0-9a-zA-Z\_]{2,32}")


tag_regex = re.compile(r"(.*)#(\d{4})")
lax_id_regex = re.compile(r"([0-9]{15,21})$")
mention_regex = re.compile(r"<@!?([0-9]+)>$")


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
        except commands.BadArgument:
            pass

        try:
            return await commands.PartialEmojiConverter().convert(ctx, argument)
        except commands.BadArgument:
            pass

        lax_id_match = lax_id_regex.match(argument)
        if lax_id_match:
            return discord.PartialEmoji(
                name="unknown", id=int(lax_id_match.group(1)), animated=False
            )

        raise commands.BadArgument('Emoji "{}" not found'.format(argument))


class DiscordCommand(commands.Converter):
    """
    Basic command converter.
    """

    async def convert(self, ctx, argument):
        command = ctx.bot.get_command(argument.lower())
        if not command:
            raise commands.BadArgument(f"Command `{argument}` not found.")
        return command


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
                raise commands.BadArgument(f"User {user_id} not found")
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
            raise commands.BadArgument("User `{}` not found".format(argument))
        return match


class BotServer(commands.Converter):
    async def convert(self, ctx, argument):
        if argument.isdigit():
            server_id = int(argument, base=10)
            try:
                server = ctx.bot.get_guild(server_id)
                if server is None:
                    raise commands.BadArgument("Server `{}` not found".format(argument))
                else:
                    return server
            except discord.HTTPException:
                raise commands.BadArgument("Server `{}` not found".format(argument))
            except discord.Forbidden:
                raise commands.BadArgument("Server `{}` not found".format(argument))
            except discord.NotFound:
                raise commands.BadArgument("Server `{}` not found".format(argument))
            except Exception as e:
                await ctx.send_or_reply(e)
        options = [
            (s, f"{s.id}: {s.name}")
            for s in ctx.bot.guilds
            if argument.lower() in s.name.lower()
        ]
        if options == []:
            raise commands.BadArgument("Server `{}` not found".format(argument))
        return options


# Similar to Botserver but does not return a list of findings
class DiscordGuild(commands.Converter):
    async def convert(self, ctx, argument):
        if argument.isdigit():
            server_id = int(argument, base=10)
            server = ctx.bot.get_guild(server_id)
            if not server:
                raise commands.BadArgument(f"Server `{argument}` not found.")
            return server
        else:
            server = discord.utils.find(
                lambda s: argument.lower() in str(s.name).lower(), ctx.bot.guilds
            )
            if not server:
                raise commands.BadArgument(f"Server `{argument}` not found.")
            return server


# converter from R.Danny
class BannedMember(commands.Converter):
    async def convert(self, ctx, argument):
        if argument.isdigit():
            member_id = int(argument, base=10)
            try:
                return await ctx.guild.fetch_ban(discord.Object(id=member_id))
            except discord.NotFound:
                raise commands.BadArgument(
                    "This member has not been banned before."
                ) from None

        ban_list = await ctx.guild.bans()
        entity = discord.utils.find(lambda u: str(u.user) == argument, ban_list)

        if entity is None:
            raise commands.BadArgument("This member has not been banned before.")
        return entity


class Arguments(argparse.ArgumentParser):
    def error(self, message):
        raise RuntimeError(message)


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


class ActionReason(commands.Converter):
    async def convert(self, ctx, argument):
        ret = f"{ctx.author} (ID: {ctx.author.id}) in #{ctx.channel.name}: {argument}"

        if len(ret) > 512:
            reason_max = 512 - len(ret) + len(argument)
            raise commands.BadArgument(
                f"Reason is too long ({len(argument)}/{reason_max})"
            )
        return ret


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
