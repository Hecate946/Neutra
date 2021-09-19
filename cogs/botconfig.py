import os
import json
import typing
import aiohttp
import discord

from discord.ext import commands, menus

from utilities import utils
from utilities import checks
from utilities import converters
from utilities import decorators
from utilities import pagination


def setup(bot):
    bot.add_cog(Botconfig(bot))


class Botconfig(commands.Cog):
    """
    Owner only configuration cog.
    """

    def __init__(self, bot):
        self.bot = bot
        self.is_adminlocked = False
        self.is_ownerlocked = False

    # this cog is owner only
    async def cog_check(self, ctx):
        return checks.is_owner(ctx)

    @decorators.command(
        aliases=["conf"],
        brief="Change a config.json value.",
        implemented="2021-03-22 06:59:02.430491",
        updated="2021-05-19 06:10:56.241058",
    )
    async def config(self, ctx, key, value):
        """
        Usage: {0}config <Key to change> <New Value>
        Alias: {0}conf
        Output:
            Edits the specified config.json file key
            to the passed value.
        Notes:
            To reflect the changes of the file change
            immediately, use the {0}botvars command
            instead of rebooting the entire client.
        """
        if value.isdigit():
            utils.modify_config(key=key, value=int(value))
        elif str(value).lower() == "true":
            val = True
        elif str(value).lower() == "false":
            val = False
            utils.modify_config(key=key, value=val)
        else:
            utils.modify_config(key=key, value=str(value))
        await ctx.success(f"Edited key `{key}` to `{value}`")

    @decorators.group(case_insensitive=True, brief="Change the bot's specifications.")
    async def change(self, ctx):
        """
        Usage: {0}change <options> <new>
        Examples:
            {0}change name Tester
            {0}change avatar <url>
        Permission: Bot Owner
        Output: Edits the specified bot attribute.
        Options:
            avatar, nickname, username
            status, activity, presence
        """
        if ctx.invoked_subcommand is None:
            return await ctx.usage()

    @change.command(
        name="username",
        aliases=["name", "user"],
        brief="Change the bot's username.",
    )
    async def change_username(self, ctx, *, name: str):
        try:
            await self.bot.user.edit(username=name)
            await ctx.send_or_reply(
                content=f"Successfully changed username to **{name}**",
            )
        except discord.HTTPException as err:
            await ctx.send_or_reply(err)

    @change.command(name="nickname", brief="Change nickname.")
    @commands.guild_only()
    async def change_nickname(self, ctx, *, name: str = None):
        try:
            await ctx.guild.me.edit(nick=name)
            if name:
                await ctx.send_or_reply(
                    content=f"Successfully changed nickname to **{name}**",
                )
            else:
                await ctx.send_or_reply(
                    content="Successfully removed nickname",
                )
        except Exception as err:
            await ctx.send_or_reply(err)

    @change.command(name="avatar", brief="Change the bot's avatar.")
    async def change_avatar(self, ctx, url: str = None):
        if url is None and len(ctx.message.attachments) == 0:
            return await ctx.send_or_reply(
                content=f"Usage: `{ctx.clean_prefix}change avatar <avatar>`",
            )
        if url is None and len(ctx.message.attachments) == 1:
            url = ctx.message.attachments[0].url
        else:
            url = url.strip("<>") if url else None

        try:
            bio = await self.bot.get(url, res_method="read")
            await self.bot.user.edit(avatar=bio)
            em = discord.Embed(
                description="**Successfully changed the avatar. Currently using:**",
                color=self.bot.constants.embed,
            )
            em.set_image(url=url)
            await ctx.send_or_reply(embed=em)
        except aiohttp.InvalidURL:
            await ctx.send_or_reply(content="Invalid URL.")
        except discord.InvalidArgument:
            await ctx.send_or_reply(
                content="This URL does not contain a useable image.",
            )
        except discord.HTTPException as err:
            await ctx.send_or_reply(err)
        except TypeError:
            await ctx.send_or_reply(
                content="Provide an attachment or a valid URL.",
            )

    @change.command(brief="Change the bot's presence", aliases=["pres"])
    async def presence(self, ctx, *, presence: str = ""):
        if presence == "":
            msg = "Presence has been reset."
        else:
            msg = f"Presence now set to `{presence}`"
        query = """
                UPDATE config
                SET presence = $1
                WHERE client_id = $2;
                """
        await self.bot.cxn.execute(query, presence, self.bot.user.id)
        await self.bot.set_status()
        await ctx.success(msg)

    @change.command(brief="Set the bot's status type.")
    async def status(self, ctx, status: converters.BotStatus):
        query = """
                UPDATE config
                SET status = $1
                WHERE client_id = $2
                """
        await self.bot.cxn.execute(query, status, self.bot.user.id)
        await self.bot.set_status()
        await ctx.success(f"Status now set as `{status}`")

    @change.command(brief="Set the bot's activity type.", aliases=["action"])
    async def activity(self, ctx, activity: converters.BotActivity):
        query = """
                UPDATE config
                SET activity = $1
                WHERE client_id = $2
                """
        await self.bot.cxn.execute(query, activity, self.bot.user.id)
        await self.bot.set_status()
        await ctx.success(f"Status now set as `{activity}`")

    @decorators.group(
        aliases=["set", "add"],
        invoke_without_command=True,
        brief="Write to the bot overview or changelog.",
    )
    async def write(self, ctx):
        """
        Usage: {0}write <method>
        Aliases: {0}set, {0}add
        Methods:
            overview: Edit the bot's overview
            changelog: Post an entry to the changelog
        """
        if ctx.invoked_subcommand is None:
            return await ctx.usage()

    @write.command(brief="Overwrite the bot overview.")
    async def overview(self, ctx, *, overview: str = None):
        if overview is None:
            return await ctx.invoke(self.bot.get_command("overview"))
        if await ctx.confirm("This action will overwrite my current overview."):
            with open("./data/txts/overview.txt", "w", encoding="utf-8") as fp:
                fp.write(overview)
            await ctx.send_or_reply(
                content=f"{self.bot.emote_dict['success']} **Successfully updated overview.**",
            )

    @write.command(brief="Write to the bot changelog.")
    async def changelog(self, ctx, *, entry: str):
        c = await ctx.confirm("This action will post to my changelog.")
        if c:
            with open("./data/txts/changelog.txt", "a", encoding="utf-8") as fp:
                fp.write(f"({discord.utils.utcnow()}) " + entry + "\n")
            await ctx.success(f"**Successfully posted to the changelog.**")

    @write.command(brief="Update the bot readme file.")
    async def readme(self, ctx):
        """
        Usage: {0}readme
        Alias: {0}md
        Output: Sends my readme file on github to your DMs
        Notes:
            This command updates the readme file
            to include all the current command descriptions
            for each registered category.
        """
        mess = await ctx.send_or_reply("Writing readme to **README.md**...")

        owner, cmds, cogs = self.bot.public_stats()
        overview = (
            open("./data/txts/overview.txt")
            .read()
            .format(self.bot.user.name, len(cmds), len(cogs))
        )
        premsg = ""
        premsg += f"# {self.bot.user.name} Moderation & Stat Tracking Discord Bot\n"
        # premsg += "![6010fc1cf1ae9c815f9b09168dbb65a7-1](https://user-images.githubusercontent.com/74381783/108671227-f6d3f580-7494-11eb-9a77-9478f5a39684.png)\n"
        premsg += f"### [Bot Invite Link]({self.bot.oauth})\n"
        premsg += f"### [Support Server]({self.bot.constants.support})\n"
        premsg += (
            "### [DiscordBots.gg](https://discord.bots.gg/bots/806953546372087818)\n"
        )
        premsg += "### [Top.gg](https://top.gg/bot/806953546372087818)\n"
        premsg += "## Overview\n"
        premsg += overview
        premsg += "\n## Categories\n"
        msg = ""

        for cog in cogs:
            premsg += f"##### [{cog.qualified_name}](#{cog.qualified_name}-1)\n"
            cmds = [c for c in cog.get_commands() if not c.hidden]
            if len(cmds) == 0:
                continue

            msg += "\n\n### {}\n#### {} ({} Commands)\n\n```yaml\n{}\n```" "".format(
                cog.qualified_name,
                cog.description,
                len(cmds),
                "\n\n".join(
                    [
                        f"{cmd.qualified_name}: {cmd.brief}"
                        for cmd in sorted(cmds, key=lambda c: c.qualified_name)
                    ]
                ),
            )
        final = premsg + msg

        with open("./README.md", "w", encoding="utf-8") as fp:
            fp.write(final)

        await mess.edit(
            content=f"{self.bot.emote_dict['success']} Successfully updated the README.md file"
        )

    @decorators.command(brief="Blacklist a discord object.")
    async def blacklist(
        self,
        ctx,
        _objects: commands.Greedy[
            typing.Union[discord.User, converters.DiscordGuild, discord.Object]
        ] = None,
        *,
        reason: typing.Optional[str] = None,
    ):
        """
        Usage: {0}blacklist <object> [reason]
        """
        if _objects is None:
            p = pagination.MainMenu(
                pagination.TextPageSource(str(self.bot.blacklist), prefix="```json")
            )
            try:
                await p.start(ctx)
            except menus.MenuError as e:
                await ctx.send_or_reply(e)
            return
        blacklisted = []
        already_blacklisted = []
        for obj in _objects:
            if obj.id in self.bot.owner_ids:
                continue
            if obj.id in self.bot.blacklist:
                already_blacklisted.append(str(obj))
                continue
            self.bot.blacklist[str(obj.id)] = reason if reason else "No reason"
            blacklisted.append(str(obj))
        if blacklisted:
            await ctx.send_or_reply(
                content=f"{self.bot.emote_dict['success']} Blacklisted `{', '.join(blacklisted)}`",
            )
        if already_blacklisted:
            ternary = "was" if len(already_blacklisted) == 1 else "were"
            await ctx.send_or_reply(
                content=f"{self.bot.emote_dict['success']} `{', '.join(already_blacklisted)}` {ternary} already blacklisted",
            )

    @decorators.command(brief="Unblacklist discord objects.")
    async def unblacklist(
        self, ctx, _object: typing.Union[discord.User, converters.DiscordGuild]
    ):
        """
        Usage: {0}unblacklist <object>
        """
        try:
            self.bot.blacklist.pop(str(_object.id))
        except KeyError:
            await ctx.success(f"`{str(_object)}` was not blacklisted.")
            return
        await ctx.success(f"Removed `{str(_object)}` from the blacklist.")

    @decorators.command(brief="Show blacklisted objects.")
    async def blacklisted(self, ctx):
        """
        Usage: {0}blacklisted
        Output: Shows which users are blacklisted globally.
        """
        if not self.bot.blacklist:
            return await ctx.success("No objects are blacklisted.")
        p = pagination.TextPages(json.dumps(self.bot.blacklist), prefix="```json")
        try:
            await p.start(ctx)
        except menus.MenuError as e:
            await ctx.send(e)

    @decorators.command(brief="Toggle disabling a command.")
    async def toggle(self, ctx, *, command):
        """
        Usage: {0}toggle <command>
        Output: Globally disables or enables a command
        """
        EXCEPTIONS = ["toggle"]
        command = self.bot.get_command(command)
        if command is None:
            return await ctx.send_or_reply(
                content=f"Usage: `{ctx.clean_prefix}toggle <command>`",
            )
        if command.name in EXCEPTIONS:
            return await ctx.send_or_reply(
                content=f"{self.bot.emote_dict['warn']} command {command.qualified_name} cannot be disabled.",
            )

        command.enabled = not command.enabled
        ternary = "Enabled" if command.enabled else "Disabled"
        await ctx.success(f"{ternary} {command.qualified_name}.")

    @decorators.command(brief="Have the bot leave a server.")
    async def leaveserver(self, ctx, *, target_server: converters.DiscordGuild = None):
        """Leaves a server - can take a name or id (owner only)."""

        c = await ctx.confirm(
            f"This action will result in me leaving the server: `{target_server.name}`"
        )

        if c:
            await target_server.leave()
            try:
                await ctx.success(
                    f"**Successfully left the server:** `{target_server.name}`"
                )
            except Exception:
                return
            return

    @decorators.command(brief="Add a new bot owner.")
    async def addowner(self, ctx, *, member: converters.DiscordUser):
        """
        Usage: {0}addowner <user>
        Permission: Hecate#3523
        Output:
            Adds the passed user's ID to the owners key
            in the config.json file
        Notes:
            USE WITH CAUTION! This will allow the user
            to access all commands including those with
            root privileges. To reflect changes instantly, use the
            {0}botvars command
        """
        if ctx.author.id is not self.bot.developer_id:
            return
        if member.bot:
            raise commands.BadArgument("I cannot be owned by a bot.")

        data = utils.load_json("config.json")
        current_owners = data["owners"]

        if member.id in current_owners:
            return await ctx.send_or_reply(
                content=f"{self.bot.emote_dict['warn']} **`{member}` is already an owner.**",
            )

        c = await ctx.confirm(f"This action will add `{member}` as an owner.")
        if c:
            current_owners.append(member.id)
            utils.modify_config("owners", current_owners)
            await ctx.success(f"**`{member}` is now officially one of my owners.**")
            return

    @decorators.command(
        aliases=["removeowner", "rmowner"],
        brief="Remove a user from my owner list.",
    )
    async def remowner(self, ctx, *, member: converters.DiscordUser):
        """
        Usage: {0}remowner <user>
        Aliases: {0}removeowner, -rmowner
        Permission: Hecate#3523
        Output:
            Removes a user from the owners key in
            my config.json file
        Notes:
            To reflect changes instantly, use the
            {0}botvars command
        """
        if ctx.author.id is not self.bot.developer_id:
            return

        data = utils.load_json("config.json")
        current_owners = data["owners"]

        if member.id not in current_owners:
            return await ctx.send_or_reply(
                content=f"{self.bot.emote_dict['warn']} **`{member}` is not an owner.**",
            )

        c = await ctx.confirm(
            f"This action will remove `{member}` from the owner list."
        )

        if c:
            index = current_owners.index(member.id)
            current_owners.pop(index)
            utils.modify_config("owners", current_owners)
            await ctx.success(
                f"**Successfully removed `{member}` from my owner list.**"
            )
            return

    @decorators.command(brief="Add a new bot admin.")
    async def addadmin(self, ctx, *, member: converters.DiscordUser):
        """
        Usage: {0}addadmin <user>
        Permission: Hecate#3523
        Output:
            Adds the passed user's ID to the admins key
            in the config.json file
        Notes:
            USE WITH CAUTION! This will allow the user
            to access global bot information. This includes
            s complete server list, member list, etc.
            To reflect changes instantly, use {0}botvars.
        """
        if ctx.author.id is not self.bot.developer_id:
            return

        if member.bot:
            raise commands.BadArgument(f"I cannot be owned by a bot.")

        data = utils.load_json("config.json")
        current_admins = data["admins"]

        if member.id in current_admins:
            return await ctx.send_or_reply(
                content=f"{self.bot.emote_dict['warn']} **`{member}` is already an admin.**",
            )

        c = await ctx.confirm(f"This action will add `{member}` as an admin.")

        if c:
            current_admins.append(member.id)
            utils.modify_config("admins", current_admins)
            await ctx.success(f"**`{member}` is now officially one of my admins.**")
            return

    @decorators.command(aliases=["removeadmin", "rmadmin"], brief="Remove a bot admin.")
    async def remadmin(self, ctx, *, member: converters.DiscordUser):
        """
        Usage: {0}remadmin <user>
        Aliases: {0}removeadmin, {0}rmadmin
        Permission: Hecate#3523
        Output:
            Removes a user from the admins key in
            my config.json file
        Notes:
            To reflect changes instantly, use the
            {0}botvars command
        """
        if ctx.author.id is not self.bot.developer_id:
            return

        data = utils.load_json("config.json")
        current_admins = data["admins"]

        if member.id not in current_admins:
            return await ctx.send_or_reply(
                content=f"{self.bot.emote_dict['warn']} **`{member}` is not an admin.**",
            )

        c = await ctx.confirm(
            f"This action will remove `{member}` from the admin list."
        )

        if c:
            index = current_admins.index(member.id)
            current_admins.pop(index)
            utils.modify_config("admins", current_admins)
            await ctx.success(
                f"**Successfully removed `{member}` from my admin list.**"
            )
            return

    @decorators.command(brief="Owner-lock the bot.")
    async def ownerlock(self, ctx):
        """
        Usage: {0}ownerlock
        """
        query = """
                UPDATE config
                SET ownerlocked = $1
                WHERE client_id = $2;
                """
        if self.is_ownerlocked is True:
            self.is_ownerlocked = False
            await self.bot.cxn.execute(query, False, self.bot.user.id)
            return await ctx.success(f"**Ownerlock Disabled.**")
        else:
            c = await ctx.confirm(
                f"This action will prevent usage from all except my owners."
            )
            if c:
                self.is_ownerlocked = True
                await self.bot.cxn.execute(query, True, self.bot.user.id)
                await ctx.success(f"**Ownerlock Enabled.**")
                return

    @decorators.command(brief="Admin-lock the bot.")
    async def adminlock(self, ctx):
        """
        Usage: {0}adminlock
        """
        if self.is_adminlocked is True:
            self.is_adminlocked = False
            return await ctx.success("**Adminlock Disabled.**")
        else:
            c = await ctx.confirm(
                f"This action will prevent usage from all except my admins."
            )
            if c:
                self.is_adminlocked = True
                await ctx.success(f"**Adminlock Enabled.**")
                return

    async def bot_check(self, ctx):
        if checks.is_owner(ctx):
            return True

        if self.is_ownerlocked is True:
            await ctx.react(self.bot.emote_dict["lock"])
            return False

        if self.is_adminlocked is True:
            if checks.is_admin(ctx):
                return True
            await ctx.react(self.bot.emote_dict["lock"])
            return False

        return True
