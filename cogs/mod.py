import re
import json
import shlex
import typing
import asyncio
import asyncpg
import discord

from collections import Counter
from discord.ext import commands

from settings import database

from utilities import humantime
from utilities import utils
from utilities import checks
from utilities import helpers
from utilities import converters
from utilities import decorators


def setup(bot):
    bot.add_cog(Mod(bot))


class Mod(commands.Cog):
    """
    Keep your server under control.
    """

    def __init__(self, bot):
        self.bot = bot
        self.mregex = re.compile(r"[0-9]{17,21}")
        self.dregex = re.compile(
            r"(?:https?://)?discord(?:app)?\.(?:com/invite|gg)/[a-zA-Z0-9]+/?"
        )
        self.uregex = re.compile(
            r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*(),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+"
        )

    ####################
    ## VOICE COMMANDS ##
    ####################

    @decorators.command(brief="Move a user from a voice channel.")
    @commands.guild_only()
    @checks.bot_has_perms(move_members=True)
    @checks.has_perms(move_members=True)
    async def vcmove(
        self,
        ctx,
        targets: commands.Greedy[converters.DiscordMember], *,
        channel: discord.VoiceChannel,
    ):
        """
        Usage: {0}vcmove <targets>... <channel>
        Output: Moves members into a new voice channel
        Permission: Move Members
        """
        if not len(targets) or not channel:
            return await ctx.usage()

        vcmoved = []
        for target in targets:
            try:
                await target.edit(voice_channel=channel)
            except discord.HTTPException:
                await ctx.send_or_reply(
                    content=f"{self.bot.emote_dict['warn']} Target is not connected to a voice channel"
                )
                continue
            vcmoved.append(str(target))
        if vcmoved:
            await ctx.send_or_reply(
                content=f"{self.bot.emote_dict['success']} VC Moved `{', '.join(vcmoved)}`"
            )

    @decorators.command(brief="Kick all users from a voice channel.")
    @commands.guild_only()
    @checks.has_perms(move_members=True)
    @checks.bot_has_perms(move_members=True)
    async def vcpurge(self, ctx, *, channel: discord.VoiceChannel = None):
        """
        Usage: {0}vcpurge <voice channel>
        Output: Kicks all members from the channel
        Permission: Move Members
        """
        if channel is None:
            return await ctx.send_or_reply(
                content=f"Usage: `{ctx.prefix}vcpurge <voice channel name/id>`",
            )
        if len(channel.members) == 0:
            return await ctx.send_or_reply(
                content=f"{self.bot.emote_dict['warn']} No members in voice channel {channel.mention}.",
            )
        failed = []
        for member in channel.members:
            try:
                await member.edit(voice_channel=None)
            except Exception as e:
                failed.append((str(member), e))
                continue
        await ctx.send_or_reply(
            content=f"{self.bot.emote_dict['success']} Purged {channel.mention}.",
        )
        if failed:
            await ctx.send_or_reply(
                content=f"{self.bot.emote_dict['success']} Failed to vckick {len(failed)} user{'' if len(failed) == 1 else 's'}.",
            )

    @decorators.command(brief="Kick users from a voice channel.")
    @commands.guild_only()
    @checks.has_perms(move_members=True)
    @checks.bot_has_perms(move_members=True)
    async def vckick(self, ctx, targets: commands.Greedy[converters.DiscordMember]):
        """
        Usage: {0}vckick <targets>...
        Output: Kicks passed members from their channel
        Permission: Move Members
        """
        if not len(targets):
            return await ctx.send_or_reply(
                content=f"Usage: `{ctx.prefix}vckick <target> [target]...`",
            )
        vckicked = []
        for target in targets:
            try:
                await target.edit(voice_channel=None)
            except discord.HTTPException:
                await ctx.send_or_reply(
                    f"{self.bot.emote_dict['warn']} Target is not connected to a voice channel."
                )
            vckicked.append(str(target))
        if vckicked:
            await ctx.send_or_reply(
                content=f"{self.bot.emote_dict['success']} VC Kicked `{', '.join(vckicked)}`"
            )

    ##########################
    ## Restriction Commands ##
    ##########################

    async def restrictor(self, ctx, targets, on_or_off, block_or_blind):
        overwrite = discord.PermissionOverwrite()
        if on_or_off == "on":
            boolean = False
        else:
            boolean = None
        if block_or_blind == "block":
            overwrite.send_messages = boolean
        else:
            overwrite.read_messages = boolean
        restrict = []
        failed = []
        for target in targets:
            res = await checks.check_priv(ctx, target)
            if res:
                failed.append((str(target), res))
                continue
            try:
                await ctx.channel.set_permissions(target, overwrite=overwrite)
                restrict.append(str(target))
            except Exception as e:
                failed.append((str(target), e))
                continue
        if restrict:
            await ctx.send_or_reply(
                content=f"{self.bot.emote_dict['success']} {ctx.command.name.capitalize()}ed `{', '.join(restrict)}`"
            )
            self.bot.dispatch("mod_action", ctx, targets=restrict)
        if failed:
            await helpers.error_info(ctx, failed)

    @decorators.command(brief="Restrict users from sending messages.")
    @commands.guild_only()
    @checks.has_perms(kick_members=True)
    async def block(self, ctx, targets: commands.Greedy[converters.DiscordMember]):
        """
        Usage: {0}block <target> [target]...
        Example: {0}block Hecate 708584008065351681 @Elizabeth
        Permission: Kick Members
        Output: Stops users from messaging in the channel.
        """
        if not len(targets):
            return await ctx.send_or_reply(
                content=f"Usage: `{ctx.prefix}block <target> [target] [target]...`",
            )
        await self.restrictor(ctx, targets, "on", "block")

    @decorators.command(brief="Reallow users to send messages.")
    @commands.guild_only()
    @checks.has_perms(kick_members=True)
    async def unblock(
        self, ctx, targets: commands.Greedy[converters.DiscordMember] = None
    ):
        """
        Usage:      {0}unblock <target> [target]...
        Example:    {0}unblock Hecate 708584008065351681 @Elizabeth
        Permission: Kick Members
        Output:     Reallows blocked users to send messages.
        """
        if not targets:  # checks if there is user
            return await ctx.send_or_reply(
                content=f"Usage: `{ctx.prefix}unblock <target> [target] [target]...`",
            )
        await self.restrictor(ctx, targets, "off", "unblock")

    @decorators.command(brief="Hide a channel from a user.")
    @commands.guild_only()
    @checks.has_perms(kick_members=True)
    async def blind(
        self, ctx, targets: commands.Greedy[converters.DiscordMember] = None
    ):
        """
        Usage:      {0}blind <target> [target]...
        Example:    {0}blind Hecate 708584008065351681 @Elizabeth
        Permission: Kick Members
        Output:     Prevents users from seeing the channel.
        """
        if not targets:  # checks if there is user
            return await ctx.send_or_reply(
                content=f"Usage: `{ctx.prefix}blind <target> [target] [target]...`",
            )
        await self.restrictor(ctx, targets, "on", "blind")

    @decorators.command(brief="Reallow users see a channel.")
    @commands.guild_only()
    @checks.has_perms(kick_members=True)
    async def unblind(
        self, ctx, targets: commands.Greedy[converters.DiscordMember] = None
    ):
        """
        Usage:      {0}unblind <targets>...
        Example:    {0}unblind Hecate 708584008065351681 @Elizabeth
        Permission: Kick Members
        Output:     Reallows blinded users to see the channel.
        """
        if not targets:  # checks if there is user
            return await ctx.usage()
        await self.restrictor(ctx, targets, "off", "unblind")

    ##################
    ## Kick Command ##
    ##################

    @decorators.command(brief="Kick users from the server.")
    @commands.guild_only()
    @checks.bot_has_perms(kick_members=True)
    @checks.has_perms(kick_members=True)
    async def kick(
        self,
        ctx,
        users: commands.Greedy[converters.DiscordMember],
        *,
        reason: typing.Optional[str] = "No reason",
    ):
        """
        Usage:      {0}kick <target> [target]... [reason]
        Example:    {0}kick @Jacob Sarah for advertising
        Permission: Kick Members
        Output:     Kicks passed members from the server.
        """
        if not len(users):
            await ctx.usage()

        kicked = []
        failed = []
        for target in users:
            res = await checks.check_priv(ctx, target)
            if res:
                failed.append((str(target), res))
                continue
            try:
                await ctx.guild.kick(target, reason=reason)
                kicked.append(str(target))
            except Exception as e:
                failed.append((str(target), e))
                continue
        if kicked:
            await ctx.send_or_reply(
                content=f"{self.bot.emote_dict['success']} Kicked `{', '.join(kicked)}`",
            )
            self.bot.dispatch("mod_action", ctx, targets=kicked)
        if failed:
            await helpers.error_info(ctx, failed)

    ##################
    ## Ban Commands ##
    ##################

    @decorators.command(
        brief="Ban users from the server.",
        permissions=["ban_members"],
    )
    @commands.guild_only()
    @checks.bot_has_perms(ban_members=True)
    @checks.has_perms(ban_members=True)
    async def ban(
        self,
        ctx,
        targets: commands.Greedy[converters.DiscordMember],
        delete_message_days: typing.Optional[int] = 1,
        *,
        reason: typing.Optional[str] = "No reason.",
    ):
        """
        Usage: {0}ban <targets>... [delete message days = 1] [reason = "No reason"]
        Example: {0}ban @Jacob Sarah 4 for advertising
        Permission: Ban Members
        Output: Ban passed members from the server.
        """
        if not len(targets):
            return await ctx.usage()

        if delete_message_days > 7:
            delete_message_days = 7
        elif delete_message_days < 0:
            delete_message_days = 0

        banned = []
        failed = []
        for target in targets:
            res = await checks.check_priv(ctx, target)
            if res:
                failed.append((str(target), res))
                continue
            try:
                await ctx.guild.ban(
                    target,
                    reason=await converters.ActionReason().convert(ctx, reason),
                    delete_message_days=delete_message_days,
                )
                banned.append(str(target))
            except Exception as e:
                failed.append((str(target), e))
                continue
        if banned:
            await ctx.success(f"Banned `{', '.join(banned)}`")
            self.bot.dispatch("mod_action", ctx, targets=banned)
        if failed:
            await helpers.error_info(ctx, failed)

    @decorators.command(brief="Softban users from the server.")
    @commands.guild_only()
    @checks.bot_has_perms(ban_members=True)
    @checks.has_perms(kick_members=True)
    async def softban(
        self,
        ctx,
        targets: commands.Greedy[converters.DiscordMember],
        delete_message_days: typing.Optional[int] = 7,
        *,
        reason: typing.Optional[str] = "No reason.",
    ):
        """
        Usage:      -softban <targets> [delete message = 7] [reason]
        Example:    -softban @Jacob Sarah 6 for advertising
        Permission: Kick Members
        Output:     Softbans members from the server.
        Notes:
            A softban bans the member and immediately
            unbans s/he in order to delete messages.
            The days to delete messages is set to 7 days.
        """
        if not len(targets):
            return await ctx.usage("<user> [days to delete messages] [reason]")

        if delete_message_days > 7:
            delete_message_days = 7
        elif delete_message_days < 0:
            delete_message_days = 0

        banned = []
        failed = []
        for target in targets:
            res = await checks.check_priv(ctx, target)
            if res:
                failed.append((str(target), res))
                continue
            try:
                await ctx.guild.ban(
                    target,
                    reason=await converters.ActionReason().convert(ctx, reason),
                    delete_message_days=delete_message_days,
                )
                await ctx.guild.unban(
                    target, reason= await converters.ActionReason().convert(ctx, reason)
                )
                banned.append(str(target))
            except Exception as e:
                failed.append((str(target), e))
                continue
        if banned:
            await ctx.success(f"Softbanned `{', '.join(banned)}`")
            self.bot.dispatch("mod_action", ctx, targets=banned)
        if failed:
            await helpers.error_info(ctx, failed)

    @decorators.command(brief="Hackban multiple users.")
    @checks.bot_has_perms(ban_members=True)
    @checks.has_perms(ban_members=True)
    async def hackban(
        self,
        ctx,
        users: commands.Greedy[converters.UserIDConverter],
        *,
        args=None,
    ):
        """
        Usage: -hackban <user id> <user id>... [--reason] [--delete]
        Example:
            -hackban 805871188462010398 --reason for spamming --delete 2
        Permission: Ban Members
        Output: Hackbans multiple users.
        Notes: Users do not have to be in the server.
        """
        if not len(users):
            return await ctx.usage("<user> [user]... [--reason] [--delete]")

        if args:
            parser = converters.Arguments(add_help=False, allow_abbrev=False)
            parser.add_argument("--reason", nargs="+", default="No reason.")
            parser.add_argument("--delete", type=int, default=1)

            try:
                args = parser.parse_args(shlex.split(args))
            except Exception as e:
                return await ctx.fail(str(e).capitalize())

            if args.reason:
                reason = " ".join(args.reason)
            reason = await converters.ActionReason().convert(ctx, reason)

            if args.delete:
                delete = args.delete
                if delete > 7:
                    delete = 7
                if delete < 0:
                    delete = 0
            else:
                delete = 1
        else:
            delete = 1
            reason = "No reason"
        banned = []
        failed = []
        for user in users:
            if isinstance(user, discord.Member):
                res = await checks.check_priv(ctx, user)
                if res:
                    failed.append((str(user), res))
                    continue
            try:
                await ctx.guild.ban(
                    user,
                    reason=reason,
                    delete_message_days=delete,
                )
                banned.append(str(user))
            except Exception as e:
                failed.append((str(user), e))
                continue
        if banned:
            await ctx.success(f"Hackbanned `{', '.join(banned)}`")
            self.bot.dispatch("mod_action", ctx, targets=banned)
        if failed:
            await helpers.error_info(ctx, failed)

    @decorators.command(brief="Unban a previously banned user.", aliases=["revokeban"])
    @commands.guild_only()
    @checks.has_perms(ban_members=True)
    async def unban(self, ctx, member: converters.BannedMember, *, reason: str = None):
        """
        Usage:      -unban <user> [reason]
        Alias:      -revokeban
        Example:    Unban Hecate#3523 Because...
        Permission: Ban Members
        Output:     Unbans a member from the server.
        Notes:      Pass either the user's ID or their username
        """
        if not member:
            return await ctx.send_or_reply(
                content=f"Usage: `{ctx.prefix}unban <id/name#discriminator> [reason]`",
            )
        if reason is None:
            reason = utils.responsible(
                ctx.author, f"Unbanned member {member} by command execution"
            )

        await ctx.guild.unban(member.user, reason=reason)
        if member.reason:
            await ctx.send_or_reply(
                content=f'{self.bot.emote_dict["success"]} Unbanned `{member.user} (ID: {member.user.id})`, previously banned for `{member.reason}.`',
            )
        else:
            await ctx.send_or_reply(
                content=f'{self.bot.emote_dict["success"]} Unbanned `{member.user} (ID: {member.user.id}).`',
            )
        self.bot.dispatch("mod_action", ctx, targets=[str(member.user)])

    # https://github.com/AlexFlipnote/discord_bot.py with my own additions

    ###################
    ## Prune Command ##
    ###################

    @decorators.group(
        brief="Remove any type of content.",
        aliases=["prune", "delete", "remove"],
        description="Methods:"
        "\nAll - Purge all messages."
        "\nBots - Purge messages sent by bots."
        "\nContains - Custom purge messages."
        "\nEmbeds - Purge messages with embeds."
        "\nEmojis - Purge messages with emojis."
        "\nFiles - Purge messages with attachments."
        "\nHumans - Purge  messages sent by humans."
        "\nImages - Purge messages with images."
        "\nInvites - Purge messages with invites."
        "\nMentions - Purge messages with mentions."
        "\nReactions - Purge reactions from messages."
        "\nUntil - Purge messages until a message."
        "\nUrls - Purge messages with URLs."
        "\nUser - Purge messages sent by a user."
        "\nWebhooks - Purge messages sent by wehooks.",
    )
    @commands.guild_only()
    @commands.max_concurrency(5, per=commands.BucketType.guild)
    @checks.bot_has_perms(manage_messages=True)
    @checks.has_perms(manage_messages=True)
    async def purge(self, ctx):
        """
        Usage: -purge <option> <amount>
        Aliases: -prune, -delete, -remove
        Permission: Manage Messages
        Options:
            all, bots, contains, embeds,
            emojis, files, humans, images,
            invites, mentions, reactions,
            until, urls, user, webhooks.
        Output:
            Deletes messages that match
            a specific search criteria
        Examples:
            -prune user Hecate
            -prune bots
            -prune invites 1000
        Notes:
            Specify the amount kwarg
            to search that number of
            messages. For example,
            -prune user Hecate 1000
            will search for all messages
            in the past 1000 sent in the
            channel, and delete all that
            were sent by Hecate.
            Default amount is 100.
        """
        args = str(ctx.message.content).split(" ")
        if ctx.invoked_subcommand is None:
            try:
                args[1]
            except IndexError:
                return await ctx.usage("<option> [amount]")
            await self._remove_all(ctx, search=int(args[1]))

    async def do_removal(
        self, ctx, limit, predicate, *, before=None, after=None, message=True
    ):
        if limit > 2000:
            return await ctx.send_or_reply(
                content=f"Too many messages to search given ({limit}/2000)",
            )

        if not before:
            before = ctx.message
        else:
            before = discord.Object(id=before)

        if after:
            after = discord.Object(id=after)

        try:
            deleted = await ctx.channel.purge(
                limit=limit, before=before, after=after, check=predicate
            )
        except discord.Forbidden:
            return await ctx.send_or_reply(
                content="I do not have permissions to delete messages.",
            )
        except discord.HTTPException as e:
            return await ctx.send_or_reply(
                content=f"Error: {e} (try a smaller search?)",
            )

        deleted = len(deleted)
        if message is True:
            msg = await ctx.send_or_reply(
                content=f'{self.bot.emote_dict["trash"]} Deleted {deleted} message{"" if deleted == 1 else "s"}',
            )
            await asyncio.sleep(7)
            await ctx.message.delete()
            await msg.delete()

    @purge.command(brief="Purge messages with embeds.")
    async def embeds(self, ctx, search=100):
        """
        Usage: -purge embeds [amount]
        Output:
            Deletes all messages that
            contain embeds in them.
        Examples:
            -purge embeds 2000
            -prune embeds
        """
        await self.do_removal(ctx, search, lambda e: len(e.embeds))

    @purge.command(brief="Purge messages with invites.", aliases=["ads"])
    async def invites(self, ctx, search=100):
        """
        Usage: -purge invites [amount]
        Alias: -purge ads
        Output:
            Deletes all messages with
            invite links in them.
        Examples:
            -purge invites
            -prune invites 125
        """

        def predicate(m):
            print(self.dregex.search(m.content))
            return self.dregex.search(m.content)

        await self.do_removal(ctx, search, predicate)

    @purge.command(aliases=["link", "url", "links"], brief="Purge messages with URLs.")
    async def urls(self, ctx, search=100):
        """
        Usage: -purge urls [amount]
        Aliases:
            -purge link
            -purge links
            -purge url
        Output:
            Deletes all messages that
            contain URLs in them.
        Examples:
            -purge urls
            -prune urls 125
        """

        def predicate(m):
            print(self.uregex.search(m.content))
            return self.uregex.search(m.content)

        await self.do_removal(ctx, search, predicate)

    @purge.command(brief="Purge messages with attachments.", aliases=["attachments"])
    async def files(self, ctx, search=100):
        """
        Usage: -purge files [amount]
        Aliases:
            -purge attachments
        Output:
            Deletes all messages that
            contain attachments in them.
        Examples:
            -purge attachments
            -prune files 125
        """
        await self.do_removal(ctx, search, lambda e: len(e.attachments))

    @purge.command(
        brief="Purge messages with mentions.", aliases=["pings", "ping", "mention"]
    )
    async def mentions(self, ctx, search=100):
        """
        Usage: -purge mentions [amount]
        Aliases:
            -purge pings
            -purge ping
            -purge mention
        Output:
            Deletes all messages that
            contain user mentions in them.
        Examples:
            -purge mentions
            -prune pings 125
        """
        await self.do_removal(
            ctx, search, lambda e: len(e.mentions) or len(e.role_mentions)
        )

    @purge.command(
        brief="Purge messages with images.", aliases=["pictures", "pics", "image"]
    )
    async def images(self, ctx, search=100):
        """
        Usage: -purge mentions [amount]
        Aliases:
            -purge pics
            -purge pictures
            -purge image
        Output:
            Deletes all messages that
            contain images in them.
        Examples:
            -purge pictures
            -prune images 125
        """
        await self.do_removal(
            ctx, search, lambda e: len(e.embeds) or len(e.attachments)
        )

    @purge.command(name="all", brief="Purge all messages.", aliases=["messages"])
    async def _remove_all(self, ctx, search=100):
        """
        Usage: -purge all [amount]
        Aliases:
            -purge
            -purge messages
        Output:
            Deletes all messages.
        Examples:
            -purge
            -prune 2000
            -prune messages 125
        """
        await self.do_removal(ctx, search, lambda e: True)

    @purge.command(brief="Purge messages sent by a user.", aliases=["member"])
    async def user(self, ctx, member: converters.DiscordMember = None, search=100):
        """
        Usage: -purge user <user> [amount]
        Aliases:
            -purge member
        Output:
            Deletes all messages that
            were sent by the passed user.
        Examples:
            -purge user
            -prune member 125
        """
        if member is None:
            return await ctx.usage(f"<user> [amount]")
        await self.do_removal(ctx, search, lambda e: e.author == member)

    @purge.command(brief="Customize purging messages.", aliases=["has"])
    async def contains(self, ctx, *, substr: str):
        """
        Usage: -purge contains <string>
        Alias:
            -purge has
        Output:
            Deletes all messages that
            contain the passed string.
        Examples:
            -purge contains hello
            -prune has no
        Notes:
            The string must a minimum
            of 2 characters in length.
        """
        if len(substr) < 2:
            await ctx.fail(
                content="The substring length must be at least 3 characters.",
            )
        else:
            await self.do_removal(ctx, 100, lambda e: substr in e.content)

    @purge.command(
        name="bots", brief="Purge messages sent by bots.", aliases=["robots"]
    )
    async def _bots(self, ctx, search=100, prefix=None):
        """
        Usage: -purge bots [amount] [prefix]
        Alias:
            -purge robots
        Output:
            Deletes all messages
            that were sent by bots.
        Examples:
            -purge robots 200
            -prune bote 150 >
        Notes:
            Specify an optional prefix to
            remove all messages that start
            with that prefix. This is useful
            for removing command invocations
        """

        if not str(search).isdigit():
            prefix = search
            search = 100
        if prefix:

            def predicate(m):
                return (m.webhook_id is None and m.author.bot) or m.content.startswith(
                    prefix
                )

        else:

            def predicate(m):
                return m.webhook_id is None and m.author.bot

        await self.do_removal(ctx, search, predicate)

    @purge.command(
        name="webhooks", aliases=["webhook"], brief="Purge messages sent by wehooks."
    )
    async def webhooks(self, ctx, search=100):
        """
        Usage: -purge webhooks [amount]
        Alias:
            -purge webhook
        Output:
            Deletes all messages that
            were sent by webhooks.
        Examples:
            -purge webhook
            -prune webhooks 125
        """

        def predicate(m):
            return m.webhook_id

        await self.do_removal(ctx, search, predicate)

    @purge.command(
        name="humans",
        aliases=["users", "members", "people"],
        brief="Purge messages sent by humans.",
    )
    async def _users(self, ctx, search=100):
        """
        Usage: -purge humans [amount]
        Aliases:
            -purge users
            -purge members
            -purge people
        Output:
            Deletes all messages
            sent by user accounts.
            Bot and webhook messages
            will not be deleted.
        Examples:
            -purge humans
            -prune people 125
        """

        def predicate(m):
            return m.author.bot is False

        await self.do_removal(ctx, search, predicate)

    @purge.command(
        name="emojis",
        aliases=["emotes", "emote", "emoji"],
        brief="Purge messages with emojis.",
    )
    async def _emojis(self, ctx, search=100):
        """
        Usage: -purge emojis [amount]
        Aliases:
            -purge emotes
            -purge emote
            -purge emoji
        Output:
            Deletes all messages that
            contain custom discord emojis.
        Examples:
            -purge emojis
            -prune emotes 125
        """
        custom_emoji = re.compile(r"<a?:(.*?):(\d{17,21})>|[\u263a-\U0001f645]")

        def predicate(m):
            return custom_emoji.search(m.content)

        await self.do_removal(ctx, search, predicate)

    @purge.command(name="reactions", brief="Purge reactions from messages.")
    async def _reactions(self, ctx, search=100):
        """
        Usage: -purge emojis [amount]
        Output:
            Demoves all reactions from
            messages that were reacted on.
        Examples:
            -purge reactions
            -prune reactions 125
        Notes:
            The messages are not deleted.
            Only the reactions are removed.
        """
        if search > 2000:
            return await ctx.send_or_reply(
                content=f"Too many messages to search for ({search}/2000)",
            )

        total_reactions = 0
        async for message in ctx.history(limit=search, before=ctx.message):
            if len(message.reactions):
                total_reactions += sum(r.count for r in message.reactions)
                await message.clear_reactions()
        await ctx.send_or_reply(
            f'{self.bot.emote_dict["trash"]} Successfully removed {total_reactions} reactions.',
            delete_after=7,
        )

    @purge.command(
        name="until", aliases=["after"], brief="Purge messages after a message."
    )
    async def _until(self, ctx, message_id: int):
        """
        Usage: -purge until <message id>
        Alias: -purge after
        Output:
            Purges all messages until
            the given message_id.
            Given ID is not deleted
        Examples:
            -purge until 810377376269
            -prune after 810377376269
        """
        channel = ctx.message.channel
        try:
            message = await channel.fetch_message(message_id)
        except commands.errors.NotFound:
            await ctx.send_or_reply(
                content="Message could not be found in this channel",
            )
            return

        await ctx.message.delete()
        await channel.purge(after=message)
        return True

    async def _basic_cleanup_strategy(self, ctx, search):
        count = 0
        async for msg in ctx.history(limit=search, before=ctx.message):
            if msg.author == ctx.me and not (msg.mentions or msg.role_mentions):
                await msg.delete()
                count += 1
        return {"Bot": count}

    async def _complex_cleanup_strategy(self, ctx, search):
        prefixes = tuple(self.bot.get_guild_prefixes(ctx.guild))  # thanks startswith

        def check(m):
            return m.author == ctx.me or m.content.startswith(prefixes)

        deleted = await ctx.channel.purge(limit=search, check=check, before=ctx.message)
        return Counter(m.author.display_name for m in deleted)

    async def _regular_user_cleanup_strategy(self, ctx, search):
        prefixes = tuple(self.bot.get_guild_prefixes(ctx.guild))

        def check(m):
            return (m.author == ctx.me or m.content.startswith(prefixes)) and not (
                m.mentions or m.role_mentions
            )

        deleted = await ctx.channel.purge(limit=search, check=check, before=ctx.message)
        return Counter(m.author.display_name for m in deleted)

    @decorators.command(
        brief="Clean up bot command usage.",
        aliases=["clean"],
        updated="2021-05-05 16:00:23.974656",
    )
    @commands.guild_only()
    async def cleanup(self, ctx, search=100):
        """
        Usage: -cleanup [search]
        Alias: -clean
        Output: Cleans up the bot's messages from the channel.
        Notes:
            If a search number is specified, it searches that many messages to delete.
            If the bot has Manage Messages permissions then it will try to delete
            messages that look like they invoked the bot as well.
            After the cleanup is completed, the bot will send you a message with
            which people got their messages deleted and their count. This is useful
            to see which users are spammers. Regular users can delete up to 25 while
            moderators can delete up to 2000 messages
        """
        strategy = self._basic_cleanup_strategy
        is_mod = ctx.channel.permissions_for(ctx.author).manage_messages
        if ctx.channel.permissions_for(ctx.me).manage_messages:
            if is_mod:
                strategy = self._complex_cleanup_strategy
            else:
                strategy = self._regular_user_cleanup_strategy

        if is_mod:
            search = min(max(2, search), 2000)
        else:
            search = min(max(2, search), 25)

        spammers = await strategy(ctx, search)
        deleted = sum(spammers.values())
        messages = [
            f"**{self.bot.emote_dict['trash']} Deleted {deleted} message{'' if deleted == 1 else 's'}\n**"
        ]
        if deleted:
            spammers = sorted(spammers.items(), key=lambda t: t[1], reverse=True)
            messages.extend(f"`{author}`: {count}" for author, count in spammers)
        desc = "\n".join(messages)
        em = discord.Embed()
        em.color = self.bot.constants.embed
        em.description = desc

        await ctx.send_or_reply(embed=em, delete_after=10)


    @decorators.command(brief="Set the slowmode for a channel")
    @commands.guild_only()
    @checks.bot_has_perms(manage_channels=True)
    @checks.has_perms(manage_channels=True)
    async def slowmode(self, ctx, channel=None, time: float = None):
        """
        Usage: {0}slowmode [channel] [seconds]
        Permission: Manage Channels
        Output:
            Sets the channel's slowmode to your input value.
        Notes:
            If no slowmode is passed, will reset the slowmode.
        """
        if channel is None:
            channel_obj = ctx.channel
            time = 0.0
        else:
            try:
                channel_obj = await commands.TextChannelConverter().convert(
                    ctx, channel
                )
            except commands.ChannelNotFound:
                channel_obj = ctx.channel
                if channel.isdigit():
                    time = float(channel)
                else:
                    time = 0.0
        try:
            await channel_obj.edit(slowmode_delay=time)
        except discord.HTTPException as e:
            await ctx.send_or_reply(
                content=f'{self.bot.emote_dict["failed"]} Failed to set slowmode because of an error\n{e}',
            )
        else:
            await ctx.send_or_reply(
                content=f'{self.bot.emote_dict["success"]} Slowmode for {channel_obj.mention} set to `{time}s`',
            )

    @decorators.command(aliases=["lockdown", "lockchannel"], brief="Lock a channel")
    @commands.guild_only()
    @checks.bot_has_perms(manage_channels=True, manage_roles=True)
    @checks.has_perms(administrator=True)
    async def lock(self, ctx, channel=None, minutes_: int = None):
        """
        Usage: -lock [channel] [minutes]
        Aliases: -lockdown, -lockchannel
        Permission: Administrator
        Output:
            Locked channel for the specified time. Infinite if not specified
        Notes:
            Max timed lock is 2 hours
        """
        if channel is None:
            channel_obj = ctx.channel
        else:
            try:
                channel_obj = await commands.TextChannelConverter().convert(
                    ctx, channel
                )
            except commands.ChannelNotFound:
                channel_obj = ctx.channel
                if channel.isdigit():
                    minutes_ = int(channel)
                else:
                    minutes_ = None
        try:
            channel = channel_obj
            overwrites_everyone = channel.overwrites_for(ctx.guild.default_role)
            my_overwrites = channel.overwrites_for(ctx.guild.me)
            everyone_overwrite_current = overwrites_everyone.send_messages
            msg = await ctx.send_or_reply(
                content=f"Locking channel {channel.mention}...",
            )
            try:
                await self.bot.cxn.execute(
                    "INSERT INTO lockedchannels VALUES ($1, $2, $3, $4)",
                    channel.id,
                    ctx.guild.id,
                    ctx.author.id,
                    str(everyone_overwrite_current),
                )
            except asyncpg.UniqueViolationError:
                return await msg.edit(
                    content=f"{self.bot.emote_dict['failed']} Channel {channel.mention} is already locked."
                )

            my_overwrites.send_messages = True
            overwrites_everyone.send_messages = False
            await ctx.message.channel.set_permissions(
                ctx.guild.default_role,
                overwrite=overwrites_everyone,
                reason=(
                    utils.responsible(ctx.author, "Channel locked by command execution")
                ),
            )
            if minutes_:
                if minutes_ > 120:
                    raise commands.BadArgument("Max timed lock is 120 minutes.")
                elif minutes_ < 0:
                    raise commands.BadArgument("Minutes must be greater than 0.")
                minutes = minutes_

                await msg.edit(
                    content=f"{self.bot.emote_dict['lock']} Channel {channel.mention} locked for `{minutes}` minute{'' if minutes == 1 else 's'}. ID: `{channel.id}`"
                )
                await asyncio.sleep(minutes * 60)
                await self.unlock(ctx, channel=channel, surpress=True)
            else:
                await msg.edit(
                    content=f"{self.bot.emote_dict['lock']} Channel {channel.mention} locked. ID: `{channel.id}`"
                )
        except discord.Forbidden:
            await msg.edit(
                content=f"{self.bot.emote_dict['failed']} I have insufficient permission to lock channels."
            )

    @decorators.command(brief="Unlock a channel.", aliases=["unlockchannel"])
    @commands.guild_only()
    @checks.bot_has_perms(manage_channels=True)
    @checks.has_perms(administrator=True)
    async def unlock(self, ctx, channel: discord.TextChannel = None, surpress=False):
        """
        Usage: -unlock [channel]
        Alias: -unlockchannel
        Permission: Administrator
        Output: Unlocks a previously locked channel
        """
        if channel is None:
            channel = ctx.channel
        try:
            locked = (
                await self.bot.cxn.fetchrow(
                    "SELECT channel_id FROM lockedchannels WHERE channel_id = $1",
                    channel.id,
                )
                or (None)
            )
            if locked is None:
                if surpress is True:
                    return
                else:
                    return await ctx.send_or_reply(
                        f"{self.bot.emote_dict['lock']} Channel {channel.mention} is already unlocked. ID: `{channel.id}`"
                    )

            msg = await ctx.send_or_reply(
                content=f"Unlocking channel {channel.mention}...",
            )
            old_overwrites = await self.bot.cxn.fetchrow(
                "SELECT everyone_perms FROM lockedchannels WHERE channel_id = $1",
                channel.id,
            )
            everyone_perms = old_overwrites[0]

            if everyone_perms == "None":
                everyone_perms = None
            elif everyone_perms == "False":
                everyone_perms = False
            elif everyone_perms == "True":
                everyone_perms = True

            overwrites_everyone = ctx.channel.overwrites_for(ctx.guild.default_role)
            overwrites_everyone.send_messages = everyone_perms
            await ctx.message.channel.set_permissions(
                ctx.guild.default_role,
                overwrite=overwrites_everyone,
                reason=(
                    utils.responsible(
                        ctx.author, "Channel unlocked by command execution"
                    )
                ),
            )
            await self.bot.cxn.execute(
                "DELETE FROM lockedchannels WHERE channel_id = $1", channel.id
            )
            await msg.edit(
                content=f"{self.bot.emote_dict['unlock']} Channel {channel.mention} unlocked. ID: `{channel.id}`"
            )
        except discord.errors.Forbidden:
            await msg.edit(
                content=f"{self.bot.emote_dict['failed']} I have insufficient permission to unlock channels."
            )

    @commands.command(
        aliases=['tban'],
        brief="Temporarily ban users.",
        implemented="2021-04-27 03:59:16.293041",
        updated="2021-05-13 00:04:42.463263",
        examples="""
                {0}tempban @Hecate 2 days for advertising
                {0}tban 708584008065351681 Hecate 2 hours for spamming
                """
    )
    @commands.guild_only()
    @checks.has_perms(ban_members=True)
    async def tempban(
        self,
        ctx,
        users: commands.Greedy[converters.DiscordMember],
        *, 
        duration: humantime.UserFriendlyTime(commands.clean_content, default='\u2026') = None
    ):
        """
        Usage: {0}tempban <users> [duration] [reason]
        Alias: {0}tban
        Output:
            Temporarily bans a member for the specified duration.
            The duration can be a a short time form, e.g. 30d or a more human
            duration like "until thursday at 3PM".
        """
        task = self.bot.get_cog("Tasks")
        if not task:
            raise commands.BadArgument(f"This feature is unavailable.")
        if not len(users):
            return await ctx.usage()
        if not duration:
            raise commands.BadArgument(f"You must specify a duration.")

        reason = duration.arg if duration and duration.arg != "…" else None
        endtime = duration.dt

        banned = []
        failed = []
        for user in users:
            res = await checks.check_priv(ctx, user)
            if res:
                failed.append((str(user), res))
                continue
            try:
                if reason:
                    embed = discord.Embed(color=self.bot.constants.embed)
                    timefmt = humantime.human_timedelta(endtime, source=ctx.message.created_at)
                    embed.title = f"{self.bot.emote_dict['ban']} Tempban Notice"
                    embed.description = f"**Server: `{ctx.guild.name} ({ctx.guild.id})`**\n"
                    embed.description += f"**Moderator: `{ctx.author} ({ctx.author.id})`**\n"
                    embed.description += f"**Duration: `{timefmt}`**\n"
                    embed.description += f"**Reason: `{reason}`**"
                    try:
                        await user.send(embed=embed)
                    except (AttributeError, discord.HTTPException):
                        pass

                await ctx.guild.ban(user, reason=reason)
                timer = await task.create_timer(
                    endtime,
                    "tempban",
                    ctx.guild.id,
                    ctx.author.id,
                    user.id,
                    connection=self.bot.cxn,
                    created=ctx.message.created_at,
                )
                banned.append(str(user))
            except Exception as e:
                failed.append((str(user), e))
        if failed:
            await helpers.error_info(ctx, failed)
        if banned:
            self.bot.dispatch("mod_action", ctx, targets=banned)
            await ctx.success(
                f"Tempbanned `{', '.join(banned)}` for {humantime.human_timedelta(duration.dt, source=timer.created_at)}."
            )

    @commands.Cog.listener()
    @decorators.wait_until_ready()
    async def on_tempban_timer_complete(self, timer):
        guild_id, mod_id, member_id = timer.args

        guild = self.bot.get_guild(guild_id)
        if guild is None:
            # RIP
            return

        moderator = guild.get_member(mod_id)
        if moderator is None:
            try:
                moderator = await self.bot.fetch_user(mod_id)
            except:
                # request failed somehow
                moderator = f"Mod ID {mod_id}"
            else:
                moderator = f"{moderator} (ID: {mod_id})"
        else:
            moderator = f"{moderator} (ID: {mod_id})"

        reason = (
            f"Automatic unban from timer made on {timer.created_at} by {moderator}."
        )
        await guild.unban(discord.Object(id=member_id), reason=reason)


    ###################
    ## Mute Commands ##
    ###################

    @decorators.command(
        aliases=["tempmute"],
        brief="Mute users for a duration.",
        implemented="2021-04-02 00:16:54.164723",
        updated="2021-05-09 15:44:25.714321",
        examples="""
                {0}mute @Hecate
                {0}mute Hecate#3523 @John 2 minutes
                {0}mute 708584008065351681 John 3 days for advertising
                {0}mute John --duration 3 hours
                {0}mute Hecate for spamming
                {0}mute Hecate John for 2 days
                """,
    )
    @commands.guild_only()
    @checks.bot_has_perms(manage_roles=True)
    @checks.has_perms(manage_roles=True)
    async def mute(
        self, ctx, users: commands.Greedy[converters.DiscordMember], *, duration: humantime.UserFriendlyTime(commands.clean_content, default='\u2026')=None
    ):
        """
        Usage: {0}mute <users>... [duration] [reason]
        Alias: {0}tempmute
        Output:
            Mutes multiple users.
            This command will attempt
            to remove all the roles from
            the passed users, and reaasign
            them on unmute. If no duration
            is specified, mute will be indefinite.
        Notes:
            Duration and reason are optional.
            Running the command with a reason
            will dm the user while running the
            command without a reason will not dm.
            Run the command: {0}examples mute
            for specific usage examples.
        """
        task = self.bot.get_cog("Tasks")
        if not task:
            raise commands.BadArgument(f"This feature is currently unavailable.")
        if not len(users):
            return await ctx.usage()

        await ctx.trigger_typing()
        query = """
                SELECT (muterole)
                FROM servers
                WHERE server_id = $1;
                """
        muterole = await self.bot.cxn.fetchval(query, ctx.guild.id)
        muterole = ctx.guild.get_role(muterole)
        if not muterole:
            raise commands.BadArgument(
                f"Run the `{ctx.prefix}muterole <role>` command to set up a mute role."
            )

        reason = duration.arg if duration and duration.arg != "…" else None
        endtime = duration.dt if duration else None
        if reason:
            dm = True
        else:
            dm = False

        failed = []
        muted = []
        for user in users:
            if user.bot:  # This is because bots sometimes have a role that cannot be removed
                failed.append((str(user), "I cannot mute bots."))
                continue  # I mean we could.. but why would someone want to mute a bot.
            if muterole in user.roles:
                failed.append((str(user), "User is already muted."))
                continue
            res = await checks.check_priv(ctx, user)
            if res:
                failed.append((str(user), res))
                continue
            query = """
                    select (id)
                    from tasks
                    where extra->'kwargs'->>'user_id' = $1;
                    """
            s = await self.bot.cxn.fetchval(query, str(user.id))
            if s:
                failed.append((str(user), "User is already muted."))
                continue
            try:
                timer = await task.create_timer(
                    endtime,
                    "mute",
                    ctx.guild.id,
                    ctx.author.id,
                    user.id,
                    dm=dm,
                    user_id=user.id,
                    roles=[x.id for x in user.roles],
                    connection=self.bot.cxn,
                    created=ctx.message.created_at,
                )
                await user.edit(roles=[muterole], reason=reason)
                muted.append(str(user))
                if reason:
                    embed = discord.Embed(color=self.bot.constants.embed)
                    embed.title = f"{self.bot.emote_dict['audioremove']} Mute Notice"
                    embed.description = (
                        f"**Server: `{ctx.guild.name} ({ctx.guild.id})`**\n"
                    )
                    embed.description += (
                        f"**Moderator: `{ctx.author} ({ctx.author.id})`**\n"
                    )
                    if endtime:
                        timefmt = humantime.human_timedelta(
                            endtime, source=timer.created_at
                        )
                        embed.description += f"**Duration: `{timefmt}`**\n"
                    embed.description += f"**Reason: `{reason}`**"
                try:
                    await user.send(embed=embed)
                except Exception:  # We tried
                    pass
            except Exception as e:
                failed.append((str(user), e))

        if failed:
            await helpers.error_info(ctx, failed)
        if muted:
            self.bot.dispatch("mod_action", ctx, targets=muted)
            if endtime:
                timefmt = humantime.human_timedelta(endtime, source=timer.created_at)
                await ctx.success(f"Muted `{', '.join(muted)}` for **{timefmt}.**")
            else:
                await ctx.success(f"Muted `{', '.join(muted)}`")

    @decorators.command(
        brief="Unmute muted users.",
        implemented="2021-05-09 19:44:24.756715",
        updated="2021-05-09 19:44:24.756715",
        examples="""
                {0}unmute Hecate @John 708584008065351681 because I forgave them
                {0}unmute Hecate#3523
                """,
    )
    @commands.guild_only()
    @checks.bot_has_perms(manage_roles=True)
    @checks.has_perms(manage_roles=True)
    async def unmute(
        self,
        ctx,
        users: commands.Greedy[converters.DiscordMember],
        *,
        reason: typing.Optional[str] = "No reason",
    ):
        """
        Usage: {0}unmute <users>... [reason]
        Output:
            Unmutes previously users previously
            muted by the {0}mute command. The bot
            will restore all the users' old roles
            that they had before they were muted.
        """
        if not len(users):
            return await ctx.usage(ctx.command.signature)
        failed = []
        unmuted = []
        for user in users:
            res = await checks.check_priv(ctx, user)
            if res:
                failed.append((str(user), res))
                continue

            query = """
                    select (id, extra)
                    from tasks
                    where extra->'kwargs'->>'user_id' = $1;
                    """
            s = await self.bot.cxn.fetchval(query, str(user.id))
            if not s:
                return await ctx.fail(f"User `{user}` is not muted.")
            await ctx.trigger_typing()
            task_id = s[0]
            args_and_kwargs = json.loads(s[1])
            dm = args_and_kwargs["kwargs"]["dm"]
            roles = args_and_kwargs["kwargs"]["roles"]
            try:
                await user.edit(
                    roles=[ctx.guild.get_role(x) for x in roles],
                    reason=await converters.ActionReason().convert(ctx, reason),
                )
                query = """
                        DELETE FROM tasks
                        WHERE id = $1
                        """
                await self.bot.cxn.execute(query, task_id)
                unmuted.append(str(user))
            except Exception as e:
                failed.append((str(user), e))
                continue
            if dm:
                embed = discord.Embed(color=self.bot.constants.embed)
                embed.title = f"{self.bot.emote_dict['audioadd']} Unmute Notice"
                embed.description = f"**Server: `{ctx.guild.name} ({ctx.guild.id})`**\n"
                embed.description += f"**Moderator: `{ctx.author} ({ctx.author.id})`**"
                try:
                    await user.send(embed=embed)
                except Exception:
                    pass
        if failed:
            await helpers.error_info(ctx, failed)
        if unmuted:
            await ctx.success(f"Unmuted `{' '.join(unmuted)}`")

    @commands.Cog.listener()
    @decorators.wait_until_ready()
    async def on_mute_timer_complete(self, timer):
        guild_id, mod_id, member_id = timer.args

        guild = self.bot.get_guild(guild_id)
        if guild is None:
            # RIP
            return

        moderator = guild.get_member(mod_id)
        if moderator is None:
            try:
                moderator = await self.bot.fetch_user(mod_id)
            except:
                # request failed somehow
                moderator = f"Mod ID {mod_id}"
            else:
                moderator = f"{moderator} ({mod_id})"
        else:
            moderator = f"{moderator} ({mod_id})"

        reason = (
            f"Automatic unmute from timer made on {timer.created_at} by {moderator}."
        )
        member = guild.get_member(member_id)
        if not member:
            return  # They left...
        roles = timer.kwargs["roles"]
        dm = timer.kwargs["dm"]
        try:
            await member.edit(roles=[guild.get_role(x) for x in roles], reason=reason)
        except Exception:  # They probably removed roles lmao.
            return
        if dm:
            embed = discord.Embed(color=self.bot.constants.embed)
            embed.title = f"{self.bot.emote_dict['audioadd']} Unmute Notice"
            embed.description = f"**Server: `{guild.name} ({guild.id})`**\n"
            embed.description += f"**Moderator: `{moderator}`**"
            try:
                await member.send(embed=embed)
            except Exception:
                pass
