import colorsys

import discord
from discord.ext import commands, menus

from utilities import pagination, permissions

EMBED_MAX_LEN = 2048  # constant for paginating embeds
STATUSMAP1 = {
    discord.Status.online: "1",
    discord.Status.dnd: "2",
    discord.Status.idle: "3",
}  # for sorting
STATUSMAP2 = {
    discord.Status.online: "<:online:810650040838258711>",
    discord.Status.dnd: "<:dnd:810650845007708200>",
    discord.Status.idle: "<:idle:810650560146833429>",
    discord.Status.offline: "<:offline:810650959859810384>",
}


def setup(bot):
    bot.add_cog(Roles(bot))


class Roles(commands.Cog):
    """
    Manage all actions regarding roles.
    """

    def __init__(self, bot):
        self.bot = bot

        self.emote_dict = bot.emote_dict

    @commands.command(brief="Get info on a specific role.", aliases=["ri"])
    @commands.guild_only()
    async def roleinfo(self, ctx, *, role: discord.Role):
        """
        Usage:  -roleinfo <role>
        Alias:  -ri
        Output: Info on the passed role
        """
        owner = ctx.guild.owner
        guild = ctx.guild

        # perm_list = [Perm[0] for Perm in role.permissions if Perm[1]]

        embed = discord.Embed(
            color=self.bot.constants.embed, timestamp=ctx.message.created_at
        )

        embed.set_author(name=f"{owner}", icon_url=owner.avatar_url)
        embed.set_thumbnail(url=guild.icon_url)
        embed.set_footer(
            text=f"Requested by {ctx.author}", icon_url=ctx.author.avatar_url
        )

        embed.add_field(
            name=f"**Role Info for {role.name}:**",
            value=f"> **Name:** {role.mention}\n"
            f"> **ID:** {role.id}\n"
            f"> **Guild:** {role.guild}\n"
            f"> **Members:** {sum(1 for member in role.guild.members if role in member.roles)}\n"
            f"> **Created at:** {role.created_at.__format__('%B %d, %Y at %I:%M %p')}\n"
            f"> **Position:** {role.position}\n"
            f"> **Hoisted:** {role.hoist}\n"
            f"> **Color:** {role.color}\n"
            f"> **Mentionable:** {role.mentionable}\n"
            f"> **Managed:** {role.managed}\n",
            # f"> **Bot Role:** {role.is_bot_managed()}\n"
            # f"> **Booster Role:** {role.is_premium_subscriber()}\n"
            inline=False,
        )
        # embed.add_field(name="Permissions:", value=str(role.permissions), inline=False)
        # embed.add_field(name="Permissions:", value=", ".join(perm_list).replace("_", " ").replace("guild", "server").title().replace("Tts", "TTS"), inline=False)
        # .replace("_", " ").replace("guild", "server").title().replace("Tts", "TTS")
        await ctx.send_or_reply(embed=embed)

    @commands.command(
        aliases=["ar", "adrl", "addrl", "adrole"], brief="Adds roles to users."
    )
    @commands.guild_only()
    @permissions.bot_has_permissions(manage_roles=True)
    @permissions.has_permissions(manage_roles=True)
    async def addrole(
        self, ctx, targets: commands.Greedy[discord.Member], *roles: discord.Role
    ):
        """
        Usage:      -addrole [user] [user...] [role] [role]...
        Aliases:    -ar, -adrole, -adrl, -addrl
        Example:    -ar Hecate#3523 @Snowbot @Verified Member
        Permission: Manage Roles
        Output:     Adds multiple roles to multiple users
        """
        if ctx.guild.me.permissions_in(ctx.message.channel).manage_roles is False:
            return await ctx.send_or_reply(
                content="Sorry, I do not have the manage_roles permission",
            )

        if len(targets) == 0:
            return await ctx.send_or_reply(
                content=f"Usage: `{ctx.prefix}ar <user> [user] [user] <role> [role] [role]...`",
            )
        if len(roles) == 0:
            return await ctx.send_or_reply(
                content=f"Usage: `{ctx.prefix}ar <user> [user] [user] <role> [role] [role]...`",
            )
        target_list = []
        target_names = []
        for target in targets:
            role_list = []
            for role in roles:
                if (
                    role.permissions.administrator
                    and ctx.author.id not in self.bot.constants.owners
                ):
                    return await ctx.send_or_reply(
                        content="I cannot manipulate an admin role",
                    )
                if (
                    role.position >= ctx.author.top_role.position
                    and ctx.author.id not in self.bot.constants.owners
                ):
                    return await ctx.send_or_reply(
                        content="That role is higher than your highest role",
                    )
                try:
                    await target.add_roles(role)
                except discord.Forbidden:
                    return await ctx.send_or_reply(
                        content="I do not have permission to do that",
                    )
                role_list.append(role)
                target_list.append(target)
            if role_list:
                role_names = []
                for role in role_list:
                    name = role.name
                    role_names += [name]
            name = f"{target.name}#{target.discriminator}"
            target_names.append(name)
        await ctx.send_or_reply(
            f'{self.bot.emote_dict["success"]} '
            f'Added user{"" if len(target_names) == 1 else "s"} `{", ".join(target_names)}` '
            f'the role{"" if len(role_list) == 1 else "s"} `{", ".join(role_names)}`'
        )

    @commands.command(
        aliases=["rr", "remrole", "rmrole", "rmrl"], brief="Removes roles from users."
    )
    @commands.guild_only()
    @permissions.bot_has_permissions(manage_roles=True)
    @permissions.has_permissions(manage_roles=True)
    async def removerole(
        self, ctx, targets: commands.Greedy[discord.Member], *roles: discord.Role
    ):
        """
        Usage:      -removerole [user] [user...] [role] [role]...
        Aliases:    -rr, -remrole, -rmrole, -rmrl
        Example:    -rr Hecate#3523 @Snowbot @Verified Member
        Permission: Manage Roles
        Output:     Removes multiple roles from multiple users
        """
        if (
            ctx.message.guild.me.permissions_in(ctx.message.channel).manage_roles
            is False
        ):
            return await ctx.send_or_reply(
                content="Sorry, I do not have the manage_roles permission",
            )

        if len(targets) == 0:
            return await ctx.send_or_reply(
                content=f"Usage: `{ctx.prefix}rr <user> [user] [user] <role> [role] [role]...`",
            )
        if len(roles) == 0:
            return await ctx.send_or_reply(
                content=f"Usage: `{ctx.prefix}rr <user> [user] [user] <role> [role] [role]...`",
            )
        target_list = []
        target_names = []
        for target in targets:
            role_list = []
            for role in roles:
                if (
                    role.permissions.administrator
                    and ctx.author.id not in self.bot.constants.owners
                ):
                    return await ctx.send_or_reply(
                        content="I cannot manipulate an admin role",
                    )
                if (
                    role.position > ctx.author.top_role.position
                    and ctx.author.id not in self.bot.constants.owners
                    and ctx.author.id != ctx.guild.owner.id
                ):
                    return await ctx.send_or_reply(
                        content="That role is higher than your highest role",
                    )
                if (
                    role.position == ctx.author.top_role.position
                    and ctx.author.id not in self.bot.constants.owners
                    and ctx.author.id != ctx.guild.owner.id
                ):
                    return await ctx.send_or_reply(
                        content="That role is your highest role",
                    )
                try:
                    await target.remove_roles(role)
                except discord.Forbidden:
                    return await ctx.send_or_reply(
                        content="I do not have permission to do that",
                    )
                role_list.append(role)
                target_list.append(target)
            if role_list:
                role_names = []
                for role in role_list:
                    name = role.name
                    role_names += [name]
            name = f"{target.name}#{target.discriminator}"
            target_names.append(name)
        await ctx.send_or_reply(
            f'{self.bot.emote_dict["success"]} '
            f'Removed user{"" if len(target_names) == 1 else "s"} `{", ".join(target_names)}` '
            f'the role{"" if len(role_list) == 1 else "s"} `{", ".join(role_names)}`'
        )

    @commands.group(
        brief="Mass adds or removes a role to users.", aliases=["multirole"]
    )
    @commands.guild_only()
    @permissions.bot_has_permissions(manage_guild=True, manage_roles=True)
    @permissions.has_permissions(manage_roles=True)
    async def massrole(self, ctx):
        """
        Usage:      -massrole <method> <role1> <role2>
        Alias:      -multirole
        Example:    -massrole add @everyone Verified
        Permission: Manage Roles
        Output:     Adds or removes a role to all users with a given role
        Methods:
            add
            remove (Aliases: rem, rm)

        Notes:
            Command may take a few minutes to complete its execution.
            Please be patient.
        """
        if ctx.invoked_subcommand is None:
            help_command = self.bot.get_command("help")
            await help_command(ctx, invokercommand="massrole")

    @massrole.command(brief="Adds all members with a certain role a new role.")
    async def add(self, ctx, role1: discord.Role = None, role2: discord.Role = None):
        if role1 is None:
            return await ctx.send_or_reply(
                content="Usage: `{ctx.prefix}massrole add <role1> <role2> ",
            )
        if role2 is None:
            return await ctx.send_or_reply(
                content="Usage: `{ctx.prefix}massrole add <role1> <role2> ",
            )
        if (
            ctx.author.top_role.position < role1.position
            and ctx.author.id not in self.bot.constants.owners
        ):
            return await ctx.send_or_reply(
                "You have insufficient permission to execute this command"
            )
        if (
            role2.permissions.administrator
            and ctx.author.id not in self.bot.constants.owners
        ):
            return await ctx.send_or_reply(
                content="I cannot manipulate an admin role",
            )
        if (
            role2.position > ctx.author.top_role.position
            and ctx.author.id not in self.bot.constants.owners
            and ctx.author.id != ctx.guild.owner.id
        ):
            return await ctx.send_or_reply(
                content="That role is higher than your highest role",
            )
        if (
            role2.position == ctx.author.top_role.position
            and ctx.author.id not in self.bot.constants.owners
            and ctx.author.id != ctx.guild.owner.id
        ):
            return await ctx.send_or_reply(
                content="That role is your highest role",
            )
        if (
            role1.position > ctx.author.top_role.position
            and ctx.author.id not in self.bot.constants.owners
            and ctx.author.id != ctx.guild.owner.id
        ):
            return await ctx.send_or_reply(
                content="That role is higher than your highest role",
            )
        if (
            role1.position == ctx.author.top_role.position
            and ctx.author.id not in self.bot.constants.owners
            and ctx.author.id != ctx.guild.owner.id
        ):
            return await ctx.send_or_reply(
                content="That role is your highest role",
            )
        number_of_members = []
        for member in ctx.guild.members:
            if role1 in member.roles and not role2 in member.roles:
                number_of_members.append(member)

        members_to_add_roles = len(number_of_members)
        if members_to_add_roles < 1:
            return await ctx.send_or_reply(
                content=f"{self.emote_dict['error']} No members to add roles to",
            )
        msg = await ctx.send_or_reply(
            f"{self.emote_dict['error']} Adding role `{role2.name}` to `{members_to_add_roles}` member{'' if members_to_add_roles == 1 else 's'}. This process may take several minutes."
        )
        for member in role1.members:
            try:
                await member.add_roles(role2)
            except discord.Forbidden:
                return await ctx.send_or_reply(
                    content="I do not have permission to do that",
                )
        # we made it
        await msg.edit(
            content=f"{self.emote_dict['success']} Added role `{role2.name}` to `{members_to_add_roles}` member{'' if members_to_add_roles == 1 else 's'}"
        )

    @massrole.command(
        brief="Removes all members with a certain role a new role",
        aliases=["rm", "rem"],
    )
    async def remove(self, ctx, role1: discord.Role, role2: discord.Role):
        if role1 is None:
            return await ctx.send_or_reply(
                content="Usage: `{ctx.prefix}massrole add <role1> <role2> ",
            )
        if role2 is None:
            return await ctx.send_or_reply(
                content="Usage: `{ctx.prefix}massrole add <role1> <role2> ",
            )
        if (
            ctx.author.top_role.position < role1.position
            and ctx.author.id not in self.bot.constants.owners
        ):
            return await ctx.send_or_reply(
                "You have insufficient permission to execute this command"
            )
        if (
            role2.permissions.administrator
            and ctx.author.id not in self.bot.constants.owners
        ):
            return await ctx.send_or_reply(
                content="I cannot manipulate an admin role",
            )
        if (
            role2.position > ctx.author.top_role.position
            and ctx.author.id not in self.bot.constants.owners
            and ctx.author.id != ctx.guild.owner.id
        ):
            return await ctx.send_or_reply(
                content="That role is higher than your highest role",
            )
        if (
            role2.position == ctx.author.top_role.position
            and ctx.author.id not in self.bot.constants.owners
            and ctx.author.id != ctx.guild.owner.id
        ):
            return await ctx.send_or_reply(
                content="That role is your highest role",
            )
        if (
            role1.position > ctx.author.top_role.position
            and ctx.author.id not in self.bot.constants.owners
            and ctx.author.id != ctx.guild.owner.id
        ):
            return await ctx.send_or_reply(
                content="That role is higher than your highest role",
            )
        if (
            role1.position == ctx.author.top_role.position
            and ctx.author.id not in self.bot.constants.owners
            and ctx.author.id != ctx.guild.owner.id
        ):
            return await ctx.send_or_reply(
                content="That role is your highest role",
            )
        number_of_members = []
        for member in ctx.guild.members:
            if role1 in member.roles and role2 in member.roles:
                number_of_members.append(member)

        members_to_add_roles = len(number_of_members)
        if members_to_add_roles < 1:
            return await ctx.send_or_reply(
                content=f"{self.emote_dict['error']} No members to remove roles from",
            )
        msg = await ctx.send_or_reply(
            f"{self.emote_dict['error']} Removing role `{role2.name}` from `{members_to_add_roles}` member{'' if members_to_add_roles == 1 else 's'}. This process may take several minutes."
        )
        for member in role1.members:
            try:
                await member.remove_roles(role2)
            except discord.Forbidden:
                return await ctx.send_or_reply(
                    content="I do not have permission to do that",
                )
        # we made it
        await msg.edit(
            content=f"{self.emote_dict['success']} Removed role `{role2.name}` from `{members_to_add_roles}` member{'' if members_to_add_roles == 1 else 's'}"
        )

    def role_accumulate(self, check_roles, members):
        ## iterate over the members to accumulate a count of each role
        rolecounts = {}
        for role in check_roles:  # populate the accumulator dict
            if not role.is_default():
                rolecounts[role] = 0

        for member in members:
            for role in member.roles:
                if (
                    role in check_roles and not role.is_default()
                ):  # want to exclude @everyone from this list
                    rolecounts[role] += 1

        return rolecounts

    async def rolelist_paginate(self, ctx, rlist, title="Server Roles"):
        # takes a list of roles and counts and sends it out as multiple embed as nessecary
        pages = []
        buildstr = ""
        for role, count in rlist:  # this generates and paginates the info
            line = "{:,} {}\n".format(count, role.mention)
            if len(buildstr) + len(line) > EMBED_MAX_LEN:
                pages.append(buildstr)  # split the page here
                buildstr = line
            else:
                buildstr += line
        if buildstr:
            pages.append(
                buildstr
            )  # if the string has data not already listed in the pages, add it

        for index, page in enumerate(pages):  # enumerate so we can add a page number
            embed = discord.Embed(
                title=f"{title}", description=page, color=self.bot.constants.embed
            )
            embed.set_footer(text="Page {:,}/{:,}".format(index + 1, len(pages)))
            await ctx.send_or_reply(embed=embed)

    # The next couple commands are mostly from CorpBot.py with a few modifications
    # https://github.com/corpnewt/CorpBot.py

    @commands.command(brief="Show an embed of all server roles.", aliases=["roles"])
    @commands.guild_only()
    @permissions.has_permissions(manage_messages=True)
    async def listroles(self, ctx, sort_order: str = "default"):
        """
        Usage: -listroles
        Alias: -roles
        Permission: Manage Messages
        Output:
            Shows roles and their member counts. Takes one argument,
            sort_order, which can be default, name, count, or color.
        """

        sort_order = sort_order.lower()
        if not sort_order in [
            "default",
            "name",
            "count",
            "color",
        ]:  # make sure it has valid args
            return await ctx.send_or_reply(
                "Invalid arguments.\n ```yaml\nVALID OPTIONS:\n=============\n\n default\nname\ncount\ncolor\n```"
            )

        check_roles = (
            ctx.guild.roles
        )  # we use roles for these because sometimes we want to see the order

        ## now we iterate over the members to accumulate a count of each role
        rolecounts = self.role_accumulate(check_roles, ctx.guild.members)

        sorted_list = []
        if sort_order == "default":  # default sort = the server role hierarchy
            for role in check_roles:
                if role in rolecounts:
                    sorted_list.append((role, rolecounts.get(role, 0)))
        elif sort_order == "name":  # name sort = alphabetical by role name
            sorted_list = sorted(
                rolecounts.items(), key=lambda tup: tup[0].name.lower()
            )
        elif sort_order == "count":  # count sort = decreasing member count
            sorted_list = sorted(
                rolecounts.items(), key=lambda tup: tup[1], reverse=True
            )
        elif (
            sort_order == "color"
        ):  # color sort: by increasing hue value in HSV color space
            sorted_list = sorted(
                rolecounts.items(),
                key=lambda tup: colorsys.rgb_to_hsv(
                    tup[0].color.r, tup[0].color.g, tup[0].color.b
                )[0],
            )

        if not sorted_list:  # another failsafe
            return

        sorted_list = sorted_list[::-1]
        await self.rolelist_paginate(
            ctx, sorted_list
        )  # send the list to get actually printed to discord

    @commands.command(brief="Counts the users with a role.")
    @commands.guild_only()
    async def rolecall(self, ctx, *, role: discord.Role = None):
        """
        Usage: -rolecall <role>
        Output:
            Shows the number of people with the passed role.
        """
        if role is None:
            return await ctx.send_or_reply(
                content=f"Usage: `{ctx.prefix}rolecall <role>`",
            )

        count = 0
        online = 0
        for member in ctx.guild.members:
            if role in member.roles:
                count += 1
                if member.status != discord.Status.offline:
                    online += 1

        embed = discord.Embed(
            title=role.name,
            description="{}/{} online".format(online, count),
            color=self.bot.constants.embed,
        )
        embed.set_footer(text="ID: {}".format(role.id))
        await ctx.send_or_reply(embed=embed)

    @commands.command(brief="Show the people who have a role.")
    @commands.guild_only()
    @permissions.has_permissions(manage_messages=True)
    async def whohas(self, ctx, *, role: discord.Role = None):
        """
        Usage: -whohas <role>
        Permission: Manage Messages
        Output:
            Lists the people who have the specified role with their status.
        Notes:
        """
        if role is None:
            return await ctx.send_or_reply(
                content=f"Usage `{ctx.prefix}whohas <role>`",
            )

        users = [member for member in ctx.guild.members if role in member.roles]

        sorted_list = sorted(
            users,
            key=lambda usr: (STATUSMAP1.get(usr.status, "4"))
            + (usr.nick.lower() if usr.nick else usr.name.lower()),
        )

        page = [
            "{} {}".format(
                STATUSMAP2.get(member.status, self.emote_dict["offline"]),
                member.mention,
            )
            for member in sorted_list
        ]

        p = pagination.SimplePages(entries=page, per_page=20, index=False)
        p.embed.title = "{:,} members with {}".format(len(users), role.name)

        try:
            await p.start(ctx)
        except menus.MenuError as e:
            await ctx.send_or_reply(e)

    @commands.command(aliases=["rp"], brief="Show the permissions for a role.")
    @commands.guild_only()
    async def roleperms(self, ctx, *, role: discord.Role = None):
        """
        Usage:  -roleperms <role>
        Alias:  -rp
        Output:
            Embed with all the permissions
            granted to the passed role
        """
        if role is None:
            return await ctx.send_or_reply(
                content=f"Usage: `{ctx.prefix}roleperms <role>`",
            )

        permissions = ""
        permissionsne = ""
        try:
            for perm in role.permissions:
                perm = (perm[0].replace("_", " ").title(), perm[1])
                permissions += "**{}**: {}\n".format(*perm)
                permissionsne += "{}: {}\n".format(*perm)
            embed = discord.Embed(
                title="Permissions for role {}".format(role), color=role.color
            )
            embed.description = permissions
            try:
                await ctx.send_or_reply(embed=embed)
            except Exception:
                await ctx.send_or_reply(
                    "```Permissions for role {}\n\n{}```".format(role, permissionsne)
                )
        except Exception:
            await ctx.send_or_reply(
                "```Couldn't find role, are you sure you typed it correctly?\n\nYou typed: '{}'```".format(
                    role
                )
            )

    @commands.command(brief="Counts the roles on the server.")
    @commands.guild_only()
    async def rolecount(self, ctx):
        """
        Usage: -rolecount
        Output: Counts all server roles
        """
        await ctx.send_or_reply(
            "This server has {:,} total roles.".format(len(ctx.guild.roles) - 1)
        )

    @commands.command(brief="Show roles that have no users.")
    @commands.guild_only()
    async def emptyroles(self, ctx):
        """
        Usage: -emptyroles
        Output: Shows all roles with zero users
        """

        check_roles = (
            ctx.guild.roles
        )  # grab in hierarchy order so they're easier to find in the server settings
        rolecounts = self.role_accumulate(
            check_roles, ctx.guild.members
        )  # same accumulate as the `roles` command

        sorted_list = []
        for role in check_roles:
            if role in rolecounts and rolecounts[role] == 0:  # only add if count = 0
                sorted_list.append((role, rolecounts.get(role, 0)))

        if not sorted_list:  # another failsafe
            return await ctx.send_or_reply(
                content=f"{self.bot.emote_dict['error']} No empty roles found.",
            )

        await self.rolelist_paginate(ctx, sorted_list, title="Empty Roles")
