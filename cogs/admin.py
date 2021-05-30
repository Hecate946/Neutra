import io
import re
import copy
import shlex
import typing
import discord

from datetime import datetime
from datetime import timedelta
from discord.ext import commands
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
        self.exceptions = []

    def _get_our_comms(self):
        # Get our cog
        our_cog = str(self.__module__.split(".")[1]).capitalize()
        # Build a list of commands
        our_comm_list = [c.name for c in self.bot.get_cog(our_cog).get_commands()]
        # Add our cog name to the list
        our_comm_list.append(our_cog)
        return our_comm_list

    def _get_commands(self, check):
        # Check Cogs first
        cog = self._get_cog_commands(check)
        if cog:
            return cog
        # Check for commands
        return self._get_command(check)

    def _get_command(self, command):
        # Returns the command in a list if it exists
        # excludes hidden commands
        for cog in self.bot.cogs:
            if cog in self.exceptions:
                # Skip exceptions
                continue
            for c in self.bot.get_cog(cog).get_commands():
                if c.name == command:
                    if c.hidden or c in self.exceptions:
                        return None
                    return [c.name]
        return None

    def _get_cog_commands(self, cog):
        # Returns a list of commands associated with the passed cog
        # excludes hidden commands
        if not cog in self.bot.cogs:
            return None
        if cog in self.exceptions:
            return None
        command_list = []
        for c in self.bot.get_cog(cog).get_commands():
            if not c.hidden and not c in self.exceptions:
                command_list.append(c.name)
        return command_list

    def _get_all_commands(self):
        # Returns a list of all commands - excludes hidden commands
        command_list = []
        for cog in self.bot.cogs:
            if cog in self.exceptions:
                continue
            for c in self.bot.get_cog(cog).get_commands():
                if not c.hidden and not c in self.exceptions:
                    command_list.append(c.name)
        return command_list

    @decorators.command(brief="React on disabled commands.")
    @checks.has_perms(manage_guild=True)
    async def disabledreact(self, ctx, *, yes_no=None):
        """Sets whether the bot reacts to disabled commands when attempted (admin-only)."""
        query = """SELECT react FROM servers WHERE server_id = $1"""
        current = await self.bot.cxn.fetchval(query, ctx.guild.id)
        if current is True:
            react = True
        else:
            react = False
        if yes_no is None:
            # Output current setting
            msg = "{} currently *{}*.".format(
                "Reacting on disabled commands",
                "enabled" if current is True else "disabled",
            )
        elif yes_no.lower() in ["yes", "on", "true", "enabled", "enable"]:
            yes_no = True
            react = True
            msg = "{} {} *enabled*.".format(
                "Reacting on disabled commands",
                "remains" if current is True else "is now",
            )
        elif yes_no.lower() in ["no", "off", "false", "disabled", "disable"]:
            yes_no = False
            react = False
            msg = "{} {} *disabled*.".format(
                "Reacting on disabled commands",
                "is now" if current is True else "remains",
            )
        else:
            msg = "That is not a valid setting."
            yes_no = current
        if yes_no != current and yes_no is not None:
            self.bot.server_settings[ctx.guild.id]["react"] = react
            await self.bot.cxn.execute(
                "UPDATE servers SET react = $1 WHERE server_id = $2",
                react,
                ctx.guild.id,
            )
        await ctx.send_or_reply(msg)

    # @decorators.command(brief="Toggle if admins can use disabled commands")
    # async def adminallow(self, ctx, *, yes_no = None):
    #     """Sets whether admins can access disabled commands (admin-only)."""
    #     query = '''SELECT admin_allow FROM servers WHERE server_id = $1'''
    #     current = await self.bot.cxn.fetchval(query, ctx.guild.id)
    #     if current is True:
    #         admin_allow = True
    #     else:
    #         admin_allow = False
    #     if yes_no is None:
    #         # Output current setting
    #         msg =  "{} currently *{}*.".format("Admin allow on disabled commands","enabled" if current is True else "disabled")
    #     elif yes_no.lower() in [ "yes", "on", "true", "enabled", "enable" ]:
    #         yes_no = True
    #         admin_allow = True
    #         msg = "{} {} *enabled*.".format("Admin allow on disabled commands","remains" if current is True else "is now")
    #     elif yes_no.lower() in [ "no", "off", "false", "disabled", "disable" ]:
    #         yes_no = False
    #         admin_allow = False
    #         msg = "{} {} *disabled*.".format("Admin allow on disabled commands","is now" if current is True else "remains")
    #     else:
    #         msg = "That is not a valid setting."
    #         yes_no = current
    #     if yes_no != current and yes_no is not None:
    #         self.bot.server_settings[ctx.guild.id]['admin_allow'] = admin_allow
    #         await self.bot.cxn.execute("UPDATE settings SET admin_allow = $1", admin_allow)
    #     await ctx.send_or_reply(msg)

    @decorators.command(brief="Disable a command.")
    @checks.has_perms(manage_guild=True)
    async def disable(self, ctx, *, command_or_cog_name=None):
        """Disables the passed command or all commands in the passed cog (owner only).  Command and cog names are case-sensitive."""

        if command_or_cog_name is None:
            return await ctx.send_or_reply(
                ": `{}disable [command_or_cog_name]`".format(ctx.prefix)
            )
        # Make sure we're not trying to block anything in this cog
        if command_or_cog_name in self._get_our_comms():
            msg = "You can't disable any commands from this cog."
            return await pagination.EmbedText(
                desc_head="```fix",
                desc_foot="```",
                color=self.bot.constants.embed,
                description=msg,
                title="Disable Commands",
            ).send(ctx)
        # At this point - we should check if we have a command
        comm = self._get_commands(command_or_cog_name)
        if comm is None:
            msg = '"{}" is not a cog or command name that is eligible for this system.'.format(
                command_or_cog_name
            )
            return await pagination.EmbedText(
                desc_head="```fix",
                desc_foot="```",
                color=self.bot.constants.embed,
                description=msg,
                title="Disable Commands",
            ).send(ctx)
        # Build a list of the commands we disable
        disabled = []
        dis_com = self.bot.server_settings[ctx.guild.id]["disabled_commands"]
        for c in comm:
            if not c in dis_com:
                dis_com.append(c)
                disabled.append(c)

        if len(disabled):
            await self.bot.cxn.execute(
                """UPDATE servers SET disabled_commands = $1 WHERE server_id = $2;""",
                ",".join([x for x in dis_com]),
                ctx.guild.id,
            )

        # Now we give some output
        msg = (
            "All eligible passed commands are already disabled."
            if len(disabled) == 0
            else ", ".join(sorted(disabled))
        )
        title = (
            "Disabled 1 Command"
            if len(disabled) == 1
            else "Disabled {} Commands".format(len(disabled))
        )
        await pagination.EmbedText(
            desc_head="```fix",
            desc_foot="```",
            color=self.bot.constants.embed,
            description=msg,
            title=title,
        ).send(ctx)

    @decorators.command(brief="Enable a command.")
    @checks.has_perms(manage_guild=True)
    async def enable(self, ctx, *, command_or_cog_name=None):
        """Enables the passed command or all commands in the passed cog (admin-only).  Command and cog names are case-sensitive."""

        if command_or_cog_name == None:
            return await ctx.usage("[command_or_cog_name]")
        # We should check if we have a command
        comm = self._get_commands(command_or_cog_name)
        if comm == None:
            msg = '"{}" is not a cog or command name that is eligible for this system.'.format(
                command_or_cog_name
            )
            return await pagination.EmbedText(
                desc_head="```fix",
                desc_foot="```",
                color=self.bot.constants.embed,
                description=msg,
                title="Enable Commands",
            ).send(ctx)
        # Build a list of the commands we disable
        enabled = []
        dis_com = self.bot.server_settings[ctx.guild.id]["disabled_commands"]
        dis_copy = []
        for c in dis_com:
            if not c in comm:
                # Not in our list - keep it disabled
                dis_copy.append(c)
            else:
                # In our list - add it to the enabled list
                enabled.append(c)
        if len(enabled):
            # We actually made changes - update the setting
            await self.bot.cxn.execute(
                """UPDATE servers SET disabled_commands = $1 WHERE server_id = $2;""",
                ",".join([x for x in dis_copy]),
                ctx.guild.id,
            )
            self.bot.server_settings[ctx.guild.id]["disabled_commands"] = dis_copy
        # Now we give some output
        msg = (
            "All eligible passed commands are already enabled."
            if len(enabled) == 0
            else ", ".join(sorted(enabled))
        )
        title = (
            "Enabled 1 Command"
            if len(enabled) == 1
            else "Enabled {} Commands".format(len(enabled))
        )
        await pagination.EmbedText(
            desc_head="```fix",
            desc_foot="```",
            color=self.bot.constants.embed,
            description=msg,
            title=title,
        ).send(ctx)

    @decorators.command(brief="List disabled commands.")
    @checks.has_perms(manage_guild=True)
    async def listdisabled(self, ctx):
        """Lists all disabled commands (admin-only)."""
        dis_com = self.bot.server_settings[ctx.guild.id]["disabled_commands"]
        msg = (
            "No commands have been disabled."
            if len(dis_com) == 0
            else ", ".join(sorted(dis_com))
        )
        title = (
            "1 Disabled Command"
            if len(dis_com) == 1
            else "{} Disabled Commands".format(len(dis_com))
        )
        await pagination.EmbedText(
            desc_head="```fix",
            desc_foot="```",
            color=self.bot.constants.embed,
            description=msg,
            title=title,
        ).send(ctx)

    @decorators.command(brief="Show the status of a command.")
    @checks.has_perms(manage_guild=True)
    async def isdisabled(self, ctx, *, command_or_cog_name=None):
        """Outputs whether the passed command - or all commands in a passed cog are disabled (admin-only)."""
        # Get our commands or whatever
        dis_com = self.bot.server_settings[ctx.guild.id]["disabled_commands"]
        comm = self._get_commands(command_or_cog_name)
        if comm == None:
            msg = '"{}" is not a cog or command name that is eligible for this system.'.format(
                command_or_cog_name
            )
            return await pagination.EmbedText(
                desc_head="```fix",
                desc_foot="```",
                color=self.bot.constants.embed,
                description=msg,
                title="Disabled Commands",
            ).send(ctx)
        is_cog = True if self.bot.get_cog(command_or_cog_name) else False
        # Now we check if they're all disabled
        disabled = []
        for c in dis_com:
            if c in comm:
                disabled.append(c)
        if is_cog:
            title = (
                "1 Command Disabled in {}".format(command_or_cog_name)
                if len(disabled) == 1
                else "{} Commands Disabled in {}".format(
                    len(disabled), command_or_cog_name
                )
            )
            if len(disabled) == 0:
                msg = "None"
                footer = "0% disabled"
            else:
                msg = ", ".join(disabled)
                footer = "{:,g}% disabled".format(
                    round(len(disabled) / len(comm) * 100, 2)
                )
        else:
            title = "{} Command Status".format(command_or_cog_name)
            footer = None
            msg = "Disabled" if len(disabled) else "Enabled"
        await pagination.EmbedText(
            desc_head="```fix",
            desc_foot="```",
            color=self.bot.constants.embed,
            description=msg,
            title=title,
            footer=footer,
        ).send(ctx)

    @decorators.command(brief="Disable all commands.")
    @checks.has_perms(manage_guild=True)
    async def disableall(self, ctx):
        """Disables all enabled commands outside this module (admin-only)."""
        # Setup our lists
        comm_list = self._get_all_commands()
        our_comm_list = self._get_our_comms()
        dis_com = self.bot.server_settings[ctx.guild.id]["disabled_commands"]
        disabled = []

        # Iterate and disable
        for c in comm_list:
            if not c in our_comm_list and not c in dis_com:
                disabled.append(c)
                dis_com.append(c)
        if len(disabled):
            # We actually made changes - update the setting
            await self.bot.cxn.execute(
                """UPDATE servers SET disabled_commands = $1 WHERE server_id = $2;""",
                ",".join([x for x in dis_com]),
                ctx.guild.id,
            )

        # Give some output
        msg = (
            "All eligible commands are already disabled."
            if len(disabled) == 0
            else ", ".join(sorted(disabled))
        )
        title = (
            "Disabled 1 Command"
            if len(disabled) == 1
            else "Disabled {} Commands".format(len(disabled))
        )
        await pagination.EmbedText(
            desc_head="```fix",
            desc_foot="```",
            color=self.bot.constants.embed,
            description=msg,
            title=title,
        ).send(ctx)

    @decorators.command(brief="Enable all commands")
    @checks.has_perms(administrator=True)
    async def enableall(self, ctx):
        """Enables all disabled commands (admin-only)."""
        # Setup our lists
        dis_com = self.bot.server_settings[ctx.guild.id]["disabled_commands"].copy()
        self.bot.server_settings[ctx.guild.id]["disabled_commands"] = []

        if len(dis_com):
            # We actually made changes - update the setting
            await self.bot.cxn.execute(
                """UPDATE servers SET disabled_commands = NULL WHERE server_id = $1;""",
                ctx.guild.id,
            )

        # Give some output
        if len(dis_com) == 0:
            return await ctx.send_or_reply(
                content=f"{self.bot.emote_dict['success']} All commands already enabled.",
            )
        msg = ", ".join(sorted(dis_com))
        title = (
            "Enabled 1 Command"
            if len(dis_com) == 1
            else "Enabled {} Commands".format(len(dis_com))
        )
        await pagination.EmbedText(
            description=msg,
            title=title,
            desc_head="```fix",
            desc_foot="```",
            color=self.bot.constants.embed,
        ).send(ctx)

    @decorators.command(brief="Disallow users from using the bot.")
    @checks.has_perms(manage_guild=True)
    async def ignore(self, ctx, user: converters.DiscordMember = None, react: str = ""):
        """
        Usage: {0}ignore <user> [react] [reason]
        Output: Will not process commands from the passed user.
        Permission: Administrator
        Notes:
            Specify the "react" to choose whether or not to
            react to the user's attempted commands.
        """

        if user is None:
            return await ctx.usage("<user> [react]")

        if user.guild_permissions.administrator:
            return await ctx.send_or_reply(
                content=f"{self.bot.emote_dict['failed']} You cannot punish other staff members",
            )
        if user.id in self.bot.constants.owners:
            return await ctx.send_or_reply(
                content=f"{self.bot.emote_dict['failed']} You cannot punish my creator.",
            )
        if user.top_role.position > ctx.author.top_role.position:
            return await ctx.send_or_reply(
                content=f"{self.bot.emote_dict['failed']} User `{user}` is higher in the role hierarchy than you.",
            )

        if react is None:
            react = False

        if react.upper() == "REACT":
            react = True
        else:
            react = False

        query = (
            """SELECT server_id FROM ignored WHERE user_id = $1 AND server_id = $2"""
        )
        already_ignored = (
            await self.bot.cxn.fetchval(query, user.id, ctx.guild.id) or None
        )

        if already_ignored is not None:
            return await ctx.send_or_reply(
                content=f"{self.bot.emote_dict['warn']} User `{user}` is already being ignored.",
            )

        query = """INSERT INTO ignored VALUES ($1, $2, $3, $4, $5)"""
        await self.bot.cxn.execute(
            query,
            ctx.guild.id,
            user.id,
            ctx.author.id,
            react,
            ctx.message.created_at.utcnow(),
        )

        self.bot.server_settings[ctx.guild.id]["ignored_users"][user.id] = react

        await ctx.send_or_reply(
            content=f"{self.bot.emote_dict['success']} Ignored `{user}`",
        )

    @decorators.command(
        aliases=["listen"],
        brief="Reallow users to use the bot.",
        permissions=["manage_guild"],
        updated="2021-05-05 19:48:06.478774",
    )
    @commands.guild_only()
    @checks.has_perms(manage_guild=True)
    async def unignore(self, ctx, user: converters.DiscordMember = None):
        """
        Usage: {0}unignore <user>
        Alias: {0}listen
        Permission: Manage Server
        Output:
            Will delete the passed user
            from the bots ignored list
            and once again respond to
            commands executed by the user
        """

        if user is None:
            return await ctx.usage("<user>")

        query = """SELECT user_id FROM ignored WHERE user_id = $1 AND server_id = $2"""
        blacklisted = await self.bot.cxn.fetchval(query, user.id, ctx.guild.id) or None
        if blacklisted is None:
            return await ctx.send_or_reply(
                content=f"{self.bot.emote_dict['warn']} User was not ignored.",
            )

        query = """DELETE FROM ignored WHERE user_id = $1 AND server_id = $2"""
        await self.bot.cxn.execute(query, user.id, ctx.guild.id)

        self.bot.server_settings[ctx.guild.id]["ignored_users"].pop(user.id, None)

        await ctx.send_or_reply(
            f"{self.bot.emote_dict['success']} Removed `{user}` from the ignore list."
        )

    async def message(self, message):
        # Check the message and see if we should allow it
        ctx = await self.bot.get_context(message)
        # never against the owners
        if message.author.id in self.bot.constants.owners:
            return

        if not ctx.command:
            # No command - no need to check
            return

        try:
            react = self.bot.server_settings[message.guild.id]["ignored_users"][
                message.author.id
            ]
        except KeyError:
            # This means they aren't in the dict of ignored users.
            return

        if react is True:
            await message.add_reaction(self.bot.emote_dict["failed"])
        # We have an ignored user
        return {"Ignore": True, "Delete": False}

    async def message(self, message):
        # Check the message and see if we should allow it
        ctx = await self.bot.get_context(message)
        if not ctx.command:
            # No command - no need to check
            return
        # Get the list of blocked commands
        dis_com = self.bot.server_settings[message.guild.id]["disabled_commands"]
        if ctx.command.name in dis_com:
            # Check if we're going to override
            admin_allow = self.bot.server_settings[message.guild.id]["admin_allow"]
            # Check if we're admin and bot admin
            is_admin = checks.is_admin(ctx)
            # Check if we override
            if is_admin and admin_allow is True:
                return
            # React if needed
            to_react = self.bot.server_settings[message.guild.id]["react"]
            if to_react:
                await message.add_reaction(self.bot.emote_dict["failed"])
            # We have a disabled command - ignore it
            return {"Ignore": True, "Delete": False}
        else:
            try:
                react = self.bot.server_settings[message.guild.id]["ignored_users"][
                    message.author.id
                ]
            except KeyError:
                # This means they aren't in the dict of ignored users.
                return

            if react is True:
                await message.add_reaction(self.bot.emote_dict["failed"])
            # We have an ignored user
            return {"Ignore": True, "Delete": False}

    @decorators.command(brief="Setup server muting system.", aliases=["setmuterole"])
    @commands.guild_only()
    @checks.bot_has_perms(manage_roles=True)
    @checks.has_perms(manage_guild=True)
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
        msg = await ctx.send_or_reply(
            f"{self.bot.emote_dict['warn']} Creating mute system. This process may take several minutes."
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
        aliases=["kill", "die"],
        brief="Have the bot leave the server.",
        permissions=["administrator"],
        implemented="2021-04-28 20:21:42.190256",
        updated="2021-05-05 19:43:51.209242",
    )
    @commands.guild_only()
    @checks.has_perms(manage_guild=True)
    async def leave(self, ctx):
        """
        Usage: {0}leave
        Aliases: {0}kill, {0}die
        Output:
            Clears all stored server data
            and kicks the bot from the server.
        Notes:
            You will receive confirmation, upon executing this
            command, all emoji stats, messages, last seen data
            roles, nicknames, and usernames will be deleted.
        """
        c = await ctx.confirm(
            f"{self.bot.emote_dict['delete']} **This action will remove me from this server and clear all my collected data. Do you wish to continue?**"
        )
        if c:
            await ctx.guild.leave()
            return

    @decorators.command(brief="Dehoist all server users.")
    @checks.bot_has_perms(manage_nicknames=True)
    @checks.has_perms(manage_guild=True)
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

        c = await pagination.Confirmation(
            msg=f"{self.bot.emote_dict['exclamation']} **This command will attempt to nickname all users with hoisting symbols in their names. Do you wish to continue?**"
        ).prompt(ctx)
        if c:
            hoisted = []
            for user in ctx.guild.members:
                if user.display_name.startswith(tuple(characters)):
                    hoisted.append(user)

            if len(hoisted) == 0:
                await ctx.send_or_reply(
                    content=f"{self.bot.emote_dict['exclamation']} No users to dehoist.",
                )
                return
            message = await ctx.send_or_reply(
                content=f"{self.bot.emote_dict['loading']} **Dehoisting {len(hoisted)} user{'' if len(hoisted) == 1 else 's'}...**",
            )
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
                except Exception as e:
                    failed.append(str(user))
                    print(e)
            msg = ""
            if edited:
                msg += f"{self.bot.emote_dict['success']} Dehoisted {len(edited)} user{'' if len(edited) == 1 else 's'}."
            if failed:
                msg += f"\n{self.bot.emote_dict['failed']} Failed to dehoist {len(failed)} user{'' if len(failed) == 1 else 's'}."
            await message.edit(content=msg)
        else:
            await ctx.send_or_reply(
                content=f"{self.bot.emote_dict['exclamation']} **Cancelled.**",
            )

    @decorators.command(brief="Mass nickname users with odd names.")
    @checks.bot_has_perms(manage_nicknames=True)
    @checks.has_perms(manage_guild=True)
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

        c = await pagination.Confirmation(
            msg=f"{self.bot.emote_dict['exclamation']} **This command will attempt to nickname all users with special symbols in their names. Do you wish to continue?**"
        ).prompt(ctx)
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

            message = await ctx.send_or_reply(
                content=f"{self.bot.emote_dict['loading']} **Ascifying {len(odd_names)} user{'' if len(odd_names) == 1 else 's'}...**",
            )
            edited = []
            failed = []
            for user in odd_names:
                try:
                    ascified = unidecode(user.display_name)
                    await user.edit(
                        nick=ascified, reason="Nickname changed by massascify command."
                    )
                    edited.append(user)
                except Exception as e:
                    print(e)
                    failed.append(user)
            msg = ""
            if edited:
                msg += f"{self.bot.emote_dict['success']} Ascified {len(edited)} user{'' if len(edited) == 1 else 's'}."
            if failed:
                msg += f"\n{self.bot.emote_dict['failed']} Failed to ascify {len(failed)} user{'' if len(failed) == 1 else 's'}."
            await message.edit(content=msg)
        else:
            await ctx.send_or_reply(
                content=f"{self.bot.emote_dict['exclamation']} **Cancelled.**",
            )

    @decorators.command(
        aliases=["multiban"],
        brief="Massban users matching a search.",
        botperms=["ban_members"],
        permissions=["manage_guild", "ban_members"],
        implemented="2021-05-02 04:12:14.126319",
        updated="2021-05-05 19:23:39.306805",
    )
    @commands.guild_only()
    @checks.bot_has_perms(ban_members=True)
    @checks.has_perms(manage_guild=True, ban_members=True)
    async def massban(self, ctx, *, args):
        """
        Usage: {0}massban <arguments>
        Aliases: {0}multiban
        Permissions: Manage Server, Ban Members
        Output:
            Massbans users matching searches
        Notes:
            Use -massban --help
            to show all valid arguments.
        """

        help_docstr = ""
        help_docstr += "**Valid Massban Flags:**"
        help_docstr += "```yaml\n"
        help_docstr += "Flags: [Every flag is optional.]\n"
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
        parser.add_argument("--has-role", type=int)
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
            return await ctx.send_or_reply(str(e).capitalize())

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
                    return await ctx.send_or_reply(f"Invalid regex passed to `--match`: {e}")
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
                return await ctx.send_or_reply(f"Invalid regex passed to `--regex`: {e}")
            else:
                predicates.append(lambda m, x=_regex: x.match(m.name))

        if args.no_avatar:
            predicates.append(lambda m: m.avatar is None)
        if args.no_roles:
            predicates.append(lambda m: len(getattr(m, "roles", [])) <= 1)
        if args.has_role:

            role = ctx.guild.get_role(args.has_role)
            if role is None:
                return await ctx.fail("Invalid role.")
            predicates.append(lambda m: role in m.roles)

        now = datetime.utcnow()
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
        # members.add([x for x in await p(m)])
        if len(members) == 0:
            return await ctx.send_or_reply("No members found matching criteria.")

        if args.show:
            members = sorted(members, key=lambda m: m.joined_at or now)
            fmt = "\n".join(
                f"{m.id}\tJoined: {m.joined_at}\tCreated: {m.created_at}\t{m}"
                for m in members
            )
            content = f"Current Time: {datetime.utcnow()}\nTotal members: {len(members)}\n{fmt}"
            file = discord.File(
                io.BytesIO(content.encode("utf-8")), filename="members.txt"
            )
            return await ctx.send_or_reply(file=file)

        if args.reason is None:
            return await ctx.send_or_reply("--reason flag is required.")
        else:
            reason = " ".join(args.reason)
            raw_reason = reason
            reason = await converters.ActionReason().convert(ctx, reason)

        confirm = await ctx.confirm(
            f"This action will ban {len(members)} user{'' if len(members) == 1 else 's'}."
        )
        if not confirm:
            return

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

        if banned:
            await ctx.success(f"Massbanned {len(banned)}/{len(members)} users.")
            self.bot.dispatch("mod_action", ctx, targets=banned)
        if failed:
            await helpers.error_info(ctx, failed)

    async def get_warncount(self, guild):
        query = """
                SELECT (warnings, user_id)
                FROM warn WHERE
                server_id = $1;
                """
        res = await self.bot.cxn.fetch(query, guild.id)
        results = {}
        for x in res:
            results[x[0][1]] = x[0][0]

        return results

    @decorators.group(
        name="prefix",
        invoke_without_command=True,
        case_insensitive=True,
        brief="Show all server prefixes.",
        hidden=True,
    )
    async def prefix(self, ctx):
        """
        Alias for {0}prefixes
        """
        await ctx.invoke(self.prefixes)

    @prefix.command(name="add", ignore_extra=False, hidden=True)
    @checks.has_perms(manage_guild=True)
    async def prefix_add(self, ctx, prefix: converters.Prefix = None):
        await ctx.invoke(self.addprefix, prefix)

    @prefix.command(
        name="remove", aliases=["delete", "rm", "rem"], ignore_extra=False, hidden=True
    )
    @checks.has_perms(manage_guild=True)
    async def prefix_remove(self, ctx, prefix: converters.Prefix = None):
        await ctx.invoke(self.removeprefix, prefix)

    @checks.has_perms(manage_guild=True)
    @prefix.command(name="clear", hidden=True)
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

        prefixes = self.bot.get_guild_prefixes(ctx.guild)

        # Lets remove the mentions and replace with @name
        del prefixes[0]
        del prefixes[0]
        prefixes.insert(0, f"@{ctx.guild.me.display_name}")

        await ctx.success(
            f"My current prefix{' is' if len(prefixes) == 1 else 'es are'} `{', '.join(prefixes)}`"
        )

    @checks.has_perms(manage_guild=True)
    @decorators.command(
        aliases=["createprefix"],
        brief="Add a custom server prefix.",
        permissions=["manage_guild"],
        implemented="2021-05-03 09:14:59.219515",
        updated="2021-05-05 19:23:39.306805",
    )
    async def addprefix(self, ctx, prefix: converters.Prefix = None):
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
        if prefix is None:
            return await ctx.usage("<new prefix>")

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

    @checks.has_perms(manage_guild=True)
    @decorators.command(
        aliases=["deleteprefix", "rmprefix", "remprefix", "delprefix"],
        brief="Remove a custom server prefix",
        ignore_extra=False,
        permissions=["manage_guild"],
        implemented="2021-05-03 09:14:59.219515",
        updated="2021-05-05 19:23:39.306805",
    )
    async def removeprefix(self, ctx, prefix: converters.Prefix = None):
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
        if prefix is None:
            return await ctx.usage("<current prefix>")

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

    @checks.has_perms(manage_guild=True)
    @decorators.command(
        aliases=["clearprefixes", "resetprefix", "resetprefixes"],
        brief="Clear all custom prefixes.",
        permissions=["manage_guild"],
        implemented="2021-05-03 09:14:59.219515",
        updated="2021-05-05 19:23:39.306805",
    )
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

    @decorators.command(
        aliases=["pruneinactive"],
        brief="Kick all inactive server members",
        implemented="2021-05-09 02:09:40.842333",
        updated="2021-05-09 02:09:40.842333",
        examples="""
                {0}kickinactive
                {0}kickinactive 25
                {0}kickinactive 12 @Helper
                {0}kickinactive @Verified
                {0}pruneinactive
                {0}pruneinactive 25
                {0}pruneinactive 12 @Helper
                {0}pruneinactive @Verified
                """,
    )
    @checks.bot_has_perms(kick_members=True)
    @checks.has_perms(administrator=True)
    async def kickinactive(
        self,
        ctx,
        days: typing.Optional[int] = 30,
        roles: commands.Greedy[converters.DiscordRole] = None,
    ):
        """
        Usage: {0}kickinactive [days] [roles]
        Alias: {0}pruneinactive
        Permission: Administrator
        Output:
            Searches for all users who have the
            specified roles (@everyone by default)
            who have not logged into discord over
            the specified duration (30 days default).
            The bot will then show how many inactive
            users were found, and prompt you for
            confirmation to kick the users.
        Notes:
            The bot will say no inactive
            users have been found if any
            of the given roles are above
            the bot's highest role.
            All arguments are optional.
        """
        if days > 30:
            raise commands.BadArgument("The `days` argument must be fewer than 30.")
        elif days < 1:
            raise commands.BadArgument("The `days` argument must be greater than 0.")
        to_be_pruned = await ctx.guild.estimate_pruned_members(days=days, roles=roles)
        if to_be_pruned == 0:
            return await ctx.success(
                f"Your server has no inactive users to prune within your specifications."
            )
        c = await pagination.Confirmation(
            f"**{self.bot.emote_dict['exclamation']} This action will kick {to_be_pruned} users. Do you wish to continue?**"
        ).prompt(ctx)
        if c:
            reason = await converters.ActionReason().convert(ctx, "Kick inactive users")
            await ctx.guild.prune_members(
                days=days, compute_prune_count=True, roles=roles, reason=reason
            )
        else:
            await ctx.send_or_reply(f"**{self.bot.emote_dict['exclamation']} Cancelled.**")

    @decorators.command(
        brief="Count the inactive users.",
        implemented="2021-05-10 02:59:21.229362",
        updated="2021-05-10 02:59:21.229362",
    )
    @checks.bot_has_perms(kick_members=True)
    @checks.has_perms(view_audit_log=True)
    async def checkinactive(
        self,
        ctx,
        days: typing.Optional[int] = 30,
        roles: commands.Greedy[converters.DiscordRole] = None,
    ):
        """
        Usage: {0}checkinactive [days] [roles]...
        Permission: View Audit Log
        Output:
            Searches for all users who have the
            specified roles (@everyone by default)
            who have not logged into discord over
            the specified duration (30 days default).
            The bot will then show how many inactive
            users were found if any.
        Notes:
            Run the command {0}kickinactive
            to kick the users from the server.
        """
        if days > 30:
            raise commands.BadArgument("The `days` argument must be fewer than 30.")
        elif days < 1:
            raise commands.BadArgument("The `days` argument must be greater than 0.")
        to_be_pruned = await ctx.guild.estimate_pruned_members(days=days, roles=roles)
        if to_be_pruned == 0:
            return await ctx.success(
                f"Your server has no inactive users to prune within your specifications."
            )
        await ctx.send_or_reply(
            f"{self.bot.emote_dict['graph']} Your server has {to_be_pruned} inactive users matching your specifications."
        )
