import discord
import re
from discord.ext import commands, menus, tasks
import datetime
from collections import Counter
from utilities import pagination, checks
from utilities import decorators


def setup(bot):
    bot.add_cog(Automod(bot))


class Automod(commands.Cog):
    """
    Manage the automod system.
    """

    def __init__(self, bot):
        self.bot = bot
        self.emote_dict = bot.emote_dict
        self.dregex = re.compile(
            r"(?:https?://)?discord(?:app)?\.(?:com/invite|gg)/[a-zA-Z0-9]+/?"
        )

    ###################
    ## Warn Commands ##
    ###################

    @decorators.command(brief="Warn users with an optional reason.")
    @commands.guild_only()
    @checks.has_perms(kick_members=True)
    async def warn(
        self, ctx, targets: commands.Greedy[discord.Member], *, reason: str = None
    ):
        """
        Usage: -warn [target] [target]... [reason]
        Output: Warns members and DMs them the reason they were warned for
        Permission: Kick Members
        Notes:
            Warnings do not automatically enforce punishments on members.
            They only store a record of how many instances a user has misbehaved.
        """
        if not len(targets):
            return await ctx.send_or_reply(
                content=f"Usage: `{ctx.prefix}warn <target> [target]... [reason]`",
            )
        warned = []
        for target in targets:
            if target.id in self.bot.constants.owners:
                return await ctx.send_or_reply(
                    content="You cannot warn my developer.",
                )
            if target.id == ctx.author.id:
                return await ctx.send_or_reply(
                    "I don't think you really want to warn yourself..."
                )
            if target.id == self.bot.user.id:
                return await ctx.send_or_reply(
                    content="I don't think I want to warn myself...",
                )
            if (
                target.guild_permissions.manage_messages
                and ctx.author.id not in self.bot.constants.owners
            ):
                return await ctx.send_or_reply(
                    content="You cannot punish other staff members.",
                )
            if (
                ctx.guild.me.top_role.position > target.top_role.position
                and not target.guild_permissions.administrator
            ):
                try:
                    warnings = (
                        await self.bot.cxn.fetchrow(
                            "SELECT warnings FROM warn WHERE user_id = $1 AND server_id = $2",
                            target.id,
                            ctx.guild.id,
                        )
                        or (None)
                    )
                    if warnings is None:
                        warnings = 0
                        await self.bot.cxn.execute(
                            "INSERT INTO warn VALUES ($1, $2, $3)",
                            target.id,
                            ctx.guild.id,
                            int(warnings) + 1,
                        )
                        warned.append(f"{target.name}#{target.discriminator}")
                    else:
                        warnings = int(warnings[0])
                        try:
                            await self.bot.cxn.execute(
                                "UPDATE warn SET warnings = warnings + 1 WHERE server_id = $1 AND user_id = $2",
                                ctx.guild.id,
                                target.id,
                            )
                            warned.append(f"{target.name}#{target.discriminator}")
                        except Exception:
                            raise

                except Exception as e:
                    return await ctx.send_or_reply(e)
                if reason:
                    try:
                        await target.send(
                            f"{self.bot.emote_dict['announce']} You have been warned in **{ctx.guild.name}** `{reason}`."
                        )
                    except Exception:
                        return
            else:
                return await ctx.send_or_reply(
                    "<:fail:816521503554273320> `{0}` could not be warned.".format(
                        target
                    )
                )
        if warned:
            await ctx.send_or_reply(
                content=f'{self.bot.emote_dict["success"]} Warned `{", ".join(warned)}`',
            )

    @decorators.command(brief="Count the warnings a user has.", aliases=["listwarns"])
    @commands.guild_only()
    async def warncount(self, ctx, *, target: discord.Member = None):
        """
        Usage: -warncount [member]
        Alias: -listwarns
        Output: Show how many warnings the user has
        """
        if target is None:
            target = ctx.author

        try:
            warnings = (
                await self.bot.cxn.fetchrow(
                    "SELECT warnings FROM warn WHERE user_id = $1 AND server_id = $2",
                    target.id,
                    ctx.guild.id,
                )
                or None
            )
            if warnings is None:
                return await ctx.send_or_reply(
                    f"{self.emote_dict['success']} User `{target}` has no warnings."
                )
            warnings = int(warnings[0])
            await ctx.send_or_reply(
                content=f"{self.bot.emote_dict['announce']} User `{target}` currently has **{warnings}** warning{'' if int(warnings) == 1 else 's'} in this server.",
            )
        except Exception as e:
            return await ctx.send_or_reply(e)

    @decorators.command(
        brief="Clear a user's warnings",
        aliases=[
            "deletewarnings",
            "removewarns",
            "removewarnings",
            "deletewarns",
            "clearwarnings",
        ],
    )
    @commands.guild_only()
    @checks.has_perms(kick_members=True)
    async def clearwarns(self, ctx, *, target: discord.Member = None):
        """
        Usage: -clearwarns [user]
        Aliases: -deletewarnings, -removewarns, -removewarnings, -deletewarns, -clearwarnings
        Permission: Kick Members
        Output: Clears all warnings for that user
        """
        if target is None:
            return await ctx.send_or_reply(
                content=f"Usage: `{ctx.prefix}deletewarn <target>`",
            )
        try:
            warnings = (
                await self.bot.cxn.fetchrow(
                    "SELECT warnings FROM warn WHERE user_id = $1 AND server_id = $2",
                    target.id,
                    ctx.guild.id,
                )
                or None
            )
            if warnings is None:
                return await ctx.send_or_reply(
                    f"{self.emote_dict['success']} User `{target}` has no warnings."
                )
            warnings = int(warnings[0])
            await self.bot.cxn.execute(
                "DELETE FROM warn WHERE user_id = $1 and server_id = $2",
                target.id,
                ctx.guild.id,
            )
            await ctx.send_or_reply(
                content=f"{self.emote_dict['success']} Cleared all warnings for `{target}` in this server.",
            )
            try:
                await target.send(
                    f"{self.bot.emote_dict['announce']} All your warnings have been cleared in **{ctx.guild.name}**."
                )
            except Exception:
                return
        except Exception as e:
            return await ctx.send_or_reply(e)

    @decorators.command(
        brief="Revoke a warning from a user",
        aliases=["revokewarning", "undowarning", "undowarn"],
    )
    @commands.guild_only()
    @checks.has_perms(kick_members=True)
    async def revokewarn(self, ctx, *, target: discord.Member = None):
        """
        Usage: -revokewarn [user]
        Aliases: -revokewarning, -undowarning, -undowarn
        Permission: Kick Members
        Output: Revokes a warning from a user
        """
        if target is None:
            return await ctx.send_or_reply(
                content=f"Usage: `{ctx.prefix}revokewarn <target>`",
            )
        try:
            warnings = (
                await self.bot.cxn.fetchrow(
                    "SELECT warnings FROM warn WHERE user_id = $1 AND server_id = $2",
                    target.id,
                    ctx.guild.id,
                )
                or None
            )
            if warnings is None:
                return await ctx.send_or_reply(
                    f"{self.emote_dict['success']} User `{target}` has no warnings to revoke."
                )
            warnings = int(warnings[0])
            if int(warnings) == 1:
                await self.bot.cxn.execute(
                    "DELETE FROM warn WHERE user_id = $1 and server_id = $2",
                    target.id,
                    ctx.guild.id,
                )
                await ctx.send_or_reply(
                    f"{self.emote_dict['success']} Cleared all warnings for `{target}` in this server."
                )
            else:
                await self.bot.cxn.execute(
                    "UPDATE warn SET warnings = warnings - 1 WHERE server_id = $1 AND user_id = $2",
                    ctx.guild.id,
                    target.id,
                )
                await ctx.send_or_reply(
                    f"{self.emote_dict['success']} Revoked a warning for `{target}` in this server."
                )
            try:
                await target.send(
                    f"{self.bot.emote_dict['announce']} You last warning has been revoked in **{ctx.guild.name}**."
                )
            except Exception:
                return
        except Exception as e:
            return await ctx.send_or_reply(e)

    @decorators.command(brief="Display the server warnlist.", aliases=["warns"])
    @commands.guild_only()
    @checks.has_perms(manage_messages=True)
    async def serverwarns(self, ctx):
        """
        Usage: -serverwarns
        Alias: -warns
        Output: Embed of all warned members in the server
        Permission: Manage Messages
        """
        query = """SELECT COUNT(*) FROM warn WHERE server_id = $1"""
        count = await self.bot.cxn.fetchrow(query, ctx.guild.id)
        query = """SELECT user_id, warnings FROM warn WHERE server_id = $1 ORDER BY warnings DESC"""
        records = await self.bot.cxn.fetch(query, ctx.guild.id) or None
        if records is None:
            return await ctx.send_or_reply(
                content=f"{self.emote_dict['warn']} No current warnings exist on this server.",
            )

        p = pagination.SimplePages(
            entries=[
                [
                    f"User: `{ctx.guild.get_member(x[0]) or 'Not Found'}` Warnings `{x[1]}`"
                ]
                for x in records
            ],
            per_page=20,
        )
        p.embed.title = "{} Warn List ({:,} total)".format(
            ctx.guild.name, int(count[0])
        )

        try:
            await p.start(ctx)
        except menus.MenuError as e:
            await ctx.send_or_reply(e)

    @decorators.command(
        brief="Enable or disable auto-deleting invite links",
        aliases=["removeinvitelinks", "deleteinvites", "antiinvites"],
    )
    @checks.has_perms(manage_guild=True)
    async def antiinvite(self, ctx, *, yes_no=None):
        """
        Usage:      -antiinvite <yes|enable|true|on||no|disable|false|off>
        Aliases:    -removeinvites, -deleteinvites, -antiinvites
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
        case_insensitive=True,
        aliases=["autoroles", "autoassign"],
        brief="Assign roles to new members.",
    )
    @checks.bot_has_perms(manage_roles=True)
    @checks.has_perms(manage_guild=True, manage_roles=True)
    async def autorole(self, ctx):
        """
        Usage: -autorole <option>
        Aliases:
            -autoassign
            -autoroles
        Output: Assigns roles to new users
        Examples:
            -autorole add <role1> <role2>
            -autorole show
        Permission: Manage Server, Manage Roles
        Options:
            add, remove, clear, show
        """
        if ctx.invoked_subcommand is None:
            return await ctx.usage("<option> [arguments]")

    @autorole.command(brief="Auto-assign roles on user join.")
    async def add(self, ctx, roles: commands.Greedy[discord.Role] = None):
        """
        Usage: -autorole add <role1> [role2]...
        Output:
            Will automatically assign
            the passed roles to users
            who join the server.
        Examples:
            -autorole add <role1> [role2]
            -autoassign add <role>
        Notes:
            Accepts any number of roles.
            Roles with multiple words must
            be encapsulated by quotes.
        """
        if roles is None:
            return await ctx.usage("<roles>")
        for role in roles:
            self.bot.server_settings[ctx.guild.id]["autoroles"].append(role.id)
        query = f"""
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
    async def remove(self, ctx, roles: commands.Greedy[discord.Role] = None):
        """
        Usage: -autorole remove <role1> [role2]...
        Output:
            Will no longer assign
            the passed roles to users
            who join the server.
        Examples:
            -autorole rm <role1> <role2>
            -autoassign remove <role>
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
        query = f"""
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

    @autorole.command(brief="Clear all current autoroles.")
    async def clear(self, ctx):
        """
        Usage: -autorole clear
        Output:
            Will no longer assign
            any previous autoroles
            to users who join the server.
        Examples:
            -autorole rm <role1> [role2]
            -autoassign remove <role>
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
        Usage: -autorole show
        Alias: -autorole display
        Output:
            Will start a pagination session
            showing all current autoroles
        Examples:
            -autorole display
            -autoassign show
        """
        autoroles = self.bot.server_settings[ctx.guild.id]["autoroles"]

        if autoroles == []:
            return await ctx.send_or_reply(
                content=f"No autoroles yet, use `{ctx.prefix}autorole add <roles>`",
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

    @commands.Cog.listener()
    async def on_message(self, message):
        if self.bot.ready is False:
            return
        if not message.guild:
            return
        if not self.dregex.search(message.content):
            return

        removeinvitelinks = self.bot.server_settings[message.guild.id]["antiinvite"]

        if removeinvitelinks is not True:
            return

        member = message.guild.get_member(message.author.id)
        if message.author.id in self.bot.constants.owners:
            return  # We are immune!
        if member.guild_permissions.manage_messages:
            return  # We are immune!

        try:
            await message.delete()
            await message.channel.send("No invite links allowed", delete_after=7)
        except Exception:
            return  # await message.channel.send(e)

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        if self.bot.ready is False:
            return
        if not before.guild:
            return
        if not self.dregex.search(after.content):
            return

        removeinvitelinks = self.bot.server_settings[after.guild.id]["antiinvite"]

        if removeinvitelinks is not True:
            return

        member = after.author
        if member.id in self.bot.constants.owners:
            return  # We are immune!
        if member.guild_permissions.manage_messages:
            return  # We are immune!
        try:
            await after.delete()
            await after.channel.send("No invite links allowed", delete_after=7)
        except Exception:
            return

    @decorators.command(brief="Reassign roles on user rejoin.", aliases=["stickyroles"])
    @commands.guild_only()
    @checks.bot_has_perms(manage_roles=True)
    @checks.has_perms(manage_guild=True, manage_roles=True)
    async def reassign(self, ctx, *, yes_no=None):
        """
        Usage:      -reassign <yes|enable|true|on||no|disable|false|off>
        Aliases:    -stickyroles
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

    @commands.Cog.listener()
    async def on_member_join(self, member):
        if self.bot.ready is False:
            return
        required_perms = member.guild.me.guild_permissions.manage_roles
        if not required_perms:
            return

        reassign = self.bot.server_settings[member.guild.id]["reassign"]
        if reassign is not True:
            pass
        else:
            query = (
                """SELECT roles FROM userroles WHERE user_id = $1 and server_id = $2"""
            )
            old_roles = (
                await self.bot.cxn.fetchval(query, member.id, member.guild.id) or None
            )
            if old_roles is None:
                pass
            roles = str(old_roles).split(",")
            for role_id in roles:
                try:
                    role = member.guild.get_role(int(role_id))
                except ValueError:
                    continue
                if role not in member.roles:
                    try:
                        await member.add_roles(role)
                    except Exception as e:
                        print(e)

        query = """SELECT autoroles FROM servers WHERE server_id = $1"""
        autoroles = await self.bot.cxn.fetchrow(query, member.guild.id) or None
        if autoroles is None or autoroles[0] is None:
            return
        else:
            roles = str(autoroles[0]).split(",")
            for role_id in roles:
                try:
                    role = member.guild.get_role(int(role_id))
                except ValueError:
                    continue
                if role not in member.roles:
                    try:
                        await member.add_roles(role)
                    except Exception as e:
                        print(e)

    @decorators.group(
        invoke_without_command=True,
        case_insensitive=True,
        name="filter",
        aliases=["profanity"],
        brief="Manage the server's word filter.",
    )
    @commands.guild_only()
    @checks.has_perms(manage_guild=True)
    async def _filter(self, ctx):
        """
        Usage: -filter <option>
        Alias: -profanity
        Permission: Manage Server
        Output:
            Adds, removes, clears, or displays the filter.
        Example:
            -filter add <badwords>
        Options:
            add, remove, display, clear
        Notes:
            Words added to the filter list
            will delete all messages with
            that word. Users with the
            Manage Messages permission are immune.
            To add or remove multiple words with
            one command, separate the words by a comma.
            Example: -filter add badword1, badword2
        """
        if ctx.invoked_subcommand is None:
            help_command = self.bot.get_command("help")
            await help_command(ctx, invokercommand="filter")

    @_filter.command(name="add", aliases=["+"], brief="Add words to the filter.")
    @checks.has_perms(manage_guild=True)
    async def add_words(self, ctx, *, words_to_filter: str = None):
        """
        Usage: -filter add <words>
        Output:
            Saves all the passed words
            and will delete when users
            without the Manage Messages
            permission send those words.
        Notes:
            separate words by a comma
            to add multiple words at once.
        """
        if words_to_filter is None:
            return await ctx.usage("<word>")

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
    async def remove_words(self, ctx, *, words: str = None):
        """
        Usage: -filter remove <words>
        Alias: --, -rm , -rem
        Output:
            Deletes the passed words from
            the filter (if they were saved.)
        Notes:
            separate words by a comma
            to remove multiple words at once.
        """
        if words is None:
            return await ctx.send_or_reply(
                content=f"Usage: `{ctx.prefix}filter remove <word>`",
            )

        words_to_remove = words.lower().split(",")

        word_list = self.bot.server_settings[ctx.guild.id]["profanities"]
        if word_list == []:
            return await ctx.send_or_reply(
                content=f"{self.bot.emote_dict['warn']} This server has no filtered words.",
            )

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
            await ctx.send_or_reply(
                content=f"{self.bot.emote_dict['warn']} The word{'' if len(not_found) == 1 else 's'} `{', '.join(not_found)}` "
                f"{'was' if len(not_found) == 1 else 'were'} not in the word filter.",
            )

        if removed:
            await ctx.send_or_reply(
                content=f"{self.bot.emote_dict['success']} The word{'' if len(removed) == 1 else 's'} `{', '.join(removed)}` "
                f"{'was' if len(removed) == 1 else 'were'} successfully removed from the word filter.",
            )

    @_filter.command(brief="Show all filtered words.", aliases=["show"])
    @checks.has_perms(manage_guild=True)
    async def display(self, ctx):
        """
        Usage: -filter display
        Alias: -filter show
        Output:
            Starts a pagination session to
            show all currently filtered words.
        """
        words = self.bot.server_settings[ctx.guild.id]["profanities"]

        if words == []:
            return await ctx.send_or_reply(
                content=f"No filtered words yet, use `{ctx.prefix}filter add <word>` to filter words",
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
        Usage: -filter clear
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
        self.bot.server_settings[ctx.guild.id]["profanities"] = []

        await ctx.send_or_reply(
            content=f"{self.bot.emote_dict['success']} Removed all filtered words.",
        )
