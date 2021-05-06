import asyncio
import inspect
import discord
import traceback

from datetime import datetime
from discord.ext import commands, menus

from utilities import utils
from utilities import checks
from utilities import converters
from utilities import decorators
from utilities import pagination


def setup(bot):
    bot.remove_command("help")
    bot.add_cog(Commands(bot))


class Commands(commands.Cog):
    """
    My extensive help category.
    """

    def __init__(self, bot):
        self.bot = bot
        self.command_exceptions = []  # pass command names to hide from help command

    ############################
    ## Get Commands From Cogs ##
    ############################

    async def send_help(self, ctx, embed, pm, delete_after):
        if pm is True:  # We're DMing the user
            if not ctx.guild:  # They invoked from a DM
                msg = await ctx.send_or_reply(embed=embed)
                return
            try:
                msg = await ctx.author.send(embed=embed)
                try:
                    await ctx.message.add_reaction(self.bot.emote_dict["letter"])
                except Exception: # Probably no perms. Ignore
                    pass
            except Exception:  # Couldn't send the message to the user. Send it to the channel.
                msg = await ctx.send_or_reply(
                    embed=embed,
                    delete_after=delete_after,
                )
        else: # Not trying to DM the user, send to the channel.
            msg = await ctx.send_or_reply(embed=embed, delete_after=delete_after)

        def reaction_check(m):
            if (
                m.message_id == msg.id  # Same message
                and m.user_id == ctx.author.id  # Only the author
                and str(m.emoji) == self.bot.emote_dict["trash"]  # Same emoji
            ):
                return True
            return False

        try:
            await msg.add_reaction(self.bot.emote_dict["trash"])
        except discord.Forbidden:
            return  # Can't react so give up.

        try:
            await self.bot.wait_for(
                "raw_reaction_add", timeout=60.0, check=reaction_check
            )
            await msg.delete()
        except asyncio.TimeoutError:  # Been a minute.
            try:
                await msg.clear_reactions()
            except Exception:  # No perms to clear rxns, delete manually.
                await msg.remove_reaction(self.bot.emote_dict["trash"], self.bot.user)

    async def helper_func(self, ctx, cog, name, pm, delete_after):
        the_cog = sorted(cog.get_commands(), key=lambda x: x.name)
        cog_commands = []
        for c in the_cog:
            if c.hidden and not checks.is_admin(ctx):
                continue
            if str(c.name).upper() in self.command_exceptions and not checks.is_admin(ctx):
                await ctx.send_or_reply(
                    f"{self.bot.emote_dict['warn']} No command named `{name}` found."
                )
                continue
            cog_commands.append(c)
        if cog_commands:
            await self.category_embed(
                ctx,
                cog=cog.qualified_name,
                list=cog_commands,
                pm=pm,
                delete_after=delete_after,
            )
            return
        else:
            return await ctx.send_or_reply(
                content=f"{self.bot.emote_dict['warn']} No command named `{name}` found.",
            )

    ##########################
    ## Build Category Embed ##
    ##########################

    async def category_embed(self, ctx, cog, list, pm, delete_after):
        embed = discord.Embed(
            title=f"Category: `{cog}`",
            description=f"**Bot Invite Link:** [https://snowbot.discord.bot]({self.bot.oauth})\n"
            f"**Support Server:**  [https://discord.gg/snowbot]({self.bot.constants.support})\n",
            color=self.bot.constants.embed,
        )
        embed.set_footer(
            text=f'Use "{ctx.prefix}help command" for information on a command.\n'
        )

        msg = ""
        for i in list:
            if not i.brief or i.brief == "":
                i.brief = "No description"
            line = f"\n`{i.name}` {i.brief}\n"
            if ctx.guild:
                if (
                    i.name
                    not in self.bot.server_settings[ctx.guild.id]["disabled_commands"]
                ):
                    msg += line
                else:
                    msg += f"\n[!] `{i.name}` ~~{i.brief}~~\n"
            else:
                msg += line

        embed.add_field(name=f"**{cog} Commands**", value=f"** **{msg}")
        try:
            await self.send_help(ctx, embed, pm, delete_after)
        except discord.Forbidden:
            pass

    @decorators.command(
        name="help",
        aliases=["commands", "documentation", "docs", "helpme"],
        brief="My documentation for all commands.",
        implemented="2021-02-22 05:04:47.433000",
        updated="2021-05-05 05:08:05.642637",
    )
    async def _help(self, ctx, *, invokercommand: str = None):
        """
        Usage:  -help [command/category] [pm = true]
        Output: HELP!
        """
        delete_after = None
        pm = False

        if ctx.guild:
            if not ctx.guild.me.permissions_in(ctx.channel).embed_links:
                pm = True

        if invokercommand:
            trigger = True
        else:
            trigger = None

        if trigger is None:

            ##########################
            ## Manages General Help ##
            ##########################

            embed = discord.Embed(
                title=f"{self.bot.user.name}'s Help Command",
                url="https://discord.gg/947ramn",
                description=f"**Bot Invite Link:** [https://snowbot.discord.bot]({self.bot.oauth})\n"
                f"**Support Server:**  [https://discord.gg/snowbot]({self.bot.constants.support})",
                color=self.bot.constants.embed,
            )

            embed.set_footer(
                text=f'Use "{ctx.prefix}help category" for information on a category.'
            )

            valid_cogs = []
            msg = ""
            for cog in sorted(self.bot.cogs):
                c = self.bot.get_cog(cog)
                command_list = c.get_commands()
                if c.qualified_name.upper() in self.bot.cog_exceptions:
                    continue
                if (
                    c.qualified_name.upper() in self.bot.useless_cogs
                    or len(command_list) == 0
                ):
                    continue
                valid_cogs.append(c)
            for c in valid_cogs:
                line = f"\n`{c.qualified_name}` {c.description}\n"
                if ctx.guild:
                    disabled_comms = self.bot.server_settings[ctx.guild.id][
                        "disabled_commands"
                    ]
                    cog_comms = [y.name for y in c.get_commands() if not y.hidden]
                    if all(x in disabled_comms for x in cog_comms):
                        msg += f"\n[!] `{c.qualified_name}` ~~{c.description}~~\n"
                    else:
                        msg += line
                else:
                    msg += line

            embed.add_field(name=f"**Current Categories**", value=f"** **{msg}**\n**")
            if not checks.is_admin(ctx):
                await self.send_help(ctx, embed, pm, delete_after)
            else:
                hidden_cogs = []
                msg = ""
                for cog in sorted(self.bot.cogs):
                    c = self.bot.get_cog(cog)
                    command_list = c.get_commands()
                    if c.qualified_name.upper() in self.bot.cog_exceptions:
                        hidden_cogs.append(c)
                for c in hidden_cogs:
                    if c.qualified_name.upper() == "JISHAKU":
                        continue  # We don't need jishaku showing up in help
                    line = f"\n`{c.qualified_name}` {c.description}\n"
                    msg += line
                embed.add_field(
                    name=f"**Hidden Categories**", value=f"** **{msg}", inline=False
                )

                await self.send_help(ctx, embed, pm, delete_after)

        elif trigger is True:

            if invokercommand.lower() in [
                "category",
                "command",
                "group",
                "subcommand",
            ]:  # Someone took the embed footer too literally.
                await ctx.fail(f"Please specify a valid {invokercommand.lower()} name.")
            ######################
            ## Manages Cog Help ##
            ######################

            if invokercommand.lower() in [
                "admin",
                "administration",
                "administrator",
                "restrict",
                "restriction",
                "disabling",
                "settings",
                "configuration",
            ]:
                cog = self.bot.get_cog("Admin")
                return await self.helper_func(
                    ctx, cog=cog, name=invokercommand, pm=pm, delete_after=delete_after
                )

            if invokercommand.lower() in [
                "bot",
                "bots",
                "info",
                "about",
                "robot",
                "information",
            ]:
                cog = self.bot.get_cog("Info")
                return await self.helper_func(
                    ctx, cog=cog, name=invokercommand, pm=pm, delete_after=delete_after
                )

            if invokercommand.lower() in [
                "help",
                "helpme",
                "assist",
                "assistance",
                "commands",
                "cmds",
            ]:
                cog = self.bot.get_cog("Commands")
                return await self.helper_func(
                    ctx, cog=cog, name=invokercommand, pm=pm, delete_after=delete_after
                )

            if invokercommand.lower() in [
                "dump",
                "files",
                "file",
                "txt",
                "txts",
                "dumps",
            ]:
                cog = self.bot.get_cog("Files")
                return await self.helper_func(
                    ctx, cog=cog, name=invokercommand, pm=pm, delete_after=delete_after
                )

            if invokercommand.lower() in ["logging", "logger", "logs"]:
                cog = self.bot.get_cog("Logging")
                return await self.helper_func(
                    ctx, cog=cog, name=invokercommand, pm=pm, delete_after=delete_after
                )

            if invokercommand.lower() in [
                "mod",
                "moderator",
                "punishment",
                "moderation",
                "punish",
            ]:
                cog = self.bot.get_cog("Mod")
                return await self.helper_func(
                    ctx, cog=cog, name=invokercommand, pm=pm, delete_after=delete_after
                )

            if invokercommand.lower() in [
                "general",
                "utility",
                "utils",
                "util",
                "utilities",
                "tools",
                "miscellaneous",
                "random",
                "misc",
            ]:
                cog = self.bot.get_cog("Utility")
                return await self.helper_func(
                    ctx, cog=cog, name=invokercommand, pm=pm, delete_after=delete_after
                )

            if invokercommand.lower() in [
                "times",
                "time",
                "timezones",
            ]:
                cog = self.bot.get_cog("Time")
                return await self.helper_func(
                    ctx, cog=cog, name=invokercommand, pm=pm, delete_after=delete_after
                )

            if invokercommand.lower() in ["roles", "role", "serverroles"]:
                cog = self.bot.get_cog("Roles")
                return await self.helper_func(
                    ctx, cog=cog, name=invokercommand, pm=pm, delete_after=delete_after
                )

            if invokercommand.lower() in [
                "server",
                "serverstats",
                "stats",
                "servers",
                "statistics",
            ]:
                cog = self.bot.get_cog("Stats")
                return await self.helper_func(
                    ctx, cog=cog, name=invokercommand, pm=pm, delete_after=delete_after
                )

            if invokercommand.lower() in [
                "track",
                "users",
                "tracking",
                "userstats",
                "user",
            ]:
                cog = self.bot.get_cog("Tracking")
                return await self.helper_func(
                    ctx, cog=cog, name=invokercommand, pm=pm, delete_after=delete_after
                )

            # if invokercommand.lower() in [
            #     "conversions",
            #     "conversion",
            #     "encoding",
            #     "encryption",
            #     "decryption",
            #     "decrypt",
            # ]:
            #     cog = self.bot.get_cog("Conversion")
            #     return await self.helper_func(
            #         ctx, cog=cog, name=invokercommand, pm=pm, delete_after=delete_after
            #     )


            if invokercommand.lower() in [
                "automod",
                "warning",
                "auto",
                "automoderation",
                "system",
            ]:
                cog = self.bot.get_cog("Automod")
                return await self.helper_func(
                    ctx, cog=cog, name=invokercommand, pm=pm, delete_after=delete_after
                )

            if invokercommand.lower() in ["jsk", "jish", "jishaku"]:
                if not checks.is_owner(ctx): # Jishaku is owner-only
                    return await ctx.send_or_reply(  # Pretend like it doesn't exist
                        f"{self.bot.emote_dict['warn']} No command named `{invokercommand}` found."
                    )
                return await ctx.send_help("jishaku")

            if invokercommand.lower() in ["conf", "config", "owner"]:
                if not checks.is_owner(ctx):
                    return await ctx.send_or_reply(
                        f"{self.bot.emote_dict['warn']} No command named `{invokercommand}` found."
                    )
                cog = self.bot.get_cog("Config")
                return await self.helper_func(
                    ctx, cog=cog, name=invokercommand, pm=pm, delete_after=delete_after
                )

            if invokercommand.lower() in ["botadmin","badmin"]:
                if not checks.is_admin(ctx):
                    return await ctx.send_or_reply(
                        f"{self.bot.emote_dict['warn']} No command named `{invokercommand}` found."
                    )
                cog = self.bot.get_cog("Botadmin")
                return await self.helper_func(
                    ctx, cog=cog, name=invokercommand, pm=pm, delete_after=delete_after
                )

            if invokercommand.lower() in ["manage", "manager", "master", "heart"]:
                if not checks.is_owner(ctx):
                    return await ctx.send_or_reply(
                        f"{self.bot.emote_dict['warn']} No command named `{invokercommand}` found."
                    )
                cog = self.bot.get_cog("Manager")
                return await self.helper_func(
                    ctx, cog=cog, name=invokercommand, pm=pm, delete_after=delete_after
                )

            ##########################
            ## Manages Command Help ##
            ##########################
            else:
                valid_cog = ""
                valid_commands = ""
                valid_help = ""
                valid_brief = ""
                for cog in sorted(self.bot.cogs):
                    cog_commands = sorted(
                        self.bot.get_cog(cog).get_commands(), key=lambda x: x.name
                    )
                    for command in cog_commands:
                        if (
                            str(command.name) == invokercommand.lower()
                            or invokercommand.lower() in command.aliases
                        ):
                            if (
                                command.hidden
                                and ctx.author.id not in self.bot.constants.owners
                            ):
                                continue
                            if isinstance(command, commands.Group):
                                await self.send_group_help(
                                    ctx, invokercommand, command, None, pm, delete_after
                                )
                                return
                            valid_commands += command.name
                            valid_help += command.help
                            if not command.brief:
                                command.brief = "None"
                            valid_brief += command.brief
                            valid_cog += str(command.cog.qualified_name)
                        else:
                            args = invokercommand.split()
                            if len(args) > 1:
                                if command.name == args[0]:
                                    if isinstance(command, commands.Group):
                                        return await self.send_group_help(
                                            ctx,
                                            invokercommand,
                                            command,
                                            args[1],
                                            pm,
                                            delete_after,
                                        )

                if valid_commands != "":
                    help_embed = discord.Embed(
                        title=f"Category: `{valid_cog.title()}`",
                        description=f"**Bot Invite Link:** [https://snowbot.discord.bot]({self.bot.oauth})\n"
                        f"**Support Server:**  [https://discord.gg/snowbot]({self.bot.constants.support})",
                        color=self.bot.constants.embed,
                    )
                    help_embed.set_footer(
                        text=f'Use "{ctx.prefix}help category" for information on a category.'
                    )
                    help_embed.add_field(
                        name=f"**Command Name:** `{valid_commands.title()}`\n**Description:** `{valid_brief}`\n",
                        value=f"** **" f"```yaml\n{valid_help.format(ctx.prefix)}```",
                    )
                    await self.send_help(ctx, help_embed, pm, delete_after)
                    return
                else:
                    await ctx.send_or_reply(
                        f"{self.bot.emote_dict['warn']} No command named `{invokercommand}` found."
                    )

    async def send_group_help(
        self, ctx, invokercommand, command, subcommand, pm, delete_after
    ):
        if subcommand:
            found = False
            for x in command.commands:
                if (
                    x.name.lower() == subcommand.lower()
                    or subcommand.lower() in x.aliases
                ):
                    found = True
                    if not x.brief or x.brief == "":
                        brief = "No description"
                    else:
                        brief = x.brief

                    if not x.help or x.help == "":
                        _help = "No help"
                    else:
                        _help = x.help.format(ctx.prefix)
                    help_embed = discord.Embed(
                        title=f"Category: `{str(command.cog.qualified_name).title()}`",
                        description=f"**Bot Invite Link:** [https://snowbot.discord.bot]({self.bot.oauth})\n"
                        f"**Support Server:**  [https://discord.gg/snowbot]({self.bot.constants.support})",
                        color=self.bot.constants.embed,
                    )
                    help_embed.set_footer(
                        text=f'Use "{ctx.prefix}help category" for information on a category.'
                    )
                    help_embed.add_field(
                        name=f"**Command Group:** `{command.name.title()}`\n**Subcommand:** `{x.name.title()}`\n**Description:** `{brief}`",
                        value=f"** **" f"```yaml\n{_help}```",
                        inline=False,
                    )
                    return await self.send_help(ctx, help_embed, pm, delete_after)
            if not found:
                await ctx.send_or_reply(
                    f"{self.bot.emote_dict['warn']} No command named `{invokercommand}` found."
                )
                return

        if not command.brief or command.brief == "":
            brief = "No description"
        else:
            brief = command.brief
        if not command.help or command.help == "":
            _help = "No help"
        else:
            _help = command.help.format(ctx.prefix)
        help_embed = discord.Embed(
            title=f"Category: `{str(command.cog.qualified_name).title()}`",
            description=f"**Bot Invite Link:** [https://snowbot.discord.bot]({self.bot.oauth})\n"
            f"**Support Server:**  [https://discord.gg/snowbot]({self.bot.constants.support})",
            color=self.bot.constants.embed,
        )
        help_embed.set_footer(
            text=f'Use "{ctx.prefix}help {command.name} option" for information on a option.'
        )
        help_embed.add_field(
            name=f"**Command Group:** `{command.name.title()}`\n**Description:** `{brief}`\n",
            value=f"** **" f"```yaml\n{_help}```",
            inline=False,
        )
        return await self.send_help(ctx, help_embed, pm, delete_after)

    @decorators.command(
        brief="Get the short description of a command.",
        aliases=["shortdoc", "shortdocs"],
        implemented="2021-05-03 02:26:36.434933",
        updated="2021-05-05 04:28:36.454921",
    )
    async def brief(self, ctx, command: converters.DiscordCommand):
        """
        Usage: {0}brief <command>
        Aliases: {0}shortdocs, {0}shortdoc
        Output:
            The short description of the passed command
        """
        await ctx.send_or_reply(
            content=f"{self.bot.emote_dict['announce']} Command brief for **{command.name}**: `{command.brief}`",
        )

    @decorators.command(
        brief="See if a command can be executed.",
        aliases=["checker"],
        implemented="2021-05-03 02:26:36.434933",
        updated="2021-05-05 04:28:36.454933",
    )
    async def canrun(self, ctx, command: converters.DiscordCommand):
        """
        Usage: {0}canrun <command>
        Alias: {0}checker
        Output:
            Tells you whether or not you have
            permission to run a command
        """
        if await command.can_run(ctx):
            await ctx.success(f"You can successfully run the command: `{command}`")

    @decorators.command(
        brief="Get the help docstring of a command.",
        aliases=["helpstr"],
        implemented="2021-05-03 02:26:36.434933",
        updated="2021-05-05 04:28:36.454933",
    )
    async def docstring(self, ctx, command: converters.DiscordCommand):
        """
        Usage: {0}docstring <command>
        Alias: {0}helpstr <command>
        Output:
            The long description of the passed command
        """
        await ctx.send_or_reply(
            content=f"{self.bot.emote_dict['announce']} Command docstring for **{command.name}**:```yaml\n{command.help}```",
        )

    @decorators.command(
        brief="Get a usage example for a command.",
        aliases=["signature"],
        implemented="2021-05-03 02:26:36.434933",
        updated="2021-05-05 04:28:36.454933",
    )
    async def usage(self, ctx, command: converters.DiscordCommand):
        """
        Usage: {0}usage <command>
        Aliases: {0}signature, {0}usage
        Output:
            The usage of a command
        """
        await ctx.usage(command.signature, command)

    @decorators.command(
        brief="Get specific examples for a command.",
        aliases=["ex", "example"],
        implemented="2021-05-06 16:54:55.398618",
        updated="2021-05-06 16:54:55.398618",
    )
    async def examples(self, ctx, command: converters.DiscordCommand):
        """
        Usage: {0}example <command>
        Alias: {0}ex
        Output:
            Shows all possible command usages
            with aliases and valid arguments.
        """
        if not command.examples:
            return await ctx.fail(f"No examples are currently available for the command `{command}`")
        examples = inspect.cleandoc(command.examples.format(ctx.prefix))
        p = pagination.MainMenu(pagination.TextPageSource(examples, prefix="```prolog"))
        try:
            await p.start(ctx)
        except menus.MenuError as e:
            await ctx.send_or_reply(e)


    @decorators.command(
        brief="Show when a command was last updated.",
        aliases=["changed"],
        implemented="2021-05-05 04:09:30.395495",
        updated="2021-05-05 04:09:30.395495",
    )
    async def updated(self, ctx, command: converters.DiscordCommand):
        """
        Usage: {0}updated <command>
        Alias: {0}changed
        Output:
            Show exactly when a command
            was last updated by the owner.
        """
        stopwatch = self.bot.emote_dict["stopwatch"]
        if command.updated:
            await ctx.send_or_reply(
                f"{stopwatch} The command `{command}` was last updated at `{command.updated} UTC`"
            )
        else:
            await ctx.fail(f"The last update on `{command}` was not documented.")

    @decorators.command(
        brief="Show when a command was first made.",
        aliases=["implemented"],
        implemented="2021-05-05 04:09:30.395495",
        updated="2021-05-05 04:09:30.395495",
    )
    async def made(self, ctx, command: converters.DiscordCommand):
        """
        Usage: {0}made <command>
        Alias: {0}implemented
        Output:
            Show exactly when a command
            was first added to the bot.
        """
        stopwatch = self.bot.emote_dict["stopwatch"]
        if command.updated:
            await ctx.send_or_reply(
                f"{stopwatch} The command `{command}` was implemented at `{command.updated} UTC`"
            )
        else:
            await ctx.fail(
                f"The implementation date for `{command}` was not documented."
            )

    @decorators.command(
        brief="Show who wrote a command.",
        aliases=["whowrote"],
        implemented="2021-05-05 04:09:30.395495",
        updated="2021-05-05 04:09:30.395495",
    )
    async def writer(self, ctx, command: converters.DiscordCommand):
        """
        Usage: {0}writer <command>
        Alias: {0}whowrote <command>
        Output:
            Show the developer who created
            a specific command.
        """
        heart = self.bot.emote_dict["heart"]
        writer = f"{self.bot.get_user(command.writer)} ({command.writer})"
        await ctx.send_or_reply(
            f"{heart} The command `{command}` was made by `{writer}`"
        )

    @decorators.command(
        brief="Get attribute info on a command.",
        aliases=['cmdinfo'],
        implemented="2021-05-05 18:41:26.960101",
        updated="2021-05-05 18:41:26.960101"
    )
    async def commandinfo(self, ctx, command: converters.DiscordCommand):
        """
        Usage: {0}commandinfo <command>
        Alias: {0}cmdinfo
        Output:
            Specific command information
        """
        writer = f"{self.bot.get_user(command.writer)} [{command.writer}]"
        uperms = await self.required_permissions(command, "")
        bperms = await self.required_permissions(command)
        query = """
                SELECT (COUNT(*), MAX(timestamp))
                FROM commands
                WHERE command = $1
                """
        stats = await self.bot.cxn.fetchval(query, command.qualified_name)
        last_run = utils.format_time(stats[1])
        total_runs = stats[0]
        title = f"{self.bot.emote_dict['commands']} **Information on `{command.qualified_name}`**"
        collection = []
        collection.append({"Name": command.qualified_name})
        collection.append({"Description": command.brief})
        if command.aliases:
            collection.append({f"Alias{'' if len(command.aliases) == 1 else 'es'}": "|".join(command.aliases)})
        collection.append({"Usage": f"{ctx.prefix}{command.qualified_name} {command.signature}"})
        collection.append({"Status": f"{'Enabled' if command.enabled else 'Disabled'}"})
        collection.append({"Hidden": command.hidden})
        if uperms:
            pretty_uperms = [x.title().replace("_", " ").replace("Tts", "TTS") for x in uperms]
            userperms = ', '.join(pretty_uperms)
        else:
            userperms = "No user permissions required."
        collection.append({"Permissions": userperms})
        if bperms:
            pretty_bperms = [x.title().replace("_", " ").replace("Tts", "TTS") for x in bperms]
            botperms = ', '.join(pretty_bperms)
        else:
            botperms = "No bot permissions required."
        collection.append({"Bot Permissions": botperms})
        if hasattr(command, "implemented"):
            implemented = utils.format_time(datetime.strptime(command.implemented, "%Y-%m-%d %H:%M:%S.%f")) if command.implemented else "Not documented"
            collection.append({"Implemented": implemented})
        if hasattr(command, "updated"):
            updated = utils.format_time(datetime.strptime(command.updated, "%Y-%m-%d %H:%M:%S.%f")) if command.updated else "Not documented"
            collection.append({"Last Updated": updated})
        collection.append({"Last Run": last_run})
        collection.append({"Total Runs": total_runs})
        if hasattr(command, "writer"):
            collection.append({"Writer": writer})

        width = max([len(x[0]) for x in [list(x) for x in [x.keys() for x in collection]]])
        msg = ""
        for item in collection:
            for key, value in item.items():
                msg += f"{str(key).ljust(width)} : {value}\n"
        p = pagination.MainMenu(pagination.TextPageSource(msg, prefix="```yaml"))
        await ctx.send_or_reply(title)
        try:
            await p.start(ctx)
        except menus.MenuError as e:
            await ctx.send_or_reply(e)


    @decorators.command(
        aliases=['dmonly', 'serveronly','guildonly'],
        brief="Show where a command can be run.",
        implemented="2021-05-06 03:00:02.824483",
        updated="2021-05-06 04:31:04.798398",
    )
    async def where(self, ctx, command: converters.DiscordCommand):
        """
        Usage: {0}where <command>
        Aliases:
            {0}dmonly
            {0}guildonly
            {0}serveronly
        Output:
            Show where a command can be run.
            Can either be exclusive to servers,
            restricted to bot-user DMs only, 
            or available in both.
        """
        checks = []
        for x in command.checks:
            checks.append(str(x.__qualname__).split('.')[0])
        if "dm_only" in checks:
            msg = f"The command `{command}` can only be run in direct messages."
        elif "guild_only" in checks:
            msg = f"The command `{command}` can only be run within servers."
        else:
            msg = f'The command `{command}` can be run in servers and in direct messages.'
        await ctx.success(msg)


    @decorators.command(
        aliases=['bothasperms', 'bothaspermissions','botpermissions'],
        brief="Check if the bot can run a command.",
        implemented="2021-05-06 03:08:59.775868",
        updated="2021-05-06 04:32:54.549795",
    )
    async def botperms(self, ctx, command: converters.DiscordCommand):
        """
        Usage: {0}botperms <command>
        Aliases:
            {0}bothasperms,
            {0}botpermissions,
            {0}bothaspermissions
        Output:
            Check which permissions the bot
            requires to run that command.
        Notes:
            The emote will signify whether or not the bot
            has the permissions needed to run that command.
        """
        perms = await self.required_permissions(command, "")
        if perms:
            if not ctx.guild:
                emote = self.bot.emote_dict['info']
            else:
                channel_perms = [x[0] for x in ctx.channel.permissions_for(ctx.author) if x[1] is True]
                guild_perms = [x[0] for x in ctx.author.guild_permissions if x[1] is True]
                userperms = guild_perms + channel_perms
                if all([x in userperms for x in perms]):
                    emote = self.bot.emote_dict['success']
                else:
                    emote = self.bot.emote_dict['failed']
            pretty_perms = [x.title().replace("_", " ").replace("Tts", "TTS") for x in perms]
            finalized = ', '.join(pretty_perms)
            return await ctx.send_or_reply(
                f"{emote} The command `{command}` requires me to have the permission{'' if len(pretty_perms) == 1 else 's'}: `{finalized}`"
            )
        else:
            return await ctx.success(f"I require no permissions to run the command `{command}`")

    @decorators.command(
        aliases=['userperms','userhasperms','authorhaspermissions','authorhasperms','userhaspermissions'],
        brief="Check if you can run a command.",
        implemented="2021-05-06 03:33:53.038375",
        updated="2021-05-06 04:38:47.396955",
    )
    async def reqperms(self, ctx, command: converters.DiscordCommand):
        """
        Usage: {0}authorperms <command>
        Aliases:
            {0}userperms,
            {0}userhasperms,
            {0}requiredperms,
            {0}userhaspermissions,
            {0}requiredpermissions
        Output:
            Check which permissions the command
            user requires to run that command.
        Notes:
            The emote will signify whether or not you
            have permission to run that command.
        """
        perms = await self.required_permissions(command, "")
        if perms:
            if not ctx.guild:
                emote = self.bot.emote_dict['info']
            else:
                channel_perms = [x[0] for x in ctx.channel.permissions_for(ctx.author) if x[1] is True]
                guild_perms = [x[0] for x in ctx.author.guild_permissions if x[1] is True]
                userperms = guild_perms + channel_perms
                if all([x in userperms for x in perms]):
                    emote = self.bot.emote_dict['success']
                else:
                    emote = self.bot.emote_dict['failed']
            pretty_perms = [x.title().replace("_", " ").replace("Tts", "TTS") for x in perms]
            finalized = ', '.join(pretty_perms)
            return await ctx.send_or_reply(
                f"{emote} The command `{command}` requires you to have the permission{'' if len(pretty_perms) == 1 else 's'}: `{finalized}`"
            )
        else:
            return await ctx.success(f"You require no permissions to run the command `{command}`")


    async def required_permissions(self, command, bot_or_author = "bot_"):
        checks = [x for x in command.checks]
        perms = []
        # Thanks Stella#2000
        for check in checks:
            if str(check.__qualname__).split('.')[0] == bot_or_author + "has_perms":
                try:
                    await check(0) # This would raise an error, because `0` is passed as ctx
                except Exception as e:
                    frames = [*traceback.walk_tb(e.__traceback__)] # Iterate through the generator
                    last_trace = frames[-1] # get the last trace
                    frame = last_trace[0] # get the first element to get the trace
                    for x in frame.f_locals['perms']:
                        perms.append(x)
        if perms:
            return perms
        return