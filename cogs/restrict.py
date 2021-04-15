import discord
from discord.ext import commands

from utilities import pagination, permissions
from .help import COG_EXCEPTIONS, COMMAND_EXCEPTIONS, USELESS_COGS


def setup(bot):
    bot.add_cog(Restrict(bot))


class Restrict(commands.Cog):
    """
    Module for disabling commands
    """

    def __init__(self, bot):
        self.bot = bot
        self.emote_dict = bot.emote_dict

        self.exceptions = []

    # This is a server admin only cog
    async def cog_check(self, ctx):
        if not ctx.guild:
            raise commands.NoPrivateMessage()
        if (
            ctx.author.id in self.bot.constants.admins
            or ctx.author.id in self.bot.constants.owners
        ):
            return True
        return
        # elif ctx.author.guild_permissions.manage_guild:
        #     return True
        # else:
        #     perm_list = ["Manage Server"]
        #     raise commands.BadArgument(
        #         message=f"You are missing the following permission{'' if len(perm_list) == 1 else 's'}: `{', '.join(perm_list)}`"
        #     )

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

    @commands.command(brief="React on disabled commands.")
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
        await ctx.send(msg)

    # @commands.command(brief="Toggle if admins can use disabled commands")
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
    #     await ctx.send(msg)

    @commands.command(brief="Disable a command.")
    async def disable(self, ctx, *, command_or_cog_name=None):
        """Disables the passed command or all commands in the passed cog (owner only).  Command and cog names are case-sensitive."""

        if command_or_cog_name is None:
            return await ctx.send(
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

    @commands.command(brief="Enable a command.")
    async def enable(self, ctx, *, command_or_cog_name=None):
        """Enables the passed command or all commands in the passed cog (admin-only).  Command and cog names are case-sensitive."""

        if command_or_cog_name == None:
            return await ctx.send(
                "Usage: `{}enable [command_or_cog_name]`".format(ctx.prefix)
            )
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

    @commands.command(brief="List disabled commands.")
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

    @commands.command(brief="Show the status of a command.")
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

    @commands.command(brief="Disable all commands.")
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

    @commands.command(brief="Enable all commands")
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
            return await ctx.send(
                f"{self.bot.emote_dict['success']} All commands already enabled."
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

    @commands.command(brief="Disallow users from using the bot.")
    @permissions.has_permissions(administrator=True)
    async def ignore(self, ctx, user: discord.Member = None, react: str = ""):
        """
        Usage: -ignore <user> [react] [reason]
        Output: Will not process commands from the passed user.
        Permission: Administrator
        Notes:
            Specify the "react" to choose whether or not to
            react to the user's attempted commands.
        """

        if user is None:
            return await ctx.send(reference=self.bot.rep_ref(ctx), content=f"Usage: `{ctx.prefix}ignore <user> [react]`")

        if user.guild_permissions.administrator:
            return await ctx.send(
                f"{self.emote_dict['failed']} You cannot punish other staff members"
            )
        if user.id in self.bot.constants.owners:
            return await ctx.send(
                f"{self.emote_dict['failed']} You cannot punish my creator."
            )
        if user.top_role.position > ctx.author.top_role.position:
            return await ctx.send(
                f"{self.emote_dict['failed']} User `{user}` is higher in the role hierarchy than you."
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
            return await ctx.send(
                f"{self.emote_dict['error']} User `{user}` is already being ignored."
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

        await ctx.send(reference=self.bot.rep_ref(ctx), content=f"{self.emote_dict['success']} Ignored `{user}`")

    @commands.command(brief="Reallow users to use the bot.", aliases=["listen"])
    @commands.guild_only()
    @permissions.has_permissions(administrator=True)
    async def unignore(self, ctx, user: discord.Member = None):
        """
        Usage: -unignore <user>
        Alias: -listen
        Output: Will delete the passed user from the ignored list
        Permission: Administrator
        """

        if user is None:
            return await ctx.send(reference=self.bot.rep_ref(ctx), content=f"Usage: `{ctx.prefix}unignore <user>`")

        query = """SELECT user_id FROM ignored WHERE user_id = $1 AND server_id = $2"""
        blacklisted = await self.bot.cxn.fetchval(query, user.id, ctx.guild.id) or None
        if blacklisted is None:
            return await ctx.send(reference=self.bot.rep_ref(ctx), content=f"{self.emote_dict['error']} User was not ignored.")

        query = """DELETE FROM ignored WHERE user_id = $1 AND server_id = $2"""
        await self.bot.cxn.execute(query, user.id, ctx.guild.id)

        self.bot.server_settings[ctx.guild.id]["ignored_users"].pop(user.id, None)

        await ctx.send(
            f"{self.emote_dict['success']} Removed `{user}` from the ignore list."
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
            await message.add_reaction(self.emote_dict["failed"])
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
            is_admin = permissions.is_admin(ctx)
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
