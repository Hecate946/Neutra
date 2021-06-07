import io
import typing
import asyncpg
import discord
import itertools

from collections import defaultdict
from discord.ext import commands

from utilities import checks
from utilities import helpers
from utilities import converters
from utilities import formatting
from utilities import decorators


def setup(bot):
    bot.add_cog(Config(bot))


class Config(commands.Cog):
    """
    Configure the permission system.
    """

    def __init__(self, bot):
        # Initialize from the DB
        bot.loop.create_task(self.load_plonks())
        bot.loop.create_task(self.load_command_config())

        self.bot = bot
        self.ignored = defaultdict(list)  # List of ignored entities
        self.command_config = defaultdict(list)  # list of ignored commands

    async def load_command_config(self):
        query = """
                SELECT entity_id, ARRAY_AGG(command) AS commands
                FROM command_config GROUP BY entity_id;
                """
        records = await self.bot.cxn.fetch(query)
        if records:
            [
                self.command_config[record["entity_id"]].extend(record["commands"])
                for record in records
            ]

    async def load_plonks(self):
        query = """
                SELECT server_id, ARRAY_AGG(entity_id) AS entities
                FROM plonks GROUP BY server_id;
                """
        records = await self.bot.cxn.fetch(query)
        if records:
            [
                self.ignored[record["server_id"]].extend(record["entities"])
                for record in records
            ]

    async def bot_check_once(self, ctx):
        # Reasons for bypassing
        if ctx.guild is None:
            return True  # Do not restrict in DMs.

        if checks.is_admin(ctx):
            return True  # Contibutors are immune.

        if isinstance(ctx.author, discord.Member):
            if ctx.author.guild_permissions.manage_guild:
                return True  # Manage guild is immune.

        # Now check channels, roles, and users.
        if ctx.channel.id in self.ignored[ctx.guild.id]:
            return False  # Channel is ignored.

        if ctx.author.id in self.ignored[ctx.guild.id]:
            return False  # User is ignored.

        if any(
            (role_id in self.ignored[ctx.guild.id] for role_id in ctx.author._roles)
        ):
            return False  # Role is ignored.

        return True  # Ok just in case we get here...

    async def bot_check(self, ctx):
        if ctx.guild is None:
            return True  # Do not restrict in DMs.

        if checks.is_admin(ctx):
            return True  # Bot devs are immune.

        if isinstance(ctx.author, discord.Member):
            if ctx.author.guild_permissions.manage_guild:
                return True  # Manage guild is immune.

        if str(ctx.command) in self.command_config[ctx.guild.id]:
            return False  # Disabled for the whole server.

        if str(ctx.command) in self.command_config[ctx.channel.id]:
            return False  # Disabled for the channel

        if str(ctx.command) in self.command_config[ctx.author.id]:
            return False  # Disabled for the user

        if any(
            (
                str(ctx.command) in self.command_config[role_id]
                for role_id in ctx.author._roles
            )
        ):
            return False  # Disabled for the role

        return True  # Ok just in case we get here...

    async def ignore_entities(self, ctx, entities):
        failed = []
        success = []
        query = """
                INSERT INTO plonks (server_id, entity_id)
                VALUES ($1, $2)
                """
        async with self.bot.cxn.acquire() as conn:
            async with conn.transaction():
                for entity in entities:
                    try:
                        await self.bot.cxn.execute(query, ctx.guild.id, entity.id)
                    except asyncpg.exceptions.UniqueViolationError:
                        failed.append((str(entity), "Entity is already being ignored"))
                        continue
                    except Exception as e:
                        failed.append((str(entity), e))
                        continue
                    else:
                        success.append(str(entity))
                        self.ignored[ctx.guild.id].append(entity.id)
        if success:
            await ctx.success(
                f"Ignored entit{'y' if len(success) == 1 else 'ies'} `{', '.join(success)}`"
            )
        if failed:
            await helpers.error_info(ctx, failed, option="Entity")

    @decorators.group(
        invoke_without_command=True,
        case_insensitive=True,
        aliases=["restrict", "plonk"],
        brief="Ignore channels, roles, and users.",
        implemented="2021-06-06 07:30:24.673270",
        updated="2021-06-06 07:30:24.673270",
        examples="""
                {0}ignore Hecate general @Helper
                {0}restrict #chatting @member
                {0}plonk #images Hecate#3523
                """,
    )
    @checks.has_perms(manage_guild=True)
    async def ignore(self, ctx, *entities: converters.ChannelOrRoleOrMember):
        """
        Usage: {0}ignore [entities...]
        Aliases: {0}restrict, {0}plonk
        Permission: Manage Server
        Output:
            Prevents commands from being
            run in channels, by users, or
            by any user with a given role.
        Notes:
            Users with Manage Server can still use the bot,
            regardless of whether or not they've been ignored.
            Use {0}ignore all as a shorthand to ignore everyone.
        Explanation:
            If channels are passed, no commands will
            be available to users inside that channel
            If roles are passed, any user with that
            role will not be able to execute commands
            in all channels in the server.
            If a user is passed, they will not be able
            to run any commands inside of the server.
        Subcommands:
            {0}ignore list # List all the ignored entities.
            {0}ignore all # Shortcut for {0}ignore @everyone.
            {0}ignore clear # Unignore all entities.
        """
        await ctx.trigger_typing()
        await self.ignore_entities(ctx, entities)

    @ignore.command(name="list")
    @commands.cooldown(2.0, 30.0, commands.BucketType.guild)
    async def ignore_list(self, ctx, dm: converters.Flag = None):
        """
        Usage: {0}ignore list
        Permission Manage Server
        Output:
            Shows all ignored users,
            roles, and channels in the server
        """
        await ctx.trigger_typing()
        query = """
                SELECT entity_id
                FROM plonks
                WHERE server_id = $1;
                """
        records = await self.bot.cxn.fetch(query, ctx.guild.id)
        if not records:
            return await ctx.success("No entities are being ignored.")

        table = formatting.TabularData()
        channels = []
        roles = []
        users = []
        for record in records:
            try:
                entity = await converters.ChannelOrRoleOrMember().convert(
                    ctx, str(record["entity_id"])
                )
            except Exception as e:  # Couldn't convert, ignore it.
                continue
            else:
                if isinstance(entity, discord.TextChannel):
                    channels.append(entity)
                elif isinstance(entity, discord.Role):
                    roles.append(entity)
                elif isinstance(entity, discord.Member):
                    users.append(entity)
                else:  # No longer a role, channel, or member so ignore.
                    pass
        table.set_columns(["CHANNELS", "ROLES", "USERS"])
        rows = list(itertools.zip_longest(channels, roles, users, fillvalue=""))
        table.add_rows(rows)
        render = table.render()
        completed = f"```sml\n{render}```"
        title = (
            f"{self.bot.emote_dict['info']} **Ignored Entities in {ctx.guild.name}**"
        )
        if (len(completed) + len(title)) < 2000:
            content = title + completed
            file = None
        else:
            fp = io.BytesIO(completed.encode("utf-8"))
            content = title
            file = discord.File(fp, "ignored.sml")
        if dm:
            await ctx.dm(content, file=file)
        else:
            await ctx.send_or_reply(content, file=file)

    @ignore.command(name="all", brief="Ignore all server users.")
    async def _all(self, ctx):
        """
        Usage: {0}ignore all
        Permission: Manage Server
        Output:
            Ignores every single user in the server
            without the Manage Server permission
        Notes:
            Shortcut for {0}ignore @everyone
            Useful for not mentioning @everyone
        """
        await ctx.trigger_typing()
        await self.ignore_entities(ctx, [ctx.guild.default_role])

    @ignore.command(name="clear")
    @checks.has_perms(manage_guild=True)
    async def ignore_clear(self, ctx):
        """
        Usage: {0}ignore clear
        Permission: Manage Server
        Output:
            Removes all entities from the
            ignored list of objects.
        """
        await ctx.trigger_typing()
        query = "DELETE FROM plonks WHERE server_id = $1;"
        await self.bot.cxn.execute(query, ctx.guild.id)
        self.ignored[ctx.guild.id].clear()
        await ctx.success("Cleared the server's ignore list.")

    @decorators.group(
        aliases=["unplonk", "unrestrict"],
        brief="Unignore channels, users, and roles.",
        invoke_without_command=True,
        case_insensitive=True,
        implemented="2021-06-06 07:30:24.673270",
        updated="2021-06-06 07:30:24.673270",
        examples="""
                {0}unignore Hecate general @Helper
                {0}unrestrict #chatting @member
                {0}unplonk #images Hecate#3523
                """,
    )
    @checks.has_perms(manage_guild=True)
    async def unignore(self, ctx, *entities: converters.ChannelOrRoleOrMember):
        """
        Usage: {0}unignore [entities...]
        Alias: {0}unplonk, {0}unrestrict
        Permission: Manage Server
        Output:
            Allows channels, users, or roles
            to run bot commands again.
        Subcommands:
            all  # Unignore all previous entities.
        """
        await ctx.trigger_typing()
        query = """
                DELETE FROM plonks
                WHERE server_id = $1
                AND entity_id = ANY($2::BIGINT[]);
                """
        entries = [c.id for c in entities]
        await self.bot.cxn.execute(query, ctx.guild.id, entries)
        self.ignored[ctx.guild.id] = [
            x for x in self.ignored[ctx.guild.id] if x not in entries
        ]
        await ctx.success(
            f"Removed `{', '.join([str(x) for x in entities])}` from the ignored list."
        )

    @unignore.command(name="all", brief="Unignore all users, roles, and channels")
    @checks.has_perms(manage_guild=True)
    async def unignore_all(self, ctx):
        """
        Usage: {0}unignore all
        Permission: Manage Server
        Output:
            Unignores all users, roles,
            and channels that were ignored.
        Notes:
            An alias for {0}ignore clear
        """
        await ctx.invoke(self.ignore_clear)

    async def disable_command(self, ctx, entity, commands):
        query = """
                INSERT INTO command_config (server_id, entity_id, command)
                VALUES ($1, $2, $3);
                """
        failed = []
        success = []
        async with self.bot.cxn.acquire() as conn:
            async with conn.transaction():
                for command in commands:
                    try:
                        await self.bot.cxn.execute(
                            query, ctx.guild.id, entity.id, command
                        )
                    except asyncpg.exceptions.UniqueViolationError:
                        failed.append(
                            (
                                command,
                                f"Command is already disabled for entity `{entity}`",
                            )
                        )
                        continue
                    except Exception as e:
                        failed.append((command, e))
                        continue
                    else:
                        success.append(command)
                        self.command_config[entity.id].append(command)
        if success:
            await ctx.success(
                f"Disabled command{'' if len(success) == 1 else 's'} `{', '.join(success)}` for entity `{entity}`"
            )
        if failed:
            await helpers.error_info(ctx, failed, option="Command")

    async def enable_command(self, ctx, entity, commands):
        query = """
                DELETE FROM command_config
                WHERE server_id = $1
                AND entity_id = $2
                AND command = ANY($3::TEXT[]);
                """
        await self.bot.cxn.execute(query, ctx.guild.id, entity.id, commands)
        self.command_config[entity.id] = [
            x for x in self.command_config[entity.id] if x not in commands
        ]
        await ctx.success(
            f"Enabled commands `{', '.join(commands)}` for entity `{entity}`"
        )

    @decorators.group(
        case_insensitive=True,
        invoke_without_command=True,
        brief="Disable commands for users, roles, and channels.",
    )
    @commands.guild_only()
    @checks.bot_has_perms(external_emojis=True)
    @checks.has_perms(manage_guild=True)
    async def disable(
        self,
        ctx,
        entity: typing.Optional[converters.ChannelOrRoleOrMember] = None,
        *commands: converters.DiscordCommand,
    ):
        """
        Usage: {0}disable [entity] <commands>
        Permission: Manage Server
        Output:
            Prevents specific commands from being
            run in channels, by users, or
            by any user with a given role.
        Notes:
            If no 'entity' is specified, the command will
            be disabled for the whole server.
            Users with Manage Server can still use the bot,
            regardless of whether or not a command has been disabled.
            Use {0}disable all as a shorthand to disable all commands.
        Explanation:
            If channels are passed, any commands passed
            will not be available to users inside that channel.
            If roles are passed, any user with that
            role will not be able to execute the passed
            commands in all channels in the server.
            If a user is passed, they will not be able
            to run any passed commands inside of the server.
        Subcommands:
            {0}disable list # List all the disabled commands.
            {0}disable clear # Unignore all entities.
        """
        if not len(commands):
            return await ctx.usage()
        if entity is None:
            entity = ctx.guild
        await ctx.trigger_typing()
        await self.disable_command(ctx, entity, [str(c) for c in commands])

    @disable.command(
        name="list", brief="Show all the disabled channels, roles, and users."
    )
    async def disable_list(
        self,
        ctx,
        option: converters.ChannelOrRoleOrMemberOption = None,
        dm: converters.Flag = None,
    ):
        """
        Usage: {0}disable list [entity] [dm]
        Permission: Manage Server

        """
        await ctx.trigger_typing()
        query = """
                SELECT entity_id,
                ARRAY_AGG(command) as commands
                FROM command_config
                WHERE server_id = $1
                GROUP BY entity_id;
                """
        records = await self.bot.cxn.fetch(query, ctx.guild.id)
        if not records:
            return await ctx.success("No commands are disabled.")

        if option == "channels":
            columns, rows, title = await self.do_channel_option(ctx, records)

        elif option == "roles":
            columns, rows, title = await self.do_role_option(ctx, records)

        elif option == "users":
            columns, rows, title = await self.do_user_option(ctx, records)

        elif option == "servers":
            columns, rows, title = await self.do_server_option(ctx, records)

        else:
            return await self.do_hastebin(ctx, records)

        table = formatting.TabularData()
        table.set_columns(columns)
        table.add_rows(rows)
        render = table.render()
        completed = f"```sml\n{render}```"

        if (len(completed) + len(title)) < 2000:
            content = title + completed
            file = None
        else:
            fp = io.BytesIO(completed.encode("utf-8"))
            content = title
            file = discord.File(fp, "disabled_channels.sml")
        if dm:
            await ctx.dm(content, file=file)
        else:
            await ctx.send_or_reply(content, file=file)

    @disable.command(name="clear")
    @commands.cooldown(2.0, 60, commands.BucketType.guild)
    async def disable_clear(self, ctx):
        """
        Usage: {0}disable clear
        Permission: Manage Server
        Output:
            Enables all the disabled commands
            for channels, roles and users.
        """
        await ctx.trigger_typing()
        query = "DELETE FROM command_config WHERE server_id = $1;"
        await self.bot.cxn.execute(query, ctx.guild.id)
        await self.load_command_config()
        await ctx.success("Cleared the server's disabled command list.")

    @decorators.group(
        case_insensitive=True,
        invoke_without_command=True,
        brief="Enable commands for users, roles, and channels.",
    )
    @commands.guild_only()
    @checks.bot_has_perms(external_emojis=True)
    @checks.has_perms(manage_guild=True)
    async def enable(
        self,
        ctx,
        entity: typing.Optional[converters.ChannelOrRoleOrMember] = None,
        *commands: converters.DiscordCommand,
    ):
        """
        Usage: {0}enable [entity] <commands...>
        Permission: Manage Server
        Output:
            Prevents specific commands from being
            run in channels, by users, or
            by any user with a given role.
        Notes:
            If no 'entity' is specified, the command will
            be enabled across the whole server.
            Users with Manage Server can still use the bot,
            regardless of whether or not a command has been disabled.
            Use {0}disable all as a shorthand to disable all commands.
        Explanation:
            If channels are passed, any commands passed
            will not be available to users inside that channel.
            If roles are passed, any user with that
            role will not be able to execute the passed
            commands in all channels in the server.
            If a user is passed, they will not be able
            to run any passed commands inside of the server.
        Subcommands:
            {0}disable list # List all the disabled commands.
            {0}disable clear # Unignore all entities.
        """
        if not len(commands):
            return await ctx.usage()
        await ctx.trigger_typing()
        if entity is None:
            entity = ctx.guild
        await self.enable_command(ctx, entity, [str(c) for c in commands])

    @enable.command()
    @commands.cooldown(2.0, 60, commands.BucketType.guild)
    async def enable_all(self, ctx):
        """
        Usage: {0}enable all
        Permission: Manage Server
        Output:
            Enables all the disabled commands
            for channels, roles and users.
        Notes:
            Alias for {0}disable clear
        """
        await ctx.invoke(self.disable_clear)

    ######################
    ## Helper Functions ##
    ######################

    async def do_channel_option(self, ctx, records):
        command_dict = {}
        for record in records:
            try:
                channel = await commands.TextChannelConverter().convert(
                    ctx, str(record["entity_id"])
                )
            except commands.ChannelNotFound:  # Couldn't convert, ignore it.
                continue
            command_dict[channel] = record["commands"]
        if not command_dict:
            raise commands.BadArgument("No channels currently have disabled commands.")
        else:
            title = f"{self.bot.emote_dict['info']} **Disabled commands for channels in {ctx.guild.name}**"
            rows = list(itertools.zip_longest(*command_dict.values(), fillvalue=""))
            columns = [chan.name for chan in command_dict.keys()]
            return (columns, rows, title)

    async def do_role_option(self, ctx, records):
        command_dict = {}
        for record in records:
            try:
                role = await converters.DiscordRole().convert(
                    ctx, str(record["entity_id"])
                )
            except Exception:  # Couldn't convert, ignore it.
                continue
            command_dict[role] = record["commands"]
        if not command_dict:
            raise commands.BadArgument("No roles currently have disabled commands.")
        else:
            title = f"{self.bot.emote_dict['info']} **Disabled commands for roles in {ctx.guild.name}**"
            rows = list(itertools.zip_longest(*command_dict.values(), fillvalue=""))
            columns = [role.name for role in command_dict.keys()]
            return (columns, rows, title)

    async def do_user_option(self, ctx, records):
        command_dict = {}
        for record in records:
            try:
                user = await converters.DiscordMember().convert(
                    ctx, str(record["entity_id"])
                )
            except Exception:  # Couldn't convert, ignore it.
                continue
            command_dict[user] = record["commands"]

        if not command_dict:
            raise commands.BadArgument("No users currently have disabled commands.")
        else:
            title = f"{self.bot.emote_dict['info']} **Disabled commands for users in {ctx.guild.name}**"
            rows = list(itertools.zip_longest(*command_dict.values(), fillvalue=""))
            columns = [str(user) for user in command_dict.keys()]
            return (columns, rows, title)

    async def do_server_option(self, ctx, records):
        command_list = []
        for record in records:
            guild = self.bot.get_guild(record["entity_id"])
            if not guild:
                raise commands.BadArgument("No globally disabled commands.")
            command_list.extend(record["commands"])

        if not command_list:
            raise commands.BadArgument("No globally disabled commands.")
        else:
            title = f"{self.bot.emote_dict['info']} **Disabled commands for {ctx.guild.name}**"
            return (["COMMANDS"], [command_list], title)

    async def do_hastebin(self, ctx, records):
        data = []
        try:
            columns, rows, title = await self.do_user_option(ctx, records)
        except Exception:
            user_data = ""
        else:
            table = formatting.TabularData()
            table.set_columns(columns)
            table.add_rows(rows)
            user_data = f"COMMANDS DISABLED FOR USERS\n{table.render()}"
            data.append(user_data)
        try:
            columns, rows, title = await self.do_role_option(ctx, records)
        except Exception:
            role_data = ""
        else:
            table = formatting.TabularData()
            table.set_columns(columns)
            table.add_rows(rows)
            role_data = f"COMMANDS DISABLED FOR ROLES\n{table.render()}"
            data.append(role_data)
        try:
            columns, rows, title = await self.do_channel_option(ctx, records)
        except Exception:
            channel_data = ""
        else:
            table = formatting.TabularData()
            table.set_columns(columns)
            table.add_rows(rows)
            channel_data = f"COMMANDS DISABLED FOR CHANNELS\n{table.render()}"
            data.append(channel_data)
        try:
            columns, rows, title = await self.do_server_option(ctx, records)
        except Exception:
            server_data = ""
        else:
            table = formatting.TabularData()
            table.set_columns(columns)
            table.add_rows(rows)
            server_data = f"COMMANDS DISABLED GLOBALLY\n{table.render()}"
            data.append(server_data)

        title = f"**{ctx.guild.name} Disabled Command Data:**"
        data = "\n\n".join(data)
        if (len(title) + len(data)) < 1000:
            await ctx.success(f"{title}```sml\n{data}```")
            return

        async with self.bot.session.post(
            "https://hastebin.com/documents", data=data
        ) as resp:
            if resp.status != 200:
                return await ctx.fail(
                    "Failed to post to hastebin. Please try again later."
                )
            else:
                js = await resp.json()
                value = f'{title}\nhttps://hastebin.com/{js["key"]}.txt'
                await ctx.success(value)

    @decorators.command(
        brief="Show ignored roles, users, and channels."
    )
    @checks.has_perms(manage_guild=True)
    async def ignored(self, ctx, dm: converters.Flag = None):
        """
        Usage: {0}ignored
        Permission Manage Server
        Output:
            Shows all ignored users,
            roles, and channels in the server
        """
        await ctx.invoke(self.ignore_list, dm=dm)

    @decorators.command(
        brief="Show disabled commands."
    )
    @checks.has_perms(manage_guild=True)
    async def disabled(self, ctx, option: converters.ChannelOrRoleOrMemberOption = None, dm: converters.Flag = None):
        """
        Usage: {0}disabled
        Permission Manage Server
        Output:
            Shows all disabled commands
            and under what conditions
            they're disabled.
        """
        await ctx.invoke(self.disable_list, option, dm)