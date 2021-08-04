import io
import re
import copy
import shlex
import typing
import discord

from datetime import timedelta
from discord.ext import commands
from collections import defaultdict
from unidecode import unidecode

from utilities import utils
from utilities import checks
from utilities import helpers
from utilities import converters
from utilities import decorators
from utilities import pagination


def setup(bot):
    bot.add_cog(Admin(bot))


class Admin(commands.Cog):
    """
    Module for server administration.
    """

    def __init__(self, bot):
        self.bot = bot
        self.mass = defaultdict(str)

    def start_working(self, guild, action):
        """
        Checks if a mass command is
        in progress in a given server
        and raises an error if it is.
        """
        if guild.id in self.mass.keys():
            prev_action = self.mass.get(guild.id)
            raise commands.BadArgument(
                f"Command `{prev_action}` is already in progress. Please wait until it has been completed."
            )
        self.mass[guild.id] = action

    def stop_working(self, guild):
        self.mass.pop(guild.id)

    @decorators.command(brief="Setup server muting system.", aliases=["setmuterole"])
    @checks.guild_only()
    @checks.bot_has_perms(manage_roles=True)
    @checks.has_perms(manage_guild=True)
    @checks.cooldown()
    async def muterole(self, ctx, role: converters.DiscordRole = None):
        """
        Usage:      {0}muterole <role>
        Alias:      {0}setmuterole
        Example:    {0}muterole @Muted
        Permission: Manage Server
        Output:
            This command will set a role of your choice as the
            "Muted" role.
        Notes:
            When this command is run, the permissions for every
            channel will have the Send Messages permission set
            to false for the muted role.
        """
        msg = await ctx.load(
            "Creating mute system. This process may take several minutes..."
        )
        if role is None:
            role = await ctx.guild.create_role(
                name="Muted", reason="For the server muting system"
            )
        try:
            if ctx.guild.me.top_role.position < role.position:
                await msg.edit(
                    content=f"{self.bot.emote_dict['failed']} The muted role is above my highest role."
                )
                return
            if ctx.author.top_role.position < role.position:
                if ctx.author.id != ctx.guild.owner.id:
                    await msg.edit(
                        content=f"{self.bot.emote_dict['failed']} The muted role is above your highest role."
                    )
            query = """UPDATE servers SET muterole = $1 WHERE server_id = $2"""
            await self.bot.cxn.execute(query, role.id, ctx.guild.id)
        except Exception as e:
            return await msg.edit(content=e)
        channels = []
        for channel in ctx.guild.text_channels:
            try:
                await channel.set_permissions(role, send_messages=False)
            except discord.Forbidden:
                channels.append(channel.name)
                continue
        if channels:
            return await msg.edit(
                content=f"{self.bot.emote_dict['failed']} I do not have permission to edit channel{'' if len(channels) == 1 else 's'}:`{', '.join(channels)}`"
            )

        await msg.edit(
            content=f"{self.bot.emote_dict['success']} Saved `{role.name}` as this server's mute role."
        )

    @decorators.command(
        aliases=["die"],
        brief="Have the bot leave the server.",
        implemented="2021-04-28 20:21:42.190256",
        updated="2021-05-05 19:43:51.209242",
    )
    @checks.guild_only()
    @checks.has_perms(manage_guild=True)
    @checks.cooldown(2, 30, bucket=commands.BucketType.guild)
    async def kill(self, ctx):
        """
        Usage: {0}kill
        Aliases: {0}die
        Output:
            Clears all stored server data
            and kicks the bot from the server.
        Notes:
            You will receive confirmation, upon executing this
            command, all emoji stats, messages, last seen data
            roles, nicknames, and usernames will be deleted.
        """
        c = await ctx.confirm(
            f"{self.bot.emote_dict['delete']} This action will remove me from this server and clear all my collected data."
        )
        if c:
            await ctx.guild.leave()
            return

    @decorators.command(brief="Dehoist all server users.")
    @checks.guild_only()
    @checks.bot_has_perms(manage_nicknames=True)
    @checks.has_perms(manage_guild=True)
    @checks.cooldown(2, 30, bucket=commands.BucketType.guild)
    async def massdehoist(self, ctx, symbol: str = None):
        """
        Usage: {0}massdehoist [symbol]
        Permission: Manage Server
        Output:
            Re-nicknames all users who hoist
            their names with characters like "!"
        Notes:
            Pass an optional symbol to only nickname
            users who's names begin with that symbol.
            By default, all hoisting symbols will be
            removed. If a user's name is made up entirely
            of hoisting characters, their nickname will be
            changed to "Dehoisted." The bot will inform you
            of the number of users it was able to edit
            and the number of users that have superior
            permissions and are immune to nickname editing.
        """
        if symbol is None:
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

        else:
            characters = [symbol]

        c = await ctx.confirm(
            "This command will attempt to nickname all users with hoisting symbols in their names."
        )
        if c:
            hoisted = []
            for user in ctx.guild.members:
                if user.display_name.startswith(tuple(characters)):
                    hoisted.append(user)

            if len(hoisted) == 0:
                await ctx.fail(f"No users to dehoist.")
                return
            message = await ctx.load(
                f"Dehoisting {len(hoisted)} user{'' if len(hoisted) == 1 else 's'}..."
            )

            self.start_working(ctx.guild, "massdehoist")

            edited = []
            failed = []
            for user in hoisted:
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
                    edited.append(str(user))
                except Exception:
                    failed.append(str(user))

            self.stop_working(ctx.guild)

            msg = ""
            if edited:
                msg += f"{self.bot.emote_dict['success']} Dehoisted {len(edited)} user{'' if len(edited) == 1 else 's'}."
            if failed:
                msg += f"\n{self.bot.emote_dict['failed']} Failed to dehoist {len(failed)} user{'' if len(failed) == 1 else 's'}."
            await message.edit(content=msg)

    @decorators.command(brief="Mass nickname users with odd names.")
    @checks.guild_only()
    @checks.bot_has_perms(manage_nicknames=True)
    @checks.has_perms(manage_guild=True)
    @checks.cooldown(2, 30, bucket=commands.BucketType.guild)
    async def massascify(self, ctx):
        """
        Usage: {0}massascify
        Permission: Manage Server
        Output:
            The bot will attempt to edit the
            nicknames of all users with
            special characters in their names.
        Notes:
            May take several minutes on larger servers
        """

        c = await ctx.confirm(
            "This command will attempt to nickname all users with special symbols in their names."
        )
        if c:
            odd_names = []
            for user in ctx.guild.members:
                current_name = copy.copy(user.display_name)
                ascified = unidecode(user.display_name)
                if current_name != ascified:
                    odd_names.append(user)

            if len(odd_names) == 0:
                await ctx.send_or_reply(
                    content=f"{self.bot.emote_dict['exclamation']} No users to ascify.",
                )
                return

            message = await ctx.load(
                f"Ascifying {len(odd_names)} user{'' if len(odd_names) == 1 else 's'}..."
            )

            self.start_working(ctx.guild, "massascify")

            edited = []
            failed = []
            for user in odd_names:
                try:
                    ascified = unidecode(user.display_name)
                    await user.edit(
                        nick=ascified, reason="Nickname changed by massascify command."
                    )
                    edited.append(str(user))
                except Exception:
                    failed.append(str(user))

            self.stop_working(ctx.guild)

            msg = ""
            if edited:
                msg += f"{self.bot.emote_dict['success']} Ascified {len(edited)} user{'' if len(edited) == 1 else 's'}."
            if failed:
                msg += f"\n{self.bot.emote_dict['failed']} Failed to ascify {len(failed)} user{'' if len(failed) == 1 else 's'}."
            await message.edit(content=msg)

    @decorators.command(
        aliases=["multiban"],
        brief="Massban users matching a search.",
        implemented="2021-05-02 04:12:14.126319",
        updated="2021-06-13 01:41:29.818783",
    )
    @checks.guild_only()
    @checks.bot_has_perms(ban_members=True)
    @checks.has_perms(manage_guild=True, ban_members=True)
    @checks.cooldown(2, 30, bucket=commands.BucketType.guild)
    async def massban(self, ctx, *, args):
        """
        Usage: {0}massban <arguments>
        Aliases: {0}multiban
        Permissions: Manage Server, Ban Members
        Output:
            Massbans users matching searches
        Notes:
            Use {0}massban --help
            to show all valid arguments.
        """

        help_docstr = ""
        help_docstr += "**Valid Massban Flags:**"
        help_docstr += "```yaml\n"
        help_docstr += "Flags: [Every flag is optional except --reason]\n"
        help_docstr += "\t--help|-h: Shows this message\n"
        help_docstr += "\t--channel|-c: Channel to search for message history.\n"
        help_docstr += "\t--reason|-r: The reason for the ban.\n"
        help_docstr += "\t--regex: Regex that usernames must match.\n"
        help_docstr += (
            "\t--created: Matches users that registered after X minutes ago.\n"
        )
        help_docstr += "\t--joined: Matches users that joined after X minutes ago.\n"
        help_docstr += (
            "\t--joined-before: Matches users who joined before the user ID given.\n"
        )
        help_docstr += (
            "\t--joined-after: Matches users who joined after the user ID given.\n"
        )
        help_docstr += (
            "\t--no-avatar: Matches users who have no avatar. (no arguments)\n"
        )
        help_docstr += "\t--no-roles: Matches users that have no role. (no arguments)\n"
        help_docstr += "\t--has-role: Matches users that have a specific role.\n"
        help_docstr += (
            "\t--show: Show members instead of banning them. (no arguments)\n"
        )
        help_docstr += (
            "\t--warns: Matches users who's warn count is more than a value.\n"
        )
        help_docstr += "\tMessage history filters (Requires --channel):\n"
        help_docstr += "\t\t--contains: A substring to search for in the message.\n"
        help_docstr += (
            "\t\t--starts: A substring to search if the message starts with.\n"
        )
        help_docstr += "\t\t--ends: A substring to search if the message ends with.\n"
        help_docstr += "\t\t--match: A regex to match the message content to.\n"
        help_docstr += (
            "\t\t--search: How many messages to search. Default 100. Max 2000.\n"
        )
        help_docstr += "\t\t--after: Messages must come after this message ID.\n"
        help_docstr += "\t\t--before: Messages must come before this message ID.\n"
        help_docstr += (
            "\t\t--files: Checks if the message has attachments (no arguments).\n"
        )
        help_docstr += (
            "\t\t--embeds: Checks if the message has embeds (no arguments).\n"
        )
        help_docstr += "```"

        parser = converters.Arguments(add_help=False, allow_abbrev=False)
        parser.add_argument("--help", "-h", action="store_true")
        parser.add_argument("--channel", "-c")
        parser.add_argument("--reason", "-r", nargs="+")
        parser.add_argument("--search", type=int, default=100)
        parser.add_argument("--regex")
        parser.add_argument("--no-avatar", action="store_true")
        parser.add_argument("--no-roles", action="store_true")
        parser.add_argument("--has-role", nargs="+")
        parser.add_argument("--warns", "--warn", type=int)
        parser.add_argument("--created", type=int)
        parser.add_argument("--joined", type=int)
        parser.add_argument("--joined-before", type=int)
        parser.add_argument("--joined-after", type=int)
        parser.add_argument("--contains")
        parser.add_argument("--starts")
        parser.add_argument("--ends")
        parser.add_argument("--match")
        parser.add_argument("--show", action="store_true")
        parser.add_argument(
            "--embeds", action="store_const", const=lambda m: len(m.embeds)
        )
        parser.add_argument(
            "--files", action="store_const", const=lambda m: len(m.attachments)
        )
        parser.add_argument("--after", type=int)
        parser.add_argument("--before", type=int)

        try:
            args = parser.parse_args(shlex.split(args))
        except Exception as e:
            return await ctx.fail(str(e).capitalize())

        members = []

        if args.help:
            return await ctx.send_or_reply(help_docstr)

        if args.channel:
            channel = await commands.TextChannelConverter().convert(ctx, args.channel)
            before = args.before and discord.Object(id=args.before)
            after = args.after and discord.Object(id=args.after)
            predicates = []
            if args.contains:
                predicates.append(lambda m: args.contains in m.content)
            if args.starts:
                predicates.append(lambda m: m.content.startswith(args.starts))
            if args.ends:
                predicates.append(lambda m: m.content.endswith(args.ends))
            if args.match:
                try:
                    _match = re.compile(args.match)
                except re.error as e:
                    return await ctx.fail(f"Invalid regex passed to `--match`: {e}")
                else:
                    predicates.append(lambda m, x=_match: x.match(m.content))
            if args.embeds:
                predicates.append(args.embeds)
            if args.files:
                predicates.append(args.files)

            async for message in channel.history(
                limit=min(max(1, args.search), 2000), before=before, after=after
            ):
                if all(p(message) for p in predicates):
                    members.append(message.author)
        else:
            if ctx.guild.chunked:
                members = ctx.guild.members
            else:
                async with ctx.typing():
                    await ctx.guild.chunk(cache=True)
                members = ctx.guild.members

        # member filters
        predicates = [
            lambda m: m.discriminator != "0000",  # No deleted users
        ]

        converter = commands.MemberConverter()

        if args.regex:
            try:
                _regex = re.compile(args.regex)
            except re.error as e:
                return await ctx.fail(f"Invalid regex passed to `--regex`: {e}")
            else:
                predicates.append(lambda m, x=_regex: x.match(m.name))

        if args.no_avatar:
            predicates.append(lambda m: m.avatar.key == m.default_avatar.key)
        if args.no_roles:
            predicates.append(lambda m: len(getattr(m, "roles", [])) <= 1)
        if args.has_role:
            discord_role = " ".join(args.has_role)
            role = await converters.DiscordRole().convert(ctx, str(discord_role))
            predicates.append(lambda m: role in m.roles)

        now = discord.utils.utcnow()
        if args.created:

            def created(member, *, offset=now - timedelta(minutes=args.created)):
                return member.created_at > offset

            predicates.append(created)
        if args.joined:

            def joined(member, *, offset=now - timedelta(minutes=args.joined)):
                if isinstance(member, discord.User):
                    # If the member is a user then they left already
                    return True
                return member.joined_at and member.joined_at > offset

            predicates.append(joined)
        if args.joined_after:
            _joined_after_member = await converter.convert(ctx, str(args.joined_after))

            def joined_after(member, *, _other=_joined_after_member):
                return (
                    member.joined_at
                    and _other.joined_at
                    and member.joined_at > _other.joined_at
                )

            predicates.append(joined_after)
        if args.joined_before:
            _joined_before_member = await converter.convert(
                ctx, str(args.joined_before)
            )

            def joined_before(member, *, _other=_joined_before_member):
                return (
                    member.joined_at
                    and _other.joined_at
                    and member.joined_at < _other.joined_at
                )

            predicates.append(joined_before)

        warned = []
        if args.warns:
            wcs = await self.get_warncount(ctx.guild)
            for user, warns in wcs.items():
                if warns >= args.warns:
                    warned.append(user)

            def warns(member):
                return member.id in warned

            predicates.append(warns)
        members = {m for m in members if all(p(m) for p in predicates)}
        if len(members) == 0:
            return await ctx.fail("No users found matching criteria.")

        if args.show:
            members = sorted(members, key=lambda m: m.joined_at or now)
            fmt = "\n".join(
                f"{m.id}\tJoined: {m.joined_at}\tCreated: {m.created_at}\t{m}"
                for m in members
            )
            content = f"Current Time: {discord.utils.utcnow()}\nTotal users: {len(members)}\n{fmt}"
            file = discord.File(
                io.BytesIO(content.encode("utf-8")), filename="users.txt"
            )
            return await ctx.send_or_reply(file=file)

        if args.reason is None:
            return await ctx.fail("--reason flag is required.")
        else:
            reason = " ".join(args.reason)
            raw_reason = reason
            reason = await converters.ActionReason().convert(ctx, reason)

        confirm = await ctx.confirm(
            f"This action will ban {len(members)} user{'' if len(members) == 1 else 's'}."
        )
        if not confirm:
            return

        self.start_working(ctx.guild, "massban")

        banned = []
        failed = []
        for member in members:
            res = await checks.check_priv(ctx, member)
            if res:
                failed.append((str(member), res))
                continue
            try:
                await ctx.guild.ban(member, reason=reason)
                banned.append((str(member), raw_reason))
            except Exception as e:
                failed.append((str(member), e))
                continue

        self.stop_working(ctx.guild)

        if banned:
            await ctx.success(
                f"Mass banned {len(banned)}/{len(members)} user{'' if len(members) == 1 else 's'}."
            )
            self.bot.dispatch("mod_action", ctx, targets=banned)
        if failed:
            await helpers.error_info(ctx, failed)

    @decorators.command(
        aliases=["multikick"],
        brief="Mass kick users matching a search.",
        implemented="2021-06-13 01:27:18.598560",
        updated="2021-06-13 01:27:18.598560",
    )
    @checks.guild_only()
    @checks.bot_has_perms(kick_members=True)
    @checks.has_perms(manage_guild=True, kick_members=True)
    @checks.cooldown(2, 30, bucket=commands.BucketType.guild)
    async def masskick(self, ctx, *, args):
        """
        Usage: {0}masskick <arguments>
        Aliases: {0}multikick
        Permissions: Manage Server, Kick Members
        Output:
            Mass kicks users matching searches
        Notes:
            Use -masskick --help
            to show all valid arguments.
        """

        help_docstr = ""
        help_docstr += "**Valid Masskick Flags:**"
        help_docstr += "```yaml\n"
        help_docstr += "Flags: [Every flag is optional except --reason]\n"
        help_docstr += "\t--help|-h: Shows this message\n"
        help_docstr += "\t--channel|-c: Channel to search for message history.\n"
        help_docstr += "\t--reason|-r: The reason for the kick.\n"
        help_docstr += "\t--regex: Regex that usernames must match.\n"
        help_docstr += (
            "\t--created: Matches users that registered after X minutes ago.\n"
        )
        help_docstr += "\t--joined: Matches users that joined after X minutes ago.\n"
        help_docstr += (
            "\t--joined-before: Matches users who joined before the user ID given.\n"
        )
        help_docstr += (
            "\t--joined-after: Matches users who joined after the user ID given.\n"
        )
        help_docstr += (
            "\t--no-avatar: Matches users who have no avatar. (no arguments)\n"
        )
        help_docstr += "\t--no-roles: Matches users that have no role. (no arguments)\n"
        help_docstr += "\t--has-role: Matches users that have a specific role.\n"
        help_docstr += (
            "\t--show: Show members instead of kicking them. (no arguments)\n"
        )
        help_docstr += (
            "\t--warns: Matches users who's warn count is more than a value.\n"
        )
        help_docstr += "\tMessage history filters (Requires --channel):\n"
        help_docstr += "\t\t--contains: A substring to search for in the message.\n"
        help_docstr += (
            "\t\t--starts: A substring to search if the message starts with.\n"
        )
        help_docstr += "\t\t--ends: A substring to search if the message ends with.\n"
        help_docstr += "\t\t--match: A regex to match the message content to.\n"
        help_docstr += (
            "\t\t--search: How many messages to search. Default 100. Max 2000.\n"
        )
        help_docstr += "\t\t--after: Messages must come after this message ID.\n"
        help_docstr += "\t\t--before: Messages must come before this message ID.\n"
        help_docstr += (
            "\t\t--files: Checks if the message has attachments (no arguments).\n"
        )
        help_docstr += (
            "\t\t--embeds: Checks if the message has embeds (no arguments).\n"
        )
        help_docstr += "```"

        parser = converters.Arguments(add_help=False, allow_abbrev=False)
        parser.add_argument("--help", "-h", action="store_true")
        parser.add_argument("--channel", "-c")
        parser.add_argument("--reason", "-r", nargs="+")
        parser.add_argument("--search", type=int, default=100)
        parser.add_argument("--regex")
        parser.add_argument("--no-avatar", action="store_true")
        parser.add_argument("--no-roles", action="store_true")
        parser.add_argument("--has-role", nargs="+")
        parser.add_argument("--warns", "--warn", type=int)
        parser.add_argument("--created", type=int)
        parser.add_argument("--joined", type=int)
        parser.add_argument("--joined-before", type=int)
        parser.add_argument("--joined-after", type=int)
        parser.add_argument("--contains")
        parser.add_argument("--starts")
        parser.add_argument("--ends")
        parser.add_argument("--match")
        parser.add_argument("--show", action="store_true")
        parser.add_argument(
            "--embeds", action="store_const", const=lambda m: len(m.embeds)
        )
        parser.add_argument(
            "--files", action="store_const", const=lambda m: len(m.attachments)
        )
        parser.add_argument("--after", type=int)
        parser.add_argument("--before", type=int)

        try:
            args = parser.parse_args(shlex.split(args))
        except Exception as e:
            return await ctx.fail(str(e).capitalize())

        members = []

        if args.help:
            return await ctx.send_or_reply(help_docstr)

        if args.channel:
            channel = await commands.TextChannelConverter().convert(ctx, args.channel)
            before = args.before and discord.Object(id=args.before)
            after = args.after and discord.Object(id=args.after)
            predicates = []
            if args.contains:
                predicates.append(lambda m: args.contains in m.content)
            if args.starts:
                predicates.append(lambda m: m.content.startswith(args.starts))
            if args.ends:
                predicates.append(lambda m: m.content.endswith(args.ends))
            if args.match:
                try:
                    _match = re.compile(args.match)
                except re.error as e:
                    return await ctx.fail(f"Invalid regex passed to `--match`: {e}")
                else:
                    predicates.append(lambda m, x=_match: x.match(m.content))
            if args.embeds:
                predicates.append(args.embeds)
            if args.files:
                predicates.append(args.files)

            async for message in channel.history(
                limit=min(max(1, args.search), 2000), before=before, after=after
            ):
                if all(p(message) for p in predicates):
                    members.append(message.author)
        else:
            if ctx.guild.chunked:
                members = ctx.guild.members
            else:
                async with ctx.typing():
                    await ctx.guild.chunk(cache=True)
                members = ctx.guild.members

        # member filters
        predicates = [
            lambda m: m.discriminator != "0000",  # No deleted users
        ]

        converter = commands.MemberConverter()

        if args.regex:
            try:
                _regex = re.compile(args.regex)
            except re.error as e:
                return await ctx.fail(f"Invalid regex passed to `--regex`: {e}")
            else:
                predicates.append(lambda m, x=_regex: x.match(m.name))

        if args.no_avatar:
            predicates.append(lambda m: m.avatar.key == m.default_avatar.key)
        if args.no_roles:
            predicates.append(lambda m: len(getattr(m, "roles", [])) <= 1)
        if args.has_role:
            discord_role = " ".join(args.has_role)
            role = await converters.DiscordRole().convert(ctx, str(discord_role))
            predicates.append(lambda m: role in m.roles)

        now = discord.utils.utcnow()
        if args.created:

            def created(member, *, offset=now - timedelta(minutes=args.created)):
                return member.created_at > offset

            predicates.append(created)
        if args.joined:

            def joined(member, *, offset=now - timedelta(minutes=args.joined)):
                if isinstance(member, discord.User):
                    # If the member is a user then they left already
                    return True
                return member.joined_at and member.joined_at > offset

            predicates.append(joined)
        if args.joined_after:
            _joined_after_member = await converter.convert(ctx, str(args.joined_after))

            def joined_after(member, *, _other=_joined_after_member):
                return (
                    member.joined_at
                    and _other.joined_at
                    and member.joined_at > _other.joined_at
                )

            predicates.append(joined_after)
        if args.joined_before:
            _joined_before_member = await converter.convert(
                ctx, str(args.joined_before)
            )

            def joined_before(member, *, _other=_joined_before_member):
                return (
                    member.joined_at
                    and _other.joined_at
                    and member.joined_at < _other.joined_at
                )

            predicates.append(joined_before)

        warned = []
        if args.warns:
            wcs = await self.get_warncount(ctx.guild)
            for user, warns in wcs.items():
                if warns >= args.warns:
                    warned.append(user)

            def warns(member):
                return member.id in warned

            predicates.append(warns)
        members = {m for m in members if all(p(m) for p in predicates)}
        if len(members) == 0:
            return await ctx.fail("No users found matching criteria.")

        if args.show:
            members = sorted(members, key=lambda m: m.joined_at or now)
            fmt = "\n".join(
                f"{m.id}\tJoined: {m.joined_at}\tCreated: {m.created_at}\t{m}"
                for m in members
            )
            content = f"Current Time: {discord.utils.utcnow()}\nTotal users: {len(members)}\n{fmt}"
            file = discord.File(
                io.BytesIO(content.encode("utf-8")), filename="users.txt"
            )
            return await ctx.send_or_reply(file=file)

        if args.reason is None:
            return await ctx.fail("--reason flag is required.")
        else:
            reason = " ".join(args.reason)
            raw_reason = reason
            reason = await converters.ActionReason().convert(ctx, reason)

        confirm = await ctx.confirm(
            f"This action will kick {len(members)} user{'' if len(members) == 1 else 's'}."
        )
        if not confirm:
            return

        self.start_working(ctx.guild, "masskick")

        kicked = []
        failed = []
        for member in members:
            res = await checks.check_priv(ctx, member)
            if res:
                failed.append((str(member), res))
                continue
            try:
                await ctx.guild.kick(member, reason=reason)
                kicked.append((str(member), raw_reason))
            except Exception as e:
                failed.append((str(member), e))
                continue

        self.stop_working(ctx.guild)

        if kicked:
            await ctx.success(
                f"Mass kicked {len(kicked)}/{len(members)} user{'' if len(members) == 1 else 's'}."
            )
            self.bot.dispatch("mod_action", ctx, targets=kicked)
        if failed:
            await helpers.error_info(ctx, failed)

    async def get_warncount(self, guild):
        query = """
                SELECT user_id, COUNT(*)
                FROM warns
                WHERE server_id = $1
                GROUP BY user_id;
                """
        records = await self.bot.cxn.fetch(query, guild.id)
        results = {record["user_id"]: record["count"] for record in records}
        return results

    @decorators.group(
        name="massrole",
        aliases=["multirole"],
        brief="Manage mass adding/removing roles.",
        implemented="2021-05-16 15:06:06.479013",
        updated="2021-05-31 05:13:52.253369",
        examples="""
                {0}role add all @Helper
                {0}massrole remove @Helper Mod
                {0}multirole add bots @Bots
                """,
    )
    @checks.guild_only()
    @checks.bot_has_perms(manage_roles=True)
    @checks.has_perms(manage_roles=True)
    @checks.cooldown(2, 30, bucket=commands.BucketType.guild)
    async def _role(self, ctx):
        """
        Usage: {0}role <add/remove> <option> <role>
        Aliases: {0}massrole, {0}multirole
        Permission: Manage Roles
        Output:
            Mass adds or removes a role to and from
            all users matching your specifications
        Add options:
            all/everyone:  Add everyone a role
            humans/people:  Add humans a role
            bots/robots:  Add bots a role
            role:  Add a role to all users with this role
        Remove options:
            all/everyone:  Remove everyone a role
            humans/people:  Remove humans a role
            bots/robots:  Remove bots a role
            role:  Remove a role from all users with this role
        Examples:
            {0}role add all @Helper
            {0}massrole remove @Helper Mod
            {0}multirole add bots @BotRole
        """
        if ctx.invoked_subcommand is None:
            await ctx.usage("<add/remove> <all/humans/bots/role> <role>")

    @_role.command(
        name="add",
        aliases=["apply"],
        brief="Add roles users with a role.",
        implemented="2021-05-16 15:06:06.479013",
        updated="2021-05-31 05:13:52.253369",
    )
    @checks.guild_only()
    @checks.bot_has_perms(manage_roles=True)
    @checks.has_perms(manage_roles=True)
    @checks.cooldown(2, 30, bucket=commands.BucketType.guild)
    async def _add(
        self, ctx, option: converters.MassRoleConverter, *, role: converters.DiscordRole
    ):
        """
        Usage: {0}role add <option> <role>
        Permission: Manage Roles
        Output:
            Mass adds a role to all users
            matching your specifications.
        Options:
            all/everyone:  Add everyone a role
            humans/people:  Add humans a role
            bots/robots:  Add bots a role
            role:  Add a role to all users with this role
        Notes:
            Pass two roles to add
            the second role to all users
            who have the first role.
            Pass 'bots' and a role to add
            all bots to a specified role
            Pass 'humans' and a role to add
            all humans to a specified role
            Pass 'all' and a role to add
            all users to a specified role

            If no role is found and 'bots',
            'humans' and 'all' were not used as an
            option, the bot will show a table
            with all valid option inputs.

            Roles can be passed as a mention,
            case-insensitive name, or an ID
        Examples:
            {0}role add all @Helper
            {0}massrole add @Helper Mod
            {0}multirole add bots @Bots
        """
        if isinstance(option, discord.Role):
            res = await checks.role_priv(ctx, option)
            if res:
                return await ctx.fail(res)

            role_members = [m for m in ctx.guild.members if option in m.roles]
            targets = [m for m in role_members if role not in m.roles]
            await self.do_massrole(ctx, "add", targets, role, "user")

        elif option == "all":
            targets = [m for m in ctx.guild.members if role not in m.roles]
            await self.do_massrole(ctx, "add", targets, role, "user")

        elif option == "humans":
            humans = [m for m in ctx.guild.members if not m.bot]
            targets = [h for h in humans if role not in h.roles]
            await self.do_massrole(ctx, "add", targets, role, "human")

        elif option == "bots":
            bots = [m for m in ctx.guild.members if m.bot]
            targets = [bot for bot in bots if role not in bot.roles]
            await self.do_massrole(ctx, "add", targets, role, "bot")

    @_role.command(
        name="remove",
        aliases=["rm", "rem"],
        brief="Add roles users with a role.",
        implemented="2021-05-16 15:06:06.479013",
        updated="2021-05-31 05:13:52.253369",
        invoke_without_command=True,
        case_insensitive=True,
    )
    @checks.guild_only()
    @checks.bot_has_perms(manage_roles=True)
    @checks.has_perms(manage_roles=True)
    @checks.cooldown(2, 30, bucket=commands.BucketType.guild)
    async def _remove(
        self, ctx, option: converters.MassRoleConverter, *, role: converters.DiscordRole
    ):
        """
        Usage: {0}role remove <option> <role>
        Aliases: {0}role rm, {0}role rem
        Permission: Manage Roles
        Output:
            Mass removes a role from all users
            matching your specifications.
        Options:
            all/everyone:  Add everyone a role
            humans/people:  Add humans a role
            bots/robots:  Add bots a role
            role:  Remove a role from all users with this role
        Notes:
            Pass two roles to remove
            the second role from all users
            who have the first role.
            Pass 'bots' and a role to remove
            all bots from a specified role
            Pass 'humans' and a role to remove
            all humans from a specified role
            Pass 'all' and a role to remove
            all users from a specified role

            If no role is found and 'bots',
            'humans' and 'all' were not used as an
            option, the bot will show a table
            with all valid option inputs.

            Roles can be passed as a mention,
            case-insensitive name, or an ID
        Examples:
            {0}role remove all @Helper
            {0}massrole rem @Helper Mod
            {0}multirole rm bots @Bots
        """
        if isinstance(option, discord.Role):
            res = await checks.role_priv(ctx, option)
            if res:
                return await ctx.fail(res)

            role_members = [m for m in ctx.guild.members if option in m.roles]
            targets = [m for m in role_members if role in m.roles]
            await self.do_massrole(ctx, "remove", targets, role, "user")

        elif option == "all":
            targets = [m for m in ctx.guild.members if role in m.roles]
            await self.do_massrole(ctx, "remove", targets, role, "user")

        elif option == "humans":
            humans = [m for m in ctx.guild.members if not m.bot]
            targets = [h for h in humans if role in h.roles]
            await self.do_massrole(ctx, "remove", targets, role, "human")

        elif option == "bots":
            bots = [m for m in ctx.guild.members if m.bot]
            targets = [bot for bot in bots if role in bot.roles]
            await self.do_massrole(ctx, "remove", targets, role, "bot")

    async def do_massrole(self, ctx, add_or_remove, targets, role, obj):

        self.start_working(ctx.guild, "massrole")

        if add_or_remove.lower() == "add":
            add = True
        else:
            add = False
        res = await checks.role_priv(ctx, role)
        if res:
            return await ctx.fail(res)

        success = []
        failed = []

        warning = "This process may take several minutes. Please be patient."
        ternary = "Add" if add else "Remov"
        to_from = "to" if add else "from"
        plural = lambda l: "" if len(l) == 1 else "s"
        em = self.bot.emote_dict["loading"]
        msg = await ctx.send_or_reply(
            f"{em} {ternary}ing role `{role.name}` {to_from} {len(targets)} {obj}{plural(targets)}. {warning}"
        )

        for target in targets:
            try:
                reason = f"Role {ternary.lower()}ed by command."
                if add:
                    await target.add_roles(role, reason=reason)
                else:
                    await target.remove_roles(role, reason=reason)
                success.append(str(target))
            except Exception as e:
                failed.append((str(target), e))

        self.stop_working(ctx.guild)

        if success or not failed:
            em = self.bot.emote_dict["success"]
            await msg.edit(
                content=f"{em} {ternary}ed role `{role.name}` {to_from} {len(success)} {obj}{plural(success)}."
            )
            self.bot.dispatch("mod_action", ctx, targets=success)
        if failed:
            await helpers.error_info(ctx, failed)

    @decorators.group(
        name="prefix",
        invoke_without_command=True,
        case_insensitive=True,
        brief="Show all server prefixes.",
    )
    async def prefix(self, ctx):
        """
        Alias for {0}prefixes
        """
        await ctx.invoke(self.prefixes)

    @prefix.command(name="add", ignore_extra=False, brief="Add a server prefix.")
    @checks.guild_only()
    @checks.has_perms(manage_guild=True)
    @checks.cooldown()
    async def prefix_add(self, ctx, prefix: converters.Prefix):
        await ctx.invoke(self.addprefix, prefix)

    @prefix.command(
        name="remove",
        aliases=["delete", "rm", "rem"],
        ignore_extra=False,
        brief="Remove a server prefix.",
    )
    @checks.guild_only()
    @checks.has_perms(manage_guild=True)
    @checks.cooldown()
    async def prefix_remove(self, ctx, prefix: converters.Prefix):
        await ctx.invoke(self.removeprefix, prefix)

    @prefix.command(name="clear", brief="Clear all server prefixes.")
    @checks.guild_only()
    @checks.has_perms(manage_guild=True)
    async def prefix_clear(self, ctx, prefix: converters.Prefix = None):
        await ctx.invoke(self.clearprefix, prefix)

    @decorators.command(
        aliases=[
            "showprefixes",
            "showprefix",
            "displayprefix",
            "displayprefixes",
            "whatprefix",
        ],
        brief="Show all server prefixes.",
        implemented="2021-05-03 09:14:59.219515",
        updated="2021-05-05 19:23:39.306805",
    )
    @checks.cooldown()
    async def prefixes(self, ctx):
        """
        Usage: {0}prefix
        Aliases:
            {0}prefix, {0}prefix show, {0}prefix display,
            {0}showprefixes, {0}showprefix, {0}whatprefix
            {0}displayprefixes, {0}displayprefix
        Output:
            Shows all my current server prefixes.
        """
        if not ctx.guild:
            prefixes = list(set(self.bot.common_prefixes + [self.bot.constants.prefix]))
            prefixes = prefixes.copy()
            mention_fmt = self.bot.user.name
        else:
            prefixes = self.bot.get_guild_prefixes(ctx.guild)
            mention_fmt = ctx.guild.me.display_name
            # Lets remove the mentions and replace with @name
            del prefixes[0]
            del prefixes[0]

        prefixes.insert(0, f"@{mention_fmt}")

        await ctx.success(
            f"My current prefix{' is' if len(prefixes) == 1 else 'es are'} `{', '.join(prefixes)}`"
        )

    @decorators.command(
        aliases=["createprefix"],
        brief="Add a custom server prefix.",
        implemented="2021-05-03 09:14:59.219515",
        updated="2021-05-05 19:23:39.306805",
        ignore_extra=False,
        hidden=True,
    )
    @checks.guild_only()
    @checks.has_perms(manage_guild=True)
    @checks.cooldown()
    async def addprefix(self, ctx, prefix: converters.Prefix):
        """
        Usage: {0}addprefix <new prefix>
        Aliases:
            {0}addprefix, {0}prefix add,
            {0}prefix create, {0}createprefix
        Output:
            Adds a prefix to the list of custom prefixes.
        Notes:
            Previously set prefixes are not overridden.
            The max prefixes to add is 10 per server,
            each a maximum of 20 characters in length.
            Multi-word prefixes must be quoted.
        """
        current_prefixes = self.bot.get_raw_guild_prefixes(ctx.guild.id)
        if prefix in current_prefixes:
            return await ctx.fail(f"`{prefix}` is already a registered prefix.")
        current_prefixes.append(prefix)
        try:
            await self.bot.set_guild_prefixes(ctx.guild, current_prefixes)
        except Exception as e:
            await ctx.send_or_reply(f"{e}")
        else:
            await ctx.success(f"Successfully added prefix: `{prefix}`")

    @addprefix.error
    async def prefix_add_error(self, ctx, error):
        if isinstance(error, commands.TooManyArguments):
            await ctx.fail(
                "If your prefix is multiple words, surround it in quotes. Otherwise, add them one at a time."
            )
            ctx.handled = True

    @decorators.command(
        aliases=["deleteprefix", "rmprefix", "remprefix", "delprefix"],
        brief="Remove a custom server prefix",
        implemented="2021-05-03 09:14:59.219515",
        updated="2021-05-05 19:23:39.306805",
        ignore_extra=False,
        hidden=True,
    )
    @checks.guild_only()
    @checks.has_perms(manage_guild=True)
    @checks.cooldown()
    async def removeprefix(self, ctx, prefix: converters.Prefix):
        """
        Usage: {0}removeprefix <new prefix>
        Aliases:
            {0}rmprefix, {0}prefix remove, {0}prefix rm
            {0}prefix rem, {0}prefix del, {0}prefix delete,
            {0}deleteprefix, {0}delprefix, {0}remprefix
        Permission: Manage Server
        Output:
            Removes a prefix from the list of custom prefixes.
        Notes:
            Will ask for confirmation if only one
            custom prefix is currently in use.
        """
        current_prefixes = self.bot.get_raw_guild_prefixes(ctx.guild.id)
        if len(current_prefixes) == 0:
            return await ctx.fail("I currently have no prefixes registered.")
        if len(current_prefixes) == 1:
            c = await pagination.Confirmation(
                msg=f"{self.bot.emote_dict['exclamation']} **Upon confirmation, I will only respond to `@{ctx.guild.me.display_name}` Do you wish to continue?**"
            ).prompt(ctx)
            if c:
                await self.bot.set_guild_prefixes(ctx.guild, [])
                await ctx.success(
                    f"Successfully cleared all prefixes. I will now only respond to <@!{self.bot.user.id}>"
                )
            else:
                await ctx.send_or_reply(f"**Cancelled.**")
            return

        try:
            current_prefixes.remove(prefix)
        except ValueError:
            return await ctx.fail("I do not have this prefix registered.")

        try:
            await self.bot.set_guild_prefixes(ctx.guild, current_prefixes)
        except Exception as e:
            await ctx.send_or_reply(f"{e}")
        else:
            await ctx.success(f"Successfully removed prefix: `{prefix}`")

    @removeprefix.error
    async def prefix_rem_error(self, ctx, error):
        if isinstance(error, commands.TooManyArguments):
            await ctx.fail(
                "If your prefix is multiple words, surround it in quotes. Otherwise, remove them one at a time."
            )
            ctx.handled = True

    @decorators.command(
        aliases=["clearprefixes", "resetprefix", "resetprefixes"],
        brief="Clear all custom prefixes.",
        implemented="2021-05-03 09:14:59.219515",
        updated="2021-05-05 19:23:39.306805",
        hidden=True,
    )
    @checks.guild_only()
    @checks.has_perms(manage_guild=True)
    @checks.cooldown()
    async def clearprefix(self, ctx):
        """
        Usage: {0}clearprefix
        Aliases:
            {0}clearprefixes, {0}prefix clear,
            {0}resetprefix, {0}resetprefixes,
        Permission: Manage Server
        Output:
            Removes all custom prefixes.
        Notes:
            After this, the bot will listen to only mention prefixes.
            To add a new custom prefix, use {0}prefix add <new prefix>
        """
        current_prefixes = self.bot.get_raw_guild_prefixes(ctx.guild.id)
        if len(current_prefixes) == 0:
            return await ctx.fail("I currently have no prefixes registered.")
        c = await pagination.Confirmation(
            msg=f"{self.bot.emote_dict['exclamation']} **Upon confirmation, I will only respond to `@{ctx.guild.me.display_name}` Do you wish to continue?**"
        ).prompt(ctx)
        if c:
            await self.bot.set_guild_prefixes(ctx.guild, [])
            await ctx.success(
                f"Successfully cleared all prefixes. I will now only respond to `@{ctx.guild.me.display_name}`"
            )
        else:
            await ctx.send_or_reply(f"**Cancelled.**")

    @decorators.group(
        name="reset",
        brief="Manage stored user data.",
        implemented="2021-07-08 16:15:20.525820",
        updated="2021-07-08 16:15:20.525820",
        invoke_without_command=True,
    )
    @checks.cooldown()
    async def _reset(self, ctx):
        """
        Usage: {0}reset <subcommand> <data option> [user]
        Subcommands:
            my: Reset data for yourself
            user: Reset server data for a user
            server: Reset data for the whole server
        Notes:
            For any assistance in deleting data,
            join the support server.
            Invite: https://discord.gg/H2qTG4yxqb
        """
        if ctx.invoked_subcommand is None:
            await ctx.usage("<my/user/server> <data option> [user]")

    @_reset.command(
        aliases=["me"],
        brief="Reset your global data",
    )
    @checks.cooldown(2, 30)
    async def my(self, ctx, option: converters.UserDataOption):
        """
        Usage: {0}reset my [option]
        Alias: {0}reset me
        Options:
            avatars
            statuses
            usernames
        Notes:
            If you wish to delete data
            not in the above options,
            voice your wish in the support server.
            Invite: https://discord.gg/H2qTG4yxqb
        """

        def opt_fmt(option):
            if option == "statuses":
                return "status"
            return option[:-1]

        c = await ctx.confirm(
            f"This action will delete all your {opt_fmt(option)} data."
        )
        if c:
            if option == "avatars":
                query = """
                        WITH data AS (
                            DELETE FROM useravatars
                            WHERE user_id = $1
                            RETURNING avatar
                        )
                        DELETE FROM avatars
                        WHERE hash IN (
                            SELECT avatar
                            FROM data
                        );
                        """
            elif option == "usernames":
                query = """
                        DELETE FROM usernames
                        WHERE user_id = $1;
                        """

            elif option == "statuses":
                query = """
                        DELETE FROM userstatus
                        WHERE user_id = $1;
                        """

            await self.bot.cxn.execute(query, ctx.author.id)
            await ctx.success(f"Reset all your {opt_fmt(option)} data.")

    @_reset.command(
        name="user", aliases=["member"], brief="Reset server data for a user."
    )
    @checks.guild_only()
    @checks.is_mod()
    @checks.cooldown(2, 30)
    async def reset_user(
        self, ctx, option: converters.ServerDataOption, *, user: converters.DiscordUser
    ):
        """
        Usage: {0}reset user <option> <user>
        Output:
            Delete recorded data for a user
        Options:
            invites
            messages
            nicknames
        Notes:
            Once removed, the data cannot be
            recovered. Use with caution.
        """
        c = await ctx.confirm(
            f"This action will delete all {option[:-1]} data collected on this server for `{user}`."
        )
        if c:
            if option == "invites":
                query = """
                        DELETE FROM invites
                        WHERE server_id = $1
                        AND inviter = $2;
                        """
            elif option == "messages":
                query = """
                        DELETE FROM messages
                        WHERE server_id = $1
                        AND author_id = $2;
                        """
            elif option == "nicknames":
                query = """
                        DELETE FROM usernicks
                        WHERE server_id = $1
                        AND user_id = $2;
                        """

            await self.bot.cxn.execute(query, ctx.guild.id, user.id)
            await ctx.success(f"Reset all {option[:-1]} data for `{user}`")

    @_reset.command(
        name="server", aliases=["guild"], brief="Reset server data for a user."
    )
    @checks.guild_only()
    @checks.is_mod()
    @checks.cooldown(2, 30)
    async def reset_server(self, ctx, option: converters.ServerDataOption):
        """
        Usage: {0}reset server <option>
        Output:
            Delete recorded data for the entire server
        Options:
            invites
            messages
            nicknames
        Notes:
            Once removed, the data cannot be
            recovered. Use with caution.
        """
        c = await ctx.confirm(
            f"This action will delete all {option[:-1]} data collected on this server."
        )
        if c:
            if option == "invites":
                query = """
                        DELETE FROM invites
                        WHERE server_id = $1;
                        """
            elif option == "messages":
                query = """
                        DELETE FROM messages
                        WHERE server_id = $1;
                        """
            elif option == "nicknames":
                query = """
                        DELETE FROM usernicks
                        WHERE server_id = $1;
                        """

            await self.bot.cxn.execute(query, ctx.guild.id)
            await ctx.success(f"Reset all {option[:-1]} data for this server.")


    @decorators.command(
        aliases=["serverlock", "lockserver", "frost"],
        brief="Lock all server channels.",
        examples="""
                {0}freeze
                {0}serverlock
                {0}lockserver
                """
    )
    @checks.has_perms(administrator=True)
    @checks.bot_has_perms(administrator=True)
    @checks.cooldown(2, 20)
    async def freeze(self, ctx):
        """
        Usage: {0}freeze
        Aliases: {0}frost, {0}serverlock, {0}serverunlock
        Permission: Administrator
        Output:
            Sets the send_messages permission to false
            for the @everyone role in all channels.
        Notes:
            Use with caution, the previous permissions
            will be permanently wiped and cannot be restored.
        """
        c = await ctx.confirm(f"This action will lock the entire server by removing permissions from the `@everyone` role.")
        if c:
            msg = await ctx.load("Freezing the server. This process may take several minutes...")
            for channel in ctx.guild.text_channels:
                await channel.set_permissions(ctx.guild.default_role, send_messages=False)

            await msg.edit(content=f"{self.bot.emote_dict['success']} Server frozen.")

    @decorators.command(
        aliases=["unlockserver", "serverunlock", "melt", "defrost"],
        brief="Unlock all server channels.",
        examples="""
                {0}unfreeze
                {0}melt
                {0}defrost
                {0}serverunlock
                {0}unlockserver
                """
    )
    @checks.has_perms(administrator=True)
    @checks.bot_has_perms(administrator=True)
    @checks.cooldown(2, 20)
    async def unfreeze(self, ctx):
        """
        Usage: {0}unfreeze
        Aliases: {0}defrost, {0}serverlock, {0}serverunlock, {0}melt
        Permission: Administrator
        Output:
            Resets the send_messages permission to default
            for the @everyone role in all channels.
        Notes:
            Use with caution, the previous permissions
            will be permanently wiped and cannot be restored.
        """
        c = await ctx.confirm(f"This action will unlock the entire server by resetting permissions for the `@everyone` role.")
        if c:
            msg = await ctx.load("Unfreezing the server. This process may take several minutes...")
            for channel in ctx.guild.text_channels:
                await channel.set_permissions(ctx.guild.default_role, send_messages=None)

            await msg.edit(content=f"{self.bot.emote_dict['success']} Server unfrozen.")

            


