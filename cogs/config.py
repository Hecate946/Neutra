import os
import time
import typing
import aiohttp
import discord

from datetime import datetime
from discord.ext import commands, menus

from utilities import utils
from utilities import checks
from utilities import converters
from utilities import decorators
from utilities import pagination


def setup(bot):
    bot.add_cog(Config(bot))


class Config(commands.Cog):
    """
    Owner only configuration cog.
    """

    def __init__(self, bot):
        self.bot = bot
        self.is_ownerlocked = False
        self.todo = "./data/txts/todo.txt"

    # this cog is owner only
    async def cog_check(self, ctx):
        return checks.is_owner(ctx)


    @decorators.command(
        brief="Change a config.json value.",
        implemented="2021-03-22 06:59:02.430491",
        updated="2021-05-19 06:10:56.241058",
    )
    async def config(self, ctx, key=None, value=None):
        """
        Usage: {0}config <Key to change> <New Value>
        Output:
            Edits the specified config.json file key
            to the passed value.
        Notes:
            To reflect the changes of the file change
            immediately, use the -refresh command
            instead of rebooting the entire client.
        """
        if key is None or value is None:
            return await ctx.send_or_reply(
                content=f"Enter a value to edit and its new value.",
            )
        if value.isdigit():
            utils.modify_config(key=key, value=int(value))
        elif type(value) is bool:
            utils.modify_config(key=key, value=bool(value))
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
                content=f"Usage: `{ctx.prefix}change avatar <avatar>`",
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
        if ctx.author.id not in self.bot.constants.owners:
            return None
        if presence == "":
            msg = "presence has been reset."
        else:
            msg = f"presence now set to `{presence}`"
        query = """
                UPDATE config
                SET presence = $1
                WHERE client_id = $2;
                """
        await self.bot.cxn.execute(query, presence, self.bot.user.id)
        await self.bot.set_status()
        await ctx.success(msg)

    @change.command(brief="Set the bot's status type.")
    async def status(self, ctx, status: str = None):
        if ctx.author.id not in self.bot.constants.owners:
            return

        if status.lower() in ["online", "green"]:
            status = "online"
        elif status.lower() in ["idle", "moon", "sleep", "yellow"]:
            status = "idle"
        elif status.lower() in ["dnd", "do-not-disturb", "do_not_disturb", "red"]:
            status = "dnd"
        elif status.lower() in ["offline", "gray", "invisible", "invis"]:
            status = "offline"
        else:
            raise commands.BadArgument(f"`{status}` is not a valid status.")

        query = """
                UPDATE config
                SET status = $1
                WHERE client_id = $2;
                """
        await self.bot.cxn.execute(query, status, self.bot.user.id)
        await self.bot.set_status()
        me = self.bot.home.get_member(self.bot.user.id)
        query = """
                INSERT INTO botstats
                VALUES ($1)
                ON CONFLICT (bot_id)
                DO UPDATE SET {0} = botstats.{0} + $2
                """.format(
            me.status
        )

        statustime = time.time() - self.bot.statustime
        await self.bot.cxn.execute(query, self.bot.user.id, statustime)
        self.bot.statustime = time.time()
        await ctx.success(f"status now set as `{status}`")

    @change.command(brief="Set the bot's activity type.", aliases=["action"])
    async def activity(self, ctx, activity: str = None):

        if activity.lower() in ["play", "playing", "game", "games"]:
            activity = "playing"
        elif activity.lower() in ["listen", "listening", "hearing", "hear"]:
            activity = "listening"
        elif activity.lower() in ["watch", "watching", "looking", "look"]:
            activity = "watching"
        elif activity.lower() in ["comp", "competing", "compete"]:
            activity = "competing"
        else:
            raise commands.BadArgument(f"`{activity}` is not a valid status.")

        query = """
                UPDATE config
                SET activity = $1
                WHERE client_id = $2;
                """
        await self.bot.cxn.execute(query, activity, self.bot.user.id)
        await self.bot.set_status()
        await ctx.success(f"Status now set as `{activity}`")

    @decorators.group(
        case_insensitive=True,
        aliases=["to-do"],
        invoke_without_command=True,
        brief="Manage the bot's todo list.",
    )
    async def todo(self, ctx):
        """
        Usage: {0}todo <method>
        Alias: {0}to-do
        Methods:
            no subcommand: shows the todo list
            add: Adds an entry to the todo list
            remove|rm|rem: Removes an entry from the todo list
        """
        if ctx.invoked_subcommand is None:
            try:
                with open(self.todo) as fp:
                    data = fp.readlines()
            except FileNotFoundError:
                return await ctx.send_or_reply(
                    f"{self.bot.emote_dict['exclamation']} No current todos."
                )
            if data is None or data == "":
                return await ctx.send_or_reply(
                    f"{self.bot.emote_dict['exclamation']} No current todos."
                )
            msg = ""
            for index, line in enumerate(data, start=1):
                msg += f"{index}. {line}\n"
            p = pagination.MainMenu(
                pagination.TextPageSource(msg, prefix="```prolog\n")
            )
            try:
                await p.start(ctx)
            except menus.MenuError as e:
                await ctx.send_or_reply(e)

    @todo.command()
    async def add(self, ctx, *, todo: str = None):
        if todo is None:
            return await ctx.send_or_reply(
                content=f"Usage: `{ctx.prefix}todo add <todo>`",
            )
        with open(self.todo, "a", encoding="utf-8") as fp:
            fp.write(todo + "\n")
        await ctx.send_or_reply(
            f"{self.bot.emote_dict['success']} Successfully added `{todo}` to the todo list."
        )

    @todo.command(aliases=["rm", "rem"])
    async def remove(self, ctx, *, index_or_todo: str = None):
        if index_or_todo is None:
            return await ctx.send_or_reply(
                content=f"Usage: `{ctx.prefix}todo remove <todo>`",
            )
        with open(self.todo, mode="r", encoding="utf-8") as fp:
            lines = fp.readlines()
            print(lines)
        found = False
        for index, line in enumerate(lines, start=1):
            if str(index) == index_or_todo:
                lines.remove(line)
                found = True
                break
            elif line.lower().strip("\n") == index_or_todo.lower():
                lines.remove(line)
                found = True
                break
        if found is True:
            with open(self.todo, mode="w", encoding="utf-8") as fp:
                print(lines)
                fp.write("".join(lines))
            await ctx.send_or_reply(
                content=f"{self.bot.emote_dict['success']} Successfully removed todo `{index_or_todo}` from the todo list.",
            )
        else:
            await ctx.send_or_reply(
                content=f"{self.bot.emote_dict['failed']} Could not find todo `{index_or_todo}` in the todo list.",
            )

    @todo.command()
    async def clear(self, ctx):
        try:
            os.remove(self.todo)
        except FileNotFoundError:
            return await ctx.send_or_reply(
                content=f"{self.bot.emote_dict['success']} Successfully cleared the todo list.",
            )
        await ctx.send_or_reply(
            f"{self.bot.emote_dict['success']} Successfully cleared the todo list."
        )

    @decorators.group(
        case_insensitive=True,
        aliases=["set", "add"],
        invoke_without_command=True,
        brief="Write to the bot's overview or changelog.",
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

    @write.command()
    async def overview(self, ctx, *, overview: str = None):
        if overview is None:
            return await ctx.invoke(self.bot.get_command("overview"))
        c = await pagination.Confirmation(
            f"**{self.bot.emote_dict['exclamation']} This action will overwrite my current overview. Do you wish to continue?**"
        ).prompt(ctx)
        if c:
            with open("./data/txts/overview.txt", "w", encoding="utf-8") as fp:
                fp.write(overview)
            await ctx.send_or_reply(
                content=f"{self.bot.emote_dict['success']} **Successfully updated overview.**",
            )
        else:
            await ctx.send_or_reply(
                content=f"{self.bot.emote_dict['exclamation']} **Cancelled.**",
            )

    @write.command()
    async def changelog(self, ctx, *, entry: str = None):
        if entry is None:
            return await ctx.send_or_reply(
                content=f"Usage: `{ctx.prefix}write changelog <entry>`",
            )
        c = await pagination.Confirmation(
            f"**{self.bot.emote_dict['exclamation']} This action will post to my changelog. Do you wish to continue?**"
        ).prompt(ctx)
        if c:
            with open("./data/txts/changelog.txt", "a", encoding="utf-8") as fp:
                fp.write(f"({datetime.utcnow()}+00:00) " + entry + "\n")
            await ctx.send_or_reply(
                content=f"{self.bot.emote_dict['success']} **Successfully posted to the changelog.**",
            )
        else:
            await ctx.send_or_reply(
                content=f"{self.bot.emote_dict['exclamation']} **Cancelled.**",
            )

    @decorators.command(brief="Blacklist a discord object.")
    async def blacklist(
        self,
        ctx,
        _objects: commands.Greedy[
            typing.Union[discord.User, converters.DiscordGuild]
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
        self, ctx, _object: typing.Union[discord.User, converters.DiscordGuild]):
        """
        Usage: {0}unblacklist <object>
        """
        try:
            self.bot.blacklist.pop(str(_object.id))
        except KeyError:
            await ctx.success(f"`{str(_object)}` was not blacklisted.")
            return
        await ctx.success(f"Removed `{str(_object)}` from the blacklist.")

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
                content=f"Usage: `{ctx.prefix}toggle <command>`",
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

        c = await ctx.confirm(f"This action will result in me leaving the server: `{target_server.name}`")

        if c:
            await target_server.leave()
            try:
                await ctx.success(f"**Successfully left the server:** `{target_server.name}`")
            except Exception:
                return
            return
        

    @decorators.command(brief="Add a new bot owner.")
    async def addowner(self, ctx, member: converters.DiscordUser):
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
        if ctx.author.id is not self.bot.hecate.id:
            return
        if member.bot:
            raise commands.BadArgument(f"I cannot be owned by a bot.")

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
    async def remowner(self, ctx, member: converters.DiscordUser):
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
        if ctx.author.id is not self.bot.hecate.id:
            return

        data = utils.load_json("config.json")
        current_owners = data["owners"]

        if member.id not in current_owners:
            return await ctx.send_or_reply(
                content=f"{self.bot.emote_dict['warn']} **`{member}` is not an owner.**",
            )

        c = await ctx.confirm(f"This action will remove `{member}` from the owner list.")

        if c:
            index = current_owners.index(member.id)
            current_owners.pop(index)
            utils.modify_config("owners", current_owners)
            await ctx.success(f"**Successfully removed `{member}` from my owner list.**")
            return

    @decorators.command(brief="Add a new bot admin.")
    async def addadmin(self, ctx, member: converters.DiscordUser):
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
        if ctx.author.id is not self.bot.hecate.id:
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

    @decorators.command(
        aliases=["removeadmin", "rmadmin"], brief="Remove a bot admin."
    )
    async def remadmin(self, ctx, member: converters.DiscordUser):
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
        if ctx.author.id is not self.bot.hecate.id:
            return

        data = utils.load_json("config.json")
        current_admins = data["admins"]

        if member.id not in current_admins:
            return await ctx.send_or_reply(
                content=f"{self.bot.emote_dict['warn']} **`{member}` is not an admin.**",
            )

        c = await ctx.confirm(f"This action will remove `{member}` from the admin list.")

        if c:
            index = current_admins.index(member.id)
            current_admins.pop(index)
            utils.modify_config("admins", current_admins)
            await ctx.success(f"**Successfully removed `{member}` from my admin list.**")
            return

    @decorators.command(brief="Toggle locking the bot to owners.")
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
            c = await ctx.confirm(f"This action will prevent usage from all except my owners.")
            if c:
                self.is_ownerlocked = True
                await self.bot.cxn.execute(query, True, self.bot.user.id)
                await ctx.success(f"**Ownerlock Enabled.**")
                return

    async def message(self, message):
        # Check the message and see if we should allow it
        ctx = await self.bot.get_context(message)
        if not ctx.command:
            # No command - no need to check
            return
        if self.is_ownerlocked is True:
            if not checks.is_owner(ctx):
                return {
                    "Ignore": True,
                    "Delete": False,
                    "React": [self.bot.emote_dict["failed"]],
                }
