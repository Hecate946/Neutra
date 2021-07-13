import discord

from better_profanity import profanity
from discord.ext import commands, menus
from discord.ext.commands.core import check

from utilities import utils
from utilities import checks
from utilities import helpers
from utilities import converters
from utilities import decorators
from utilities import pagination


def setup(bot):
    bot.add_cog(Automod(bot))


class Automod(commands.Cog):
    """
    Manage the automod system.
    """

    def __init__(self, bot):
        self.bot = bot
        self.emote_dict = bot.emote_dict

    ###################
    ## Warn Commands ##
    ###################

    @decorators.command(
        aliases=["strike"],
        brief="Warn users with an optional reason.",
        implemented="2021-04-07 01:26:34.603363",
        updated="2021-07-07 22:07:21.374659",
    )
    @checks.guild_only()
    @checks.has_perms(kick_members=True)
    @checks.cooldown()
    async def warn(
        self,
        ctx,
        targets: commands.Greedy[converters.DiscordMember(False)],
        *,
        reason: str = None,
    ):
        """
        Usage: {0}warn [target] [target]... [reason]
        Alias: {0}strike
        Output: Warns members and DMs them the reason they were warned for
        Permission: Kick Members
        Notes:
            Warnings do not automatically enforce punishments on members.
            They only store a record of how many instances a user has misbehaved.
        """
        if not len(targets):
            return await ctx.usage()
        warned = []
        failed = []
        insert = []
        for target in targets:
            res = await checks.check_priv(ctx, target)
            if res:
                failed.append((str(target), res))
                continue
            if reason:
                try:
                    embed = discord.Embed(color=self.bot.constants.embed)
                    embed.title = "Warn Notice"
                    embed.description = (
                        f"**Server**: `{ctx.guild.name} ({ctx.guild.id})`\n"
                    )
                    embed.description += (
                        f"**Moderator**: `{ctx.author} ({ctx.author.id})`\n"
                    )
                    embed.description += f"**Reason**: `{reason}`"
                    await target.send(embed=embed)
                except Exception:
                    pass
            warned.append(str(target))
            insert.append((target.id, ctx.guild.id, reason))

        query = """
                INSERT INTO warns (user_id, server_id, reason)
                VALUES ($1, $2, $3)
                """
        await self.bot.cxn.executemany(query, (data for data in insert))

        if warned:
            await ctx.success(f"Warned `{', '.join(warned)}`")
        if failed:
            await helpers.error_info(ctx, failed)

    @decorators.command(
        brief="Count the warnings a user has.",
        implemented="2021-04-07 01:26:34.603363",
        updated="2021-07-07 22:07:21.374659",
    )
    @checks.guild_only()
    @checks.cooldown()
    async def warncount(self, ctx, *, target: converters.DiscordMember = None):
        """
        Usage: {0}warncount [user]
        Output: Show how many warnings the user has
        """
        target = target or ctx.author

        query = """
                SELECT COUNT(*)
                FROM warns
                WHERE user_id = $1
                AND server_id = $2;
                """
        wc = await self.bot.cxn.fetchval(query, target.id, ctx.guild.id)
        if not wc or wc == 0:
            return await ctx.success(f"User `{target}` has no warnings.")

        em = self.bot.emote_dict["exclamation"]
        fmt = "warning" if wc == 1 else "warnings"
        guild = f"**{ctx.guild.name}**"

        await ctx.send_or_reply(
            f"{em} User `{target}` currently has **{wc}** {fmt} in {guild}."
        )

    @decorators.command(
        brief="Show all warnings a user has.",
        implemented="2021-07-08 02:15:33.685845",
        updated="2021-07-08 02:15:33.685845",
    )
    @checks.guild_only()
    @checks.bot_has_perms(add_reactions=True, embed_links=True, external_emojis=True)
    @checks.cooldown()
    async def listwarns(self, ctx, target: converters.DiscordMember = None):
        target = target or ctx.author

        query = """
                SELECT id, reason AS res, insertion AS time
                FROM warns WHERE user_id = $1
                AND server_id = $2 ORDER BY insertion DESC;
                """
        warns = await self.bot.cxn.fetch(query, target.id, ctx.guild.id)
        if not warns:
            return await ctx.success(f"User `{target}` has no current warnings.")

        p = pagination.MainMenu(
            pagination.FieldPageSource(
                entries=[
                    (
                        f"**Warning ID:** {rec['id']}",
                        f"**Issued:** {utils.short_time(rec['time'])}\n"
                        f"**Reason:** {rec['res']}",
                    )
                    for rec in warns
                ],
                title="User Warnings",
                per_page=10,
                description=f"User `{target}` has {len(warns)} total warning{'' if len(warns) == 1 else 's'}.",
            )
        )

        try:
            await p.start(ctx)
        except menus.MenuError as e:
            await ctx.send_or_reply(e)

    @decorators.command(
        aliases=[
            "deletewarnings",
            "removewarns",
            "removewarnings",
            "deletewarns",
            "clearwarnings",
        ],
        brief="Clear a user's warnings",
        implemented="2021-04-07 01:26:34.603363",
        updated="2021-07-07 22:07:21.374659",
    )
    @checks.guild_only()
    @checks.has_perms(kick_members=True)
    @checks.cooldown()
    async def clearwarns(self, ctx, *, target: converters.DiscordMember):
        """
        Usage: {0}clearwarns [user]
        Aliases: {0}deletewarnings, {0}removewarns, {0}removewarnings, {0}deletewarns, {0}clearwarnings
        Permission: Kick Members
        Output: Clears all warnings for that user
        """
        query = """
                DELETE FROM warns
                WHERE user_id = $1
                AND server_id = $2
                RETURNING warning;
                """
        data = await self.bot.cxn.fetch(query, target.id, ctx.guild.id)
        if not data:
            await ctx.success(f"User `{target}` has no current warnings.")
            return
        fmt = f"{len(data)} warning{'' if len(data) == 1 else 's'}"
        await ctx.success(f"Cleared {fmt} for `{target}`")
        try:
            await target.send(
                f"Moderator `{ctx.author}` has cleared all your warnings in **{ctx.guild.name}**."
            )
        except Exception:
            pass

    @decorators.command(
        aliases=["unstrike"],
        brief="Revoke a warning from a user",
        implemented="2021-07-08 06:59:09.201252",
        updated="2021-07-08 06:59:09.201252",
    )
    @commands.guild_only()
    @checks.has_perms(kick_members=True)
    async def unwarn(self, ctx, warning_id: int):
        """
        Usage: {0}revokewarn [warning id]
        Aliases: {0}unstrike
        Permission: Kick Members
        Output: Revokes a warning from a user
        """
        query = """
                DELETE FROM warns
                WHERE server_id = $1
                AND id = $2
                RETURNING *
                """
        data = await self.bot.cxn.fetchrow(query, ctx.guild.id, warning_id)
        if not data:
            return await ctx.fail(
                f"**Invalid warning ID.** Use `{ctx.clean_prefix}listwarns [user]` to view valid warning IDs."
            )
        user = await self.bot.fetch_user(data["user_id"])
        if not user:
            return await ctx.fail(
                "The user this warning was issued for no longer exists."
            )
        await ctx.success(
            f"Removed warning #{data['id']} for user `{user}`\n"
            f"\n**Issued:** {utils.short_time(data['insertion'])}"
            f"\n**Reason:** {data['reason']}"
        )

    @decorators.command(
        aliases=["serverwarns"],
        brief="Display the server warnlist.",
        implemented="2021-04-07 01:26:34.603363",
        updated="2021-07-07 22:07:21.374659",
    )
    @checks.guild_only()
    @checks.bot_has_perms(add_reactions=True, embed_links=True, external_emojis=True)
    @checks.has_perms(manage_messages=True)
    @checks.cooldown()
    async def warns(self, ctx):
        """
        Usage: {0}warns
        Alias: {0}serverwarns
        Output: Embed of all warned members in the server
        Permission: Manage Messages
        """
        query = """
                SELECT user_id AS u, COUNT(*) as c
                FROM warns WHERE server_id = $1
                GROUP BY user_id ORDER BY c DESC;
                """
        records = await self.bot.cxn.fetch(query, ctx.guild.id)
        if not records:
            return await ctx.success("No current warnings exist on this server.")

        def mem(snowflake):
            m = ctx.guild.get_member(snowflake)
            if m:
                return m

        entries = [
            f"User: `{mem(rec['u'])}` Warnings: `{rec['c']}`"
            for rec in records
            if mem(rec["u"])
        ]

        p = pagination.SimplePages(
            entries=entries,
            per_page=20,
        )
        p.embed.title = f"Server Warn List ({len(entries):,} Users)"
        try:
            await p.start(ctx)
        except menus.MenuError as e:
            await ctx.send_or_reply(e)

    @decorators.command(
        brief="Enable or disable auto-deleting invite links",
        aliases=["removeinvitelinks", "deleteinvites", "antiinvites"],
        implemented="2021-04-07 01:26:34.603363",
        updated="2021-07-07 22:07:21.374659",
    )
    @checks.guild_only()
    @checks.bot_has_perms(manage_messages=True)
    @checks.has_perms(manage_guild=True)
    @checks.cooldown()
    async def antiinvite(self, ctx, *, yes_no=None):
        """
        Usage:      {0}antiinvite <yes|enable|true|on||no|disable|false|off>
        Aliases:    {0}removeinvites, -deleteinvites, -antiinvites
        Permission: Manage Server
        Output:     Removes invite links sent by users.
        Notes:
            Users with the Manage Messages permission
            are immune to the antiinviter.
        """
        query = """SELECT antiinvite FROM servers WHERE server_id = $1"""
        current = await self.bot.cxn.fetchval(query, ctx.guild.id)
        if current is True:
            removeinvitelinks = True
        else:
            removeinvitelinks = False
        if yes_no is None:
            # Output current setting
            msg = "{} currently *{}*.".format(
                "Removal of invite links", "enabled" if current is True else "disabled"
            )
        elif yes_no.lower() in ["yes", "on", "true", "enabled", "enable"]:
            yes_no = True
            removeinvitelinks = True
            msg = "{} {} *enabled*.".format(
                "Removal of invite links", "remains" if current is True else "is now"
            )
        elif yes_no.lower() in ["no", "off", "false", "disabled", "disable"]:
            yes_no = False
            removeinvitelinks = False
            msg = "{} {} *disabled*.".format(
                "Removal of invite links", "is now" if current is True else "remains"
            )
        else:
            msg = "That is not a valid setting."
            yes_no = current
        if yes_no != current and yes_no is not None:
            self.bot.server_settings[ctx.guild.id]["antiinvite"] = removeinvitelinks
            query = """
                    UPDATE servers
                    SET antiinvite = $1
                    WHERE server_id = $2
                    """
            await self.bot.cxn.execute(query, removeinvitelinks, ctx.guild.id)
        await ctx.send_or_reply(msg)

    @decorators.group(
        aliases=["autoroles", "autoassign"],
        brief="Assign roles to new members.",
        implemented="2021-04-07 01:26:34.603363",
        updated="2021-07-07 22:07:21.374659",
    )
    @checks.bot_has_perms(manage_roles=True)
    @checks.has_perms(manage_guild=True, manage_roles=True)
    async def autorole(self, ctx):
        """
        Usage: {0}autorole <option>
        Aliases:
            {0}autoassign
            {0}autoroles
        Output: Assigns roles to new users
        Examples:
            {0}autorole add <role1> <role2>
            {0}autorole show
        Permission: Manage Server, Manage Roles
        Options:
            add, remove, clear, show
        """
        if ctx.invoked_subcommand is None:
            return await ctx.usage("<option> [arguments]")

    @autorole.command(brief="Auto-assign roles on user join.")
    async def add(self, ctx, roles: commands.Greedy[converters.DiscordRole] = None):
        """
        Usage: {0}autorole add <role1> [role2]...
        Output:
            Will automatically assign
            the passed roles to users
            who join the server.
        Examples:
            {0}autorole add <role1> [role2]
            {0}autoassign add <role>
        Notes:
            Accepts any number of roles.
            Roles with multiple words must
            be encapsulated by quotes.
        """
        if roles is None:
            return await ctx.usage("<roles>")
        for role in roles:
            self.bot.server_settings[ctx.guild.id]["autoroles"].append(role.id)
        query = """
                UPDATE servers
                SET autoroles = $1
                WHERE server_id = $2;
                """
        autoroles = ",".join(
            [str(x) for x in self.bot.server_settings[ctx.guild.id]["autoroles"]]
        )
        await self.bot.cxn.execute(query, autoroles, ctx.guild.id)
        await ctx.send_or_reply(
            content=f"{self.bot.emote_dict['success']} Updated autorole settings.",
        )

    @autorole.command(aliases=["rem", "rm"], brief="Remove automatic autoroles.")
    async def remove(self, ctx, roles: commands.Greedy[converters.DiscordRole] = None):
        """
        Usage: {0}autorole remove <role1> [role2]...
        Output:
            Will no longer assign
            the passed roles to users
            who join the server.
        Examples:
            {0}autorole rm <role1> <role2>
            {0}autoassign remove <role>
        Notes:
            Accepts any number of roles.
            Roles with multiple words must
            be encapsulated by quotes.
        """
        if roles is None:
            return await ctx.usage("<roles>")
        autoroles = self.bot.server_settings[ctx.guild.id]["autoroles"]
        for role in roles:
            index = autoroles.index(str(role.id))
            autoroles.pop(index)
        query = """
                UPDATE servers
                SET autoroles = $1
                WHERE server_id = $2;
                """
        autoroles = ",".join(
            [str(x) for x in self.bot.server_settings[ctx.guild.id]["autoroles"]]
        )
        await self.bot.cxn.execute(query, autoroles, ctx.guild.id)
        await ctx.success("Updated autorole settings.")

    @autorole.command(brief="Clear all current autoroles.")
    async def clear(self, ctx):
        """
        Usage: {0}autorole clear
        Output:
            Will no longer assign
            any previous autoroles
            to users who join the server.
        Examples:
            {0}autorole rm <role1> [role2]
            {0}autoassign remove <role>
        Notes:
            Will ask for confirmation.
        """
        if not self.bot.server_settings[ctx.guild.id]["autoroles"]:
            return await ctx.fail("This server has no current autoroles.")
        content = f"{self.bot.emote_dict['exclamation']} **This action will remove all current autoroles. Do you wish to continue?**"
        p = await pagination.Confirmation(msg=content).prompt(ctx)
        if p:
            self.bot.server_settings[ctx.guild.id]["autoroles"] = []
            query = """
                    UPDATE servers
                    SET autoroles = NULL
                    WHERE server_id = $1;
                    """
            await self.bot.cxn.execute(query, ctx.guild.id)
            await ctx.send_or_reply(
                content=f"{self.bot.emote_dict['success']} Cleared all autoroles.",
            )
        else:
            await ctx.send_or_reply(
                f"{self.bot.emote_dict['exclamation']} **Cancelled.**"
            )

    @autorole.command(brief="Show all current autoroles.", aliases=["display"])
    async def show(self, ctx):
        """
        Usage: {0}autorole show
        Alias: {0}autorole display
        Output:
            Will start a pagination session
            showing all current autoroles
        Examples:
            {0}autorole display
            {0}autoassign show
        """
        autoroles = self.bot.server_settings[ctx.guild.id]["autoroles"]

        if autoroles == []:
            return await ctx.send_or_reply(
                content=f"No autoroles yet, use `{ctx.clean_prefix}autorole add <roles>`",
            )

        p = pagination.SimplePages(
            entries=[f"`{ctx.guild.get_role(int(x)).name}`" for x in autoroles],
            per_page=20,
        )
        p.embed.title = "Autoroles in {} ({:,} total)".format(
            ctx.guild.name, len(autoroles)
        )

        try:
            await p.start(ctx)
        except menus.MenuError as e:
            await ctx.send_or_reply(e)

    @decorators.command(brief="Reassign roles on user rejoin.", aliases=["stickyroles"])
    @commands.guild_only()
    @checks.bot_has_perms(manage_roles=True)
    @checks.has_perms(manage_guild=True, manage_roles=True)
    async def reassign(self, ctx, *, yes_no=None):
        """
        Usage:      {0}reassign <yes|enable|true|on||no|disable|false|off>
        Aliases:    {0}stickyroles
        Permission: Manage Server
        Output:     Reassigns roles when past members rejoin the server.
        Notes:
            This setting is enabled by default. The bot will attempt to
            add the users their old roles unless it is missing permissions.
        """
        current = self.bot.server_settings[ctx.guild.id]["reassign"]
        if current is False:
            reassign = False
        else:
            current is True
            reassign = True
        if yes_no is None:
            # Output what we have
            msg = "{} currently **{}**.".format(
                "Reassigning roles on member rejoin",
                "enabled" if current is True else "disabled",
            )
        elif yes_no.lower() in ["yes", "on", "true", "enabled", "enable"]:
            yes_no = True
            reassign = True
            msg = "{} {} **enabled**.".format(
                "Reassigning roles on member rejoin",
                "remains" if current is True else "is now",
            )
        elif yes_no.lower() in ["no", "off", "false", "disabled", "disable"]:
            yes_no = False
            reassign = False
            msg = "{} {} **disabled**.".format(
                "Reassigning roles on member rejoin",
                "is now" if current is True else "remains",
            )
        else:
            msg = f"{self.bot.emote_dict['warn']} That is not a valid setting."
            yes_no = current
        if yes_no != current and yes_no is not None:
            await self.bot.cxn.execute(
                "UPDATE servers SET reassign = $1 WHERE server_id = $2",
                reassign,
                ctx.guild.id,
            )
            self.bot.server_settings[ctx.guild.id]["reassign"] = reassign
        await ctx.send_or_reply(msg)

    @decorators.group(
        invoke_without_command=True,
        case_insensitive=True,
        name="filter",
        aliases=["profanity"],
        brief="Manage the server's word filter.",
    )
    @checks.guild_only()
    @checks.has_perms(manage_guild=True)
    @checks.cooldown(bucket=commands.BucketType.guild)
    async def _filter(self, ctx):
        """
        Usage: {0}filter <option>
        Alias: {0}profanity
        Permission: Manage Server
        Output:
            Adds, removes, clears, or displays the filter.
        Example:
            {0}filter add <badwords>
        Options:
            add, remove, display, clear
        Notes:
            Words added to the filter list
            will delete all messages with
            that word. Users with the
            Manage Messages permission are immune.
            To add or remove multiple words with
            one command, separate the words by a comma.
            Example: {0}filter add badword1, badword2
        """
        if ctx.invoked_subcommand is None:
            help_command = self.bot.get_command("help")
            await help_command(ctx, invokercommand="filter")

    @_filter.command(name="add", aliases=["+"], brief="Add words to the filter.")
    @checks.has_perms(manage_guild=True)
    async def add_words(self, ctx, *, words_to_filter: str):
        """
        Usage: {0}filter add <words>
        Output:
            Saves all the passed words
            and will delete when users
            without the Manage Messages
            permission send those words.
        Notes:
            separate words by a comma
            to add multiple words at once.
        """
        words_to_filter = words_to_filter.split(",")

        current_filter = self.bot.server_settings[ctx.guild.id]["profanities"]

        added = []
        existing = []
        for word in words_to_filter:
            if word.strip().lower() not in current_filter:
                current_filter.append(word.strip().lower())
                added.append(word.strip().lower())
            else:
                existing.append(word.strip().lower())

        insertion = ",".join(current_filter)

        query = """UPDATE servers SET profanities = $1 WHERE server_id = $2;"""
        await self.bot.cxn.execute(query, insertion, ctx.guild.id)

        if existing:
            await ctx.send_or_reply(
                content=f"{self.bot.emote_dict['warn']} The word{'' if len(existing) == 1 else 's'} `{', '.join(existing)}` "
                f"{'was' if len(existing) == 1 else 'were'} already in the word filter.",
            )

        if added:
            await ctx.send_or_reply(
                content=f"{self.bot.emote_dict['success']} The word{'' if len(added) == 1 else 's'} `{', '.join(added)}` "
                f"{'was' if len(added) == 1 else 'were'} successfully added to the word filter.",
            )

    @_filter.command(
        name="remove",
        aliases=["-", "rm", "rem"],
        brief="Removes words from the filter.",
    )
    @checks.has_perms(manage_guild=True)
    async def remove_words(self, ctx, *, words: str):
        """
        Usage: {0}filter remove <words>
        Alias: {0}-, {0}rm , {0}rem
        Output:
            Deletes the passed words from
            the filter (if they were saved.)
        Notes:
            separate words by a comma
            to remove multiple words at once.
        """
        words_to_remove = words.lower().split(",")

        word_list = self.bot.server_settings[ctx.guild.id]["profanities"]
        if not word_list:
            return await ctx.fail(f"This server has no filtered words.")

        removed = []
        not_found = []
        for word in words_to_remove:
            if word.strip().lower() not in word_list:
                not_found.append(word)
                continue
            else:
                word_index = word_list.index(word.strip().lower())
                word_list.pop(word_index)
                removed.append(word.strip().lower())

        insertion = ",".join(word_list)

        query = """
                UPDATE servers
                SET profanities = $1
                WHERE server_id = $2;
                """
        await self.bot.cxn.execute(query, insertion, ctx.guild.id)

        if not_found:
            await ctx.fail(
                f"The word{'' if len(not_found) == 1 else 's'} `{', '.join(not_found)}` "
                f"{'was' if len(not_found) == 1 else 'were'} not in the word filter.",
            )

        if removed:
            await ctx.success(
                f"The word{'' if len(removed) == 1 else 's'} `{', '.join(removed)}` "
                f"{'was' if len(removed) == 1 else 'were'} successfully removed from the word filter.",
            )

    @_filter.command(brief="Show all filtered words.", aliases=["show"])
    @checks.has_perms(manage_guild=True)
    async def display(self, ctx):
        """
        Usage: {0}filter display
        Alias: {0}filter show
        Output:
            Starts a pagination session to
            show all currently filtered words.
        """
        words = self.bot.server_settings[ctx.guild.id]["profanities"]

        if not words:
            return await ctx.fail(
                f"No filtered words yet, use `{ctx.clean_prefix}filter add <word>` to filter words",
            )

        p = pagination.SimplePages(entries=[f"`{x}`" for x in words], per_page=20)
        p.embed.title = "Filtered words in {} ({:,} total)".format(
            ctx.guild.name, len(words)
        )

        try:
            await p.start(ctx)
        except menus.MenuError as e:
            await ctx.send_or_reply(e)

    @_filter.command(name="clear", brief="Clear all words from the filer.")
    @checks.has_perms(manage_guild=True)
    async def _clear(self, ctx):
        """
        Usage: {0}filter clear
        Output:
            Confirmation that the filtered
            word list has been cleared.
        """
        query = """
                UPDATE servers
                SET profanities = NULL
                WHERE server_id = $1;
                """
        await self.bot.cxn.execute(query, ctx.guild.id)
        self.bot.server_settings[ctx.guild.id]["profanities"].clear()

        await ctx.success(f"Removed all filtered words.")

    #####################
    ## Event Listeners ##
    #####################

    @commands.Cog.listener()
    @decorators.wait_until_ready()
    @decorators.event_check(lambda s, m: not m.bot)
    async def on_member_join(self, member):
        required_perms = member.guild.me.guild_permissions.manage_roles
        if not required_perms:
            return

        guild = member.guild
        reassign = self.bot.server_settings[member.guild.id]["reassign"]
        if reassign:
            query = """
                    SELECT roles
                    FROM userroles
                    WHERE user_id = $1
                    and server_id = $2;
                    """
            old_roles = await self.bot.cxn.fetchval(query, member.id, guild.id)
            if old_roles:
                roles = str(old_roles).split(",")
                role_objects = [
                    guild.get_role(int(role_id))
                    for role_id in roles
                    if guild.get_role(int(role_id))
                ]
                to_reassign = (
                    role_objects + member.roles
                )  # In case they already had roles added
                try:
                    await member.edit(
                        roles=to_reassign, reason="Roles reassigned on rejoin."
                    )
                except Exception:  # Try to add them on one by one.
                    for role in role_objects:
                        if role not in member.roles:
                            try:
                                await member.add_roles(role)
                            except Exception:
                                continue

        autoroles = self.bot.server_settings[member.guild.id]["autoroles"]
        if autoroles:
            role_objects = [
                guild.get_role(int(role_id))
                for role_id in autoroles
                if guild.get_role(int(role_id))
            ]
            to_assign = (
                role_objects + member.roles
            )  # In case they already had roles added
            try:
                await member.edit(
                    roles=to_assign, reason="Roles auto-assigned on join."
                )
            except Exception:  # Try to add them on one by one.
                for role in role_objects:
                    if role not in member.roles:
                        try:
                            await member.add_roles(role)
                        except Exception:
                            continue

    @commands.Cog.listener()
    @decorators.wait_until_ready()
    @decorators.event_check(lambda s, m: m.guild and not m.author.bot)
    async def on_message(self, message):  # Check for invite links and bad words
        if message.author.id in self.bot.constants.owners:
            return  # We are immune!
        if message.author.guild_permissions.manage_messages:
            return  # We are immune!
        if self.bot.dregex.search(message.content):  # Check for invite linkes
            removeinvitelinks = self.bot.server_settings[message.guild.id]["antiinvite"]
            if removeinvitelinks:  # Do we care?
                try:
                    await message.delete()
                    await message.channel.send(
                        f"{self.bot.emote_dict['failed']} No invite links allowed",
                        delete_after=7,
                    )
                except Exception:  # We tried...
                    pass
        bad_words = self.bot.server_settings[message.guild.id]["profanities"]
        if bad_words:
            vulgar = False
            profanity.load_censor_words(bad_words)
            for word in bad_words:
                if (
                    profanity.contains_profanity(message.content)
                    or word in message.content
                ):
                    try:
                        await message.delete()
                        vulgar = True  # Lets try to DM them
                    except Exception:  # We tried...
                        pass
            if vulgar:
                await message.author.send(
                    f"Your message `{message.content}` was removed in **{message.guild.name}** for containing a filtered word."
                )

    @commands.Cog.listener()
    @decorators.wait_until_ready()
    @decorators.event_check(lambda s, b, a: a.guild and not a.author.bot)
    async def on_message_edit(self, before, after):
        if after.author.id in self.bot.constants.owners:
            return  # We are immune!
        if after.author.guild_permissions.manage_messages:
            return  # We are immune!
        if self.bot.dregex.search(after.content):
            removeinvitelinks = self.bot.server_settings[after.guild.id]["antiinvite"]
            if removeinvitelinks:
                try:
                    await after.delete()
                    await after.channel.send("No invite links allowed", delete_after=7)
                except Exception:
                    pass

        bad_words = self.bot.server_settings[after.guild.id]["profanities"]
        if bad_words:
            vulgar = False
            profanity.load_censor_words(bad_words)
            for word in bad_words:
                if profanity.contains_profanity(after.content) or word in after.content:
                    try:
                        await after.delete()
                        vulgar = True  # Lets try to DM them
                    except Exception:  # We tried...
                        pass
            if vulgar:
                await after.author.send(
                    f"Your message `{after.content}` was removed in **{after.guild.name}** for containing a filtered word."
                )
