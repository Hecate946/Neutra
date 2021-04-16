import re
import asyncio
import asyncpg
import discord

from discord.ext import commands, menus

from utilities import permissions, pagination, utils


def setup(bot):
    bot.add_cog(Admin(bot))


class Admin(commands.Cog):
    """
    Module for server administration.
    """

    def __init__(self, bot):
        self.bot = bot
        self.dregex = re.compile(
            r"(?:https?://)?discord(?:app)?\.(?:com/invite|gg)/[a-zA-Z0-9]+/?"
        )

    @commands.command(
        brief="Add a custom server prefix.", aliases=["prefix", "setprefix"]
    )
    @commands.guild_only()
    @permissions.has_permissions(manage_guild=True)
    async def addprefix(self, ctx, new_prefix=None):
        """
        Usage: -addprefix
        Aliases: -prefix, -setprefix
        Output: Adds a custom prefix to your server.
        """
        if new_prefix is None:
            return await self.prefixes(ctx)
        current_prefixes = self.bot.server_settings[ctx.guild.id]["prefixes"].copy()
        try:
            current_prefixes.remove(f"<@!{self.bot.user.id}>")
        except ValueError:
            pass
        if new_prefix in current_prefixes:
            return await ctx.send(
                f"{self.bot.emote_dict['error']} `{new_prefix}` is already a registered prefix."
            )
        if len(current_prefixes) == 10:
            return await ctx.send(
                f"{self.bot.emote_dict['failed']} Max prefix limit of 10 has been reached."
            )
        if len(new_prefix) > 20:
            return await ctx.send(
                f"{self.bot.emote_dict['failed']} Max prefix length is 20 characters."
            )
        self.bot.server_settings[ctx.guild.id]["prefixes"].append(new_prefix)
        query = """
                INSERT INTO prefixes
                VALUES ($1, $2);
                """
        await self.bot.cxn.execute(query, ctx.guild.id, new_prefix)
        await ctx.send(
            f"{self.bot.emote_dict['success']} Successfully added prefix `{new_prefix}`"
        )

    @commands.command(
        brief="Remove a custom server prefix.", aliases=["remprefix", "rmprefix"]
    )
    @commands.guild_only()
    @permissions.has_permissions(manage_guild=True)
    async def removeprefix(self, ctx, old_prefix):
        """
        Usage: -removeprefix
        Aliases: -remprefix, -rmprefix
        Output: Removes a custom prefix from your server.
        """
        if old_prefix is None:
            return await ctx.send(
                reference=self.bot.rep_ref(ctx),
                content=f"Usage: `{ctx.prefix}addprefix <old prefix>`",
            )
        current_prefixes = self.bot.server_settings[ctx.guild.id]["prefixes"].copy()
        try:
            current_prefixes.remove(f"<@!{self.bot.user.id}>")
        except ValueError:
            pass
        if old_prefix not in current_prefixes:
            return await ctx.send(
                f"{self.bot.emote_dict['error']} `{old_prefix}` is not a registered prefix."
            )
        if len(current_prefixes) == 1:
            c = await pagination.Confirmation(
                msg=f"{self.bot.emote_dict['exclamation']} "
                "**This action will clear all my set prefixes "
                f"I will only respond to <@!{self.bot.user.id}>. "
                "Do you wish to continue?**"
            ).prompt(ctx)
            if c:
                query = """
                        DELETE FROM prefixes
                        WHERE server_id = $1
                        """
                await self.bot.cxn.execute(query, ctx.guild.id)
                query = """
                        INSERT INTO prefixes
                        VALUES ($1, $2)
                        """
                await self.bot.cxn.execute(
                    query, ctx.guild.id, f"<@!{self.bot.user.id}>"
                )
                self.bot.server_settings[ctx.guild.id]["prefixes"] = [
                    f"<@!{self.bot.user.id}>"
                ]
                f"{self.bot.emote_dict['success']} Successfully cleared all prefixes."
        else:
            query = """
                    DELETE FROM prefixes
                    WHERE server_id = $1
                    AND prefix = $2
                    """
            await self.bot.cxn.execute(query, ctx.guild.id, old_prefix)
            self.bot.server_settings[ctx.guild.id]["prefixes"].remove(old_prefix)
            await ctx.send(
                f"{self.bot.emote_dict['success']} Successfully removed prefix `{old_prefix}`"
            )

    @commands.command(
        brief="Clear all custom server prefixes.",
        aliases=[
            "clearprefixes",
            "removeprefixes",
            "remprefixes",
            "rmprefixes",
            "purgeprefixes",
            "purgeprefix",
        ],
    )
    @commands.guild_only()
    @permissions.has_permissions(manage_guild=True)
    async def clearprefix(self, ctx):
        """
        Usage: -clearprefix
        Aliases:
            -clearprefixes, -removeprefixes, -remprefixes,
            -rmprefixes, -purgeprefixes, -purgeprefix
        Output: Clears all custom server prefixes
        Notes:


        """
        current_prefixes = self.bot.server_settings[ctx.guild.id]["prefixes"].copy()
        try:
            current_prefixes.remove(f"<@!{self.bot.user.id}>")
        except ValueError:
            pass
        if current_prefixes == []:
            return await ctx.send(
                f"{self.bot.emote_dict['exclamation']} I currently have no prefixes set."
            )
        c = await pagination.Confirmation(
            msg=f"{self.bot.emote_dict['exclamation']} "
            "**This action will clear all my set prefixes "
            f"I will only respond to <@!{self.bot.user.id}>. "
            "Do you wish to continue?**"
        ).prompt(ctx)
        if c:
            query = """
                    DELETE FROM prefixes
                    WHERE server_id = $1
                    """
            await self.bot.cxn.execute(query, ctx.guild.id)

            query = """
                    INSERT INTO prefixes
                    VALUES ($1, $2)
                    """
            await self.bot.cxn.execute(query, ctx.guild.id, f"<@!{self.bot.user.id}>")
            self.bot.server_settings[ctx.guild.id]["prefixes"] = [
                f"<@!{self.bot.user.id}>"
            ]
            await ctx.send(
                f"{self.bot.emote_dict['success']} **Successfully cleared all prefixes.**"
            )
            return
        await ctx.send(
            reference=self.bot.rep_ref(ctx),
            content=f"{self.bot.emote_dict['exclamation']} **Cancelled.**",
        )

    @commands.command(
        brief="Show all server prefixes.",
        aliases=[
            "showprefix",
            "showprefixes",
            "listprefixes",
            "listprefix",
            "displayprefix",
            "displayprefixes",
        ],
    )
    @commands.guild_only()
    async def prefixes(self, ctx):
        """
        Usage: -prefixes
        Aliases:
            -showprefix, -showprefixes, -listprefixes,
            -listprefix, -displayprefixes, -displayprefix
        Output: Shows all the current server prefixes
        """
        current_prefixes = self.bot.server_settings[ctx.guild.id]["prefixes"].copy()
        try:
            current_prefixes.remove(f"<@!{self.bot.user.id}>")
        except ValueError:
            pass
        if current_prefixes == []:
            return await ctx.send(
                f"{self.bot.emote_dict['exclamation']} I currently have no prefixes set."
            )
        if len(current_prefixes) == 0:
            return await ctx.send(
                reference=self.bot.rep_ref(ctx),
                content=f"My current prefix is {self.bot.constants.prefix}",
            )
        await ctx.send(
            f"{self.bot.emote_dict['info']} My current prefix{' is' if len(current_prefixes) == 1 else 'es are '} `{', '.join(current_prefixes)}`"
        )

    @commands.command(brief="Setup server muting system.", aliases=["setmuterole"])
    @commands.guild_only()
    @permissions.bot_has_permissions(manage_roles=True)
    @permissions.has_permissions(manage_guild=True)
    async def muterole(self, ctx, role: discord.Role = None):
        """
        Usage:      -muterole <role>
        Alias:      -setmuterole
        Example:    -muterole @Muted
        Permission: Manage Server
        Output:
            This command will set a role of your choice as the
            "Muted" role. The bot will also create a channel
            named "muted" specifically for muted members.
        Notes:
            Channel "muted" may be deleted after command execution
            if so desired.
        """
        msg = await ctx.send(
            f"{self.bot.emote_dict['error']} Creating mute system. This process may take several minutes."
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

    # @commands.command(aliases=["setprefix"], brief="Set your server's custom prefix.")
    # @commands.guild_only()
    # @permissions.has_permissions(manage_guild=True)
    # async def prefix(self, ctx, new: str = None):
    #     """
    #     Usage: -prefix [new prefix]
    #     Alias: -setprefix
    #     Output: A new prefix for the server
    #     Example: -prefix $
    #     Permission: Manage Server
    #     Notes:
    #         The bot will always respond to @NGC0000 in addition
    #         to the set prefix. The default prefix is -.
    #         The bot will only respond to that prefix in DMs.
    #         The new prefix set must be under 5 characters.
    #     """
    #     if new is None:
    #         prefix = self.bot.server_settings[ctx.guild.id]["prefix"]
    #         await ctx.reply(f"The current prefix is `{prefix}`")
    #     else:
    #         if len(new) > 5:
    #             await ctx.send(
    #                 f"{ctx.author.mention}, that prefix is too long. The prefix must be five characters maximum."
    #             )
    #         else:
    #             self.bot.server_settings[ctx.guild.id]["prefix"] = new
    #             query = """
    #                     UPDATE servers
    #                     SET prefix = $1
    #                     WHERE server_id = $2
    #                     """
    #             await self.bot.cxn.execute(query, new, ctx.guild.id)
    #             await ctx.reply(
    #                 f"{self.bot.emote_dict['success']} The prefix has been set to `{new}`"
    #             )

    @commands.command(
        brief="Enable or disable auto-deleting invite links",
        aliases=["removeinvitelinks", "deleteinvites", "antiinvites"],
    )
    @permissions.has_permissions(manage_guild=True)
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
        await ctx.send(msg)

    @commands.group(case_insensitive=True, aliases=["autoroles"], brief="Assign roles to new members.")
    @permissions.bot_has_permissions(manage_roles=True)
    @permissions.has_permissions(manage_guild=True, manage_roles=True)
    async def autorole(self, ctx):
        """
        Usage: -autorole <option>
        Example: -autorole add <role1> <role2>
        Permission: Manage Server, Manage Roles
        Output: Assigns the roles to new users on server join.
        Options:
            add  <role1> <role2>... Adds autoroles
            remove <role1> <role2>... Removes autoroles
            clear Deletes all autoroles
            show Shows all current autoroles
        """
        if ctx.invoked_subcommand is None:
            await ctx.send_help(str(ctx.command))

    @autorole.command()
    async def add(self, ctx, roles: commands.Greedy[discord.Role] = None):
        if roles is None:
            return await ctx.send(
                reference=self.bot.rep_ref(ctx),
                content=f"Usage: `{ctx.prefix}autorole <roles>`",
            )
        for role in roles:
            self.bot.server_settings[ctx.guild.id]["autoroles"].append(role.id)
        query = f"""UPDATE servers
                    SET autoroles = $1
                    WHERE server_id = $2;
                """
        autoroles = ",".join(
            [str(x) for x in self.bot.server_settings[ctx.guild.id]["autoroles"]]
        )
        await self.bot.cxn.execute(query, autoroles, ctx.guild.id)
        await ctx.send(
            reference=self.bot.rep_ref(ctx),
            content=f"{self.bot.emote_dict['success']} Updated autorole settings.",
        )

    @autorole.command(aliases=["rem", "rm"])
    async def remove(self, ctx, roles: commands.Greedy[discord.Role] = None):
        if roles is None:
            return await ctx.send(
                reference=self.bot.rep_ref(ctx),
                content=f"Usage: `{ctx.prefix}autorole <roles>`",
            )
        autoroles = self.bot.server_settings[ctx.guild.id]["autoroles"]
        for role in roles:
            index = autoroles.index(str(role.id))
            autoroles.pop(index)
        query = f"""UPDATE servers SET autoroles = $1 WHERE server_id = $2"""
        autoroles = ",".join(
            [str(x) for x in self.bot.server_settings[ctx.guild.id]["autoroles"]]
        )
        await self.bot.cxn.execute(query, autoroles, ctx.guild.id)
        await ctx.send(
            reference=self.bot.rep_ref(ctx),
            content=f"{self.bot.emote_dict['success']} Updated autorole settings.",
        )

    @autorole.command()
    async def clear(self, ctx):
        self.bot.server_settings[ctx.guild.id]["autoroles"] = []
        query = """UPDATE servers
                   SET autoroles = NULL
                   WHERE server_id = $1;
                """
        await self.bot.cxn.execute(query, ctx.guild.id)
        await ctx.send(
            reference=self.bot.rep_ref(ctx),
            content=f"{self.bot.emote_dict['success']} Cleared all autoroles.",
        )

    @autorole.command()
    async def show(self, ctx):
        autoroles = self.bot.server_settings[ctx.guild.id]["autoroles"]

        if autoroles == []:
            return await ctx.send(
                f"No autoroles yet, use `{ctx.prefix}autorole add <roles>`"
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
            await ctx.send(e)

    @commands.Cog.listener()
    async def on_message(self, message):
        if self.bot.bot_ready is False:
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
        if self.bot.bot_ready is False:
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

    @commands.command(brief="Reassign roles on user rejoin.", aliases=["stickyroles"])
    @commands.guild_only()
    @permissions.bot_has_permissions(manage_roles=True)
    @permissions.has_permissions(manage_guild=True, manage_roles=True)
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
            msg = f"{self.bot.emote_dict['error']} That is not a valid setting."
            yes_no = current
        if yes_no != current and yes_no is not None:
            await self.bot.cxn.execute(
                "UPDATE servers SET reassign = $1 WHERE server_id = $2",
                reassign,
                ctx.guild.id,
            )
            self.bot.server_settings[ctx.guild.id]["reassign"] = reassign
        await ctx.send(msg)

    @commands.Cog.listener()
    async def on_member_join(self, member):
        if self.bot.bot_ready is False:
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

    @commands.group(
        invoke_without_command=True,
        name="filter",
        aliases=["profanity"],
        brief="Manage the server's word filter list (Command Group).",
    )
    @commands.guild_only()
    @permissions.has_permissions(manage_guild=True)
    async def _filter(self, ctx):
        """
        Usage:      -filter <method>
        Alias:      -profanity
        Example:    -filter add <badwords>
        Permission: Manage Server
        Output:     Adds, removes, clears, or displays the filter.
        Methods:
            add
            remove
            display     (Alias: show)
            clear
        Notes:
            Words added the the filter list will delete all
            messages containing that word. Users with the
            Manage Messages permission are immune. To add or
            remove multiple words with one command, separate
            the words with a comma.
            Example: -filter add badword1, badword2, badword3
        """
        if ctx.invoked_subcommand is None:
            help_command = self.bot.get_command("help")
            await help_command(ctx, invokercommand="filter")

    @_filter.command(name="add", aliases=["+"])
    @permissions.has_permissions(manage_guild=True)
    async def add_words(self, ctx, *, words_to_filter: str = None):
        if words_to_filter is None:
            return await ctx.channel.send(f"Usage: `{ctx.prefix}filter add <word>`")

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
            await ctx.send(
                f"{self.bot.emote_dict['error']} The word{'' if len(existing) == 1 else 's'} `{', '.join(existing)}` "
                f"{'was' if len(existing) == 1 else 'were'} already in the word filter."
            )

        if added:
            await ctx.send(
                f"{self.bot.emote_dict['success']} The word{'' if len(added) == 1 else 's'} `{', '.join(added)}` "
                f"{'was' if len(added) == 1 else 'were'} successfully added to the word filter."
            )

    @_filter.command(
        name="remove",
        aliases=["-"],
        brief="Remove a word from the servers filtere list",
    )
    @permissions.has_permissions(manage_guild=True)
    async def remove_words(self, ctx, *, words: str = None):
        if words is None:
            return await ctx.send(
                reference=self.bot.rep_ref(ctx),
                content=f"Usage: `{ctx.prefix}filter remove <word>`",
            )

        words_to_remove = words.lower().split(",")

        word_list = self.bot.server_settings[ctx.guild.id]["profanities"]
        if word_list == []:
            return await ctx.send(
                f"{self.bot.emote_dict['error']} This server has no filtered words."
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

        query = """UPDATE servers SET profanities = $1 WHERE server_id = $2;"""
        await self.bot.cxn.execute(query, insertion, ctx.guild.id)

        if not_found:
            await ctx.send(
                f"{self.bot.emote_dict['error']} The word{'' if len(not_found) == 1 else 's'} `{', '.join(not_found)}` "
                f"{'was' if len(not_found) == 1 else 'were'} not in the word filter."
            )

        if removed:
            await ctx.send(
                f"{self.bot.emote_dict['success']} The word{'' if len(removed) == 1 else 's'} `{', '.join(removed)}` "
                f"{'was' if len(removed) == 1 else 'were'} successfully removed from the word filter."
            )

    @_filter.command(
        brief="Display a list of this server's filtered words.", aliases=["show"]
    )
    @permissions.has_permissions(manage_guild=True)
    async def display(self, ctx):
        words = self.bot.server_settings[ctx.guild.id]["profanities"]

        if words == []:
            return await ctx.send(
                f"No filtered words yet, use `{ctx.prefix}filter add <word>` to filter words"
            )

        p = pagination.SimplePages(entries=[f"`{x}`" for x in words], per_page=20)
        p.embed.title = "Filtered words in {} ({:,} total)".format(
            ctx.guild.name, len(words)
        )

        try:
            await p.start(ctx)
        except menus.MenuError as e:
            await ctx.send(e)

    @_filter.command(name="clear")
    @permissions.has_permissions(manage_guild=True)
    async def _clear(self, ctx):

        query = """UPDATE servers SET profanities = NULL where server_id = $1;"""
        await self.bot.cxn.execute(query, ctx.guild.id)
        self.bot.server_settings[ctx.guild.id]["profanities"] = []

        await ctx.send(
            reference=self.bot.rep_ref(ctx),
            content=f"{self.bot.emote_dict['success']} Removed all filtered words.",
        )

    @commands.command(brief="Set the slowmode for a channel")
    @commands.guild_only()
    @permissions.bot_has_permissions(manage_channels=True)
    @permissions.has_permissions(manage_channels=True)
    async def slowmode(self, ctx, time: float):
        """
        Usage:      -slowmode [seconds]
        Output:     Sets the channel's slowmode to your input value.
        Permission: Manage Channels
        """
        try:
            await ctx.channel.edit(slowmode_delay=time)
        except discord.HTTPException as e:
            await ctx.send(
                f'{self.bot.emote_dict["failed"]} Failed to set slowmode because of an error\n{e}'
            )
        else:
            await ctx.send(
                f'{self.bot.emote_dict["success"]} Slowmode set to `{time}s`'
            )

    @commands.command(aliases=["lockdown", "lockchannel"], brief="Lock a channel")
    @commands.guild_only()
    @permissions.bot_has_permissions(manage_channels=True, manage_roles=True)
    @permissions.has_permissions(administrator=True)
    async def lock(self, ctx, channel_=None, minutes_: int = None):
        """
        Usage:      -lock [channel] [minutes]
        Output:     Locked channel for the specified time. Infinite if not specified
        Permission: Administrator
        """
        channel_id = 0

        minutes = 0
        if channel_ is None:
            channel_id += ctx.channel.id

        elif channel_.isdigit() or str(channel_).strip("<#>").isdigit():
            try:
                channel = ctx.guild.get_channel(int(str(channel_).strip("<#>")))
                channel_id += int(channel.id)
            except TypeError:
                minutes += int(channel_)
                channel_id += ctx.channel.id
        else:
            try:
                channel_obj = discord.utils.get(ctx.guild.text_channels, name=channel_)
                if channel_obj is None:
                    channel_id += ctx.channel.id
                else:
                    channel_id += channel_obj.id
            except Exception as e:
                return await ctx.send(e)
        channel = ctx.guild.get_channel(channel_id)
        try:
            overwrites_everyone = channel.overwrites_for(ctx.guild.default_role)
            my_overwrites = channel.overwrites_for(ctx.guild.me)
            everyone_overwrite_current = overwrites_everyone.send_messages
            msg = await ctx.send(
                reference=self.bot.rep_ref(ctx),
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
            if minutes_ is not None:
                if minutes_ > 120:
                    minutes_ = 120
                elif minutes_ < 1:
                    minutes_ = 0
                minutes += minutes_
            if minutes != 0:
                await msg.edit(
                    content=f"<:lock:817168229712527360> Channel {channel.mention} locked for `{minutes}` minute{'' if minutes == 1 else 's'}. ID: `{channel.id}`"
                )
                await asyncio.sleep(minutes * 60)
                await self.unlock(ctx, channel=channel, surpress=True)
            await msg.edit(
                content=f"<:lock:817168229712527360> Channel {channel.mention} locked. ID: `{channel.id}`"
            )
        except discord.Forbidden:
            await msg.edit(
                content=f"{self.bot.emote_dict['failed']} I have insufficient permission to lock channels."
            )

    @commands.command(brief="Unlock a channel.", aliases=["unlockchannel"])
    @commands.guild_only()
    @permissions.bot_has_permissions(manage_channels=True)
    @permissions.has_permissions(administrator=True)
    async def unlock(self, ctx, channel: discord.TextChannel = None, surpress=False):
        """
        Usage:      -unlock [channel]
        Output:     Unlocks a previously locked channel
        Permission: Administrator
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
                    return await ctx.send(
                        f"<:lock:817168229712527360> Channel {channel.mention} is already unlocked. ID: `{channel.id}`"
                    )

            msg = await ctx.send(
                reference=self.bot.rep_ref(ctx),
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
                content=f"<:unlock:817168258825846815> Channel {channel.mention} unlocked. ID: `{channel.id}`"
            )
        except discord.errors.Forbidden:
            await msg.edit(
                content=f"{self.bot.emote_dict['failed']} I have insufficient permission to unlock channels."
            )

    @commands.command(brief="Have the bot leave the server.", aliases=["kill", "die"])
    @commands.guild_only()
    @permissions.has_permissions(manage_guild=True)
    async def leave(self, ctx):
        """
        Usage: -leave
        Aliases: -kill, -die
        Output: Clears all stored server data and kicks me.
        Notes:
            You will receive confirmation, upon executing this
            command, all emoji stats, messages, last seen data
            roles, nicknames, and usernames will be deleted.
        """
        c = await pagination.Confirmation(
            f"{self.bot.emote_dict['exclamation']} **This action will remove me from this server and clear all my collected data. Do you wish to continue?**"
        ).prompt(ctx)
        if c:
            await ctx.guild.leave()
            return
        await ctx.send(
            reference=self.bot.rep_ref(ctx),
            content=f"{self.bot.emote_dict['exclamation']} **Cancelled.**",
        )
