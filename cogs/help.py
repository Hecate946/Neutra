import inspect
import discord
import traceback

from collections import Counter
from datetime import datetime
from discord.ext import commands, menus

from utilities import utils
from utilities import checks
from utilities import converters
from utilities import decorators
from utilities import formatting
from utilities import pagination


class HelpView(discord.ui.View):
    def __init__(self, ctx, embed):
        super().__init__(timeout=120)

        self.ctx = ctx
        self.bot = ctx.bot
        self.embed = embed

        invite_url = ctx.bot.oauth
        support_url = ctx.bot.constants.support
        github_url = (
            "https://github.com/Hecate946/Neutra/blob/main/README.md"  # "Docs link
        )

        self.invite = discord.ui.Button(label="Invite", url=invite_url)
        self.support = discord.ui.Button(label="Support", url=support_url)
        self.github = discord.ui.Button(label="Docs", url=github_url)

        self.clear_items()
        self.fill_items()

    def fill_items(self, *, _help=False, expired=False):
        if expired:
            self.add_item(self.github)
            self.add_item(self.invite)
            self.add_item(self.support)
            return
        if _help:
            self.add_item(self.delete)
            self.add_item(self._return)
            self.add_item(self.github)
            self.add_item(self.invite)
            self.add_item(self.support)
            return

        self.add_item(self.delete)
        self.add_item(self.helper)
        self.add_item(self.github)

    async def start(self):
        if not self.ctx.guild:  # In DMs, just send the embed
            self.message = await self.ctx.safe_send(embed=self.embed, view=self)
        else:  # In a server
            if not self.ctx.channel.permissions_for(
                self.ctx.me
            ).embed_links:  # Can't embed
                self.message = await self.attempt_dm(self.ctx, self.embed)  # DM them.
            else:
                self.message = await self.ctx.send_or_reply(embed=self.embed, view=self)

        return self.message

    async def attempt_dm(self, ctx, embed):
        try:
            msg = await ctx.author.send(embed=embed, view=self)
        except Exception:
            await ctx.fail(
                f"I was unable to send you help. Please ensure I have the `Embed Links` permission in this channel or enable your DMs for this server."
            )
        else:
            await ctx.react(self.bot.emote_dict["letter"])
            return msg

    @property
    def help_embed(self):
        help_embed = discord.Embed(
            description="I'm a multipurpose discord bot that specializes in stat tracking and moderation.",
            color=self.bot.constants.embed,
        )
        help_embed.set_author(
            name="Welcome to my help page.", icon_url=self.bot.user.display_avatar.url
        )
        help_embed.add_field(
            name="Here's how to understand my help command.",
            value="Please note that __**you should not type in the brackets when running the commands**__.",
            inline=False,
        )
        help_embed.add_field(
            name="**<argument>**",
            value="This means that the argument is __**required**__.",
            inline=False,
        )
        help_embed.add_field(
            name="**[argument]**",
            value="This means that the argument is __**optional**__.",
            inline=False,
        )
        help_embed.add_field(
            name="**[X|Y]**",
            value="This means that the argument can be __**either X or Y**__.",
            inline=False,
        )
        help_embed.add_field(
            name="**[argument...]**",
            value="This means that you can pass __**multiple arguments**__ into the command.",
            inline=False,
        )
        return help_embed

    async def interaction_check(self, interaction):
        if self.ctx.author.id == interaction.user.id:
            return True
        else:
            await interaction.response.send_message(
                "Only the command invoker can use this button.", ephemeral=True
            )

    async def on_error(
        self,
        error: Exception,
        item: discord.ui.Item,
        interaction: discord.Interaction,
    ):
        if interaction.response.is_done():
            await interaction.followup.send(str(error), ephemeral=True)
        else:
            await interaction.response.send_message(str(error), ephemeral=True)

    async def on_timeout(self):
        self.clear_items()
        self.fill_items(expired=True)
        await self.message.edit(embed=self.embed, view=self)

    @discord.ui.button(label="Delete", style=discord.ButtonStyle.red)
    async def delete(self, button: discord.ui.Button, interaction: discord.Interaction):
        await interaction.message.delete()
        self.stop()

    @discord.ui.button(label="Need help?", style=discord.ButtonStyle.green)
    async def helper(self, button: discord.ui.Button, interaction: discord.Interaction):
        self.clear_items()
        self.fill_items(_help=True)
        await interaction.message.edit(embed=self.help_embed, view=self)

    @discord.ui.button(label="Go back", style=discord.ButtonStyle.blurple)
    async def _return(
        self, button: discord.ui.Button, interaction: discord.Interaction
    ):
        self.clear_items()
        self.fill_items()
        await interaction.message.edit(embed=self.embed, view=self)


def setup(bot):
    bot.remove_command("help")
    bot.add_cog(Help(bot))


class Help(commands.Cog):
    """
    My extensive help category.
    """

    def __init__(self, bot):
        self.bot = bot

        self.desc = (
            f"**Bot Invite Link:** [https://neutra.discord.bot]({self.bot.oauth})\n"
        )
        self.desc += f"**Support Server:**  [https://discord.gg/neutra]({self.bot.constants.support})\n"
        self.desc += f"**Voting Link:**  [https://top.gg/bot/neutra/vote](https://top.gg/bot/806953546372087818/vote)"

    ############################
    ## Get Commands From Cogs ##
    ############################

    async def send_help(self, ctx, embed):
        await HelpView(ctx, embed).start()

    async def send_category_help(self, ctx):

        embed = discord.Embed(
            title=f"{self.bot.user.name}'s Help Command",
            url="https://discord.gg/947ramn",
            description=self.desc,
            color=self.bot.constants.embed,
        )

        embed.set_footer(
            text=f'Use "{ctx.clean_prefix}help category" for information on a category.'
        )

        def pred(cog):
            if len([c for c in cog.get_commands() if not c.hidden]) == 0:
                return False
            return True

        cogs = [cog for cog in self.bot.get_cogs() if pred(cog)]
        public = ""
        beta = ""
        admin = ""
        for cog in sorted(cogs, key=lambda cog: cog.qualified_name):
            if cog.qualified_name.upper() in self.bot.admin_cogs:
                admin += f"\n`{cog.qualified_name}` {cog.description}\n"
            elif cog.qualified_name.upper() in self.bot.music_cogs:
                beta += f"\n`{cog.qualified_name}` {cog.description}\n"
            else:
                public += f"\n`{cog.qualified_name}` {cog.description}\n"

        embed.add_field(
            name="**General Categories**", value=f"** **{public}**\n**", inline=False
        )
        if beta != "":
            embed.add_field(
                name="**Music Categories**",
                value=f"** **{beta}**\n**",
                inline=False,
            )
        if checks.is_admin(ctx):
            embed.add_field(
                name="**Admin Categories**", value=f"** **{admin}**\n**", inline=False
            )

        await self.send_help(ctx, embed)

    async def send_cog_help(self, ctx, cog):
        commands = [c for c in cog.walk_commands() if not c.hidden]
        commands = sorted(commands, key=lambda x: x.qualified_name)

        embed = discord.Embed(
            title=f"Category: `{cog.qualified_name}`",
            description=self.desc,
            color=self.bot.constants.embed,
        )
        embed.set_footer(
            text=f'Use "{ctx.clean_prefix}help command" for information on a command.\n'
        )

        value = ""
        for cmd in commands:
            cmd.brief = cmd.brief or "No description"
            if checks.is_disabled(ctx, cmd):
                value += f"\n[!] ~~`{cmd.qualified_name}` {cmd.brief}~~\n"
            else:
                value += f"\n`{cmd.qualified_name}` {cmd.brief}\n"

        embed.add_field(
            name=f"**{cog.qualified_name} Commands**", value=f"** **{value}"
        )
        await self.send_help(ctx, embed)

    async def send_command_help(self, ctx, command, search):
        _footer = "subcommand" if isinstance(command, commands.Group) else "category"
        command.help = command.help or "No help available."
        command.brief = command.brief or "No description available."

        if command.hidden:
            return await ctx.fail(f"No command named `{search}` found.")

        if command.cog_name in self.bot.admin_cogs and not checks.is_admin(ctx):
            return await ctx.fail(f"No command named `{search}` found.")

        embed = discord.Embed(
            title=f"Category: `{command.cog_name}`",
            description=self.desc,
            color=self.bot.constants.embed,
        )
        embed.set_footer(
            text=f'Use "{ctx.clean_prefix}help {_footer}" for information on a {_footer}.'
        )
        embed.add_field(
            name=f"**Command Name:** `{command.qualified_name.capitalize()}`\n**Description:** `{command.brief}`\n",
            value=f"** **" f"```yaml\n{command.help.format(ctx.clean_prefix)}```",
        )
        return await self.send_help(ctx, embed)

    @decorators.command(
        name="help",
        aliases=["commands", "documentation", "docs", "helpme"],
        brief="My documentation for all commands.",
        implemented="2021-02-22 05:04:47.433000",
        updated="2021-05-05 05:08:05.642637",
    )
    async def _help(self, ctx, *, category_or_command: str = None):
        """
        Usage:  {0}help [command/category] [pm = true]
        Output: Show documentation for all my commands.
        """

        if category_or_command is None:
            return await self.send_category_help(
                ctx,
            )
        else:

            ##########################
            ## Manages General Help ##
            ##########################

            if category_or_command.lower() in [
                "category",
                "command",
                "group",
                "subcommand",
            ]:  # Someone took the embed footer too literally.
                if category_or_command.lower() == "subcommand":
                    example = f"{ctx.clean_prefix}help purge until"
                elif category_or_command.lower() == "group":
                    example = f"{ctx.clean_prefix}help purge"
                elif category_or_command.lower() == "command":
                    example = f"{ctx.clean_prefix}help userinfo"
                else:
                    example = f"{ctx.clean_prefix}help info"
                await ctx.fail(
                    f"Please specify a valid {category_or_command.lower()} name. Example: `{example}`"
                )
                return

            ######################
            ## Manages Cog Help ##
            ######################

            if category_or_command.lower() in [
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
                return await self.send_cog_help(ctx, cog)

            if category_or_command.lower() in [
                "bot",
                "bots",
                "info",
                "about",
                "robot",
                "information",
            ]:
                cog = self.bot.get_cog("Info")
                return await self.send_cog_help(ctx, cog)

            if category_or_command.lower() in [
                "help",
                "helpme",
                "assist",
                "assistance",
                "commands",
                "cmds",
            ]:
                cog = self.bot.get_cog("Help")
                return await self.send_cog_help(ctx, cog)

            if category_or_command.lower() in [
                "dump",
                "files",
                "file",
                "txt",
                "txts",
                "dumps",
            ]:
                cog = self.bot.get_cog("Files")
                return await self.send_cog_help(ctx, cog)

            if category_or_command.lower() in ["logging", "logs"]:
                cog = self.bot.get_cog("Logging")
                return await self.send_cog_help(ctx, cog)

            if category_or_command.lower() in [
                "mod",
                "moderator",
                "punishment",
                "moderation",
                "punish",
            ]:
                cog = self.bot.get_cog("Mod")
                return await self.send_cog_help(ctx, cog)

            if category_or_command.lower() in [
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
                return await self.send_cog_help(ctx, cog)

            if category_or_command.lower() in ["roles", "serverroles"]:
                cog = self.bot.get_cog("Roles")
                return await self.send_cog_help(ctx, cog)

            if category_or_command.lower() in [
                "serverstats",
                "stats",
                "statistics",
            ]:
                cog = self.bot.get_cog("Stats")
                return await self.send_cog_help(ctx, cog)

            if category_or_command.lower() in [
                "server",
                "servers",
            ]:
                cog = self.bot.get_cog("Server")
                return await self.send_cog_help(ctx, cog)

            if category_or_command.lower() in [
                "track",
                "users",
                "tracking",
                "userstats",
                "user",
            ]:
                cog = self.bot.get_cog("Tracking")
                return await self.send_cog_help(ctx, cog)

            if category_or_command.lower() in [
                "conversions",
                "conversion",
                "encoding",
                "encryption",
                "decryption",
                "decrypt",
            ]:
                cog = self.bot.get_cog("Conversion")
                if not cog:
                    return await ctx.fail(
                        f"The conversion category is currently unavailable. Please try again later."
                    )
                return await self.send_cog_help(ctx, cog)

            if category_or_command.lower() in [
                "automod",
                "warning",
                "auto",
                "automoderation",
                "system",
            ]:
                cog = self.bot.get_cog("Automod")
                return await self.send_cog_help(ctx, cog)

            if category_or_command.lower() in [
                "conf",
                "configuration",
                "config",
            ]:
                cog = self.bot.get_cog("Config")
                return await self.send_cog_help(ctx, cog)

            if category_or_command.lower() in [
                "tasks",
                "reminders",
                "timers",
            ]:
                cog = self.bot.get_cog("Tasks")
                return await self.send_cog_help(ctx, cog)

            #####################
            ## Admin Only Help ##
            #####################

            if category_or_command.lower() in ["jsk", "jish", "jishaku"]:
                if not checks.is_admin(ctx):  # Jishaku is owner-only
                    return await ctx.fail(
                        f"No command named `{category_or_command}` found."
                    )
                return await ctx.send_help("jishaku")

            if category_or_command.lower() in ["botconfig", "owner"]:
                if not checks.is_admin(ctx):
                    return await ctx.fail(
                        f"No command named `{category_or_command}` found."
                    )
                cog = self.bot.get_cog("Botconfig")
                return await self.send_cog_help(ctx, cog)

            if category_or_command.lower() in ["botadmin", "badmin"]:
                if not checks.is_admin(ctx):
                    return await ctx.fail(
                        f"No command named `{category_or_command}` found."
                    )
                cog = self.bot.get_cog("Botadmin")
                return await self.send_cog_help(ctx, cog)

            if category_or_command.lower() in ["manage", "manager", "master"]:
                if not checks.is_admin(ctx):
                    return await ctx.fail(
                        f"No command named `{category_or_command}` found."
                    )
                cog = self.bot.get_cog("Manager")
                return await self.send_cog_help(ctx, cog)

            if category_or_command.lower() in ["monitor", "heart"]:
                if not checks.is_admin(ctx):
                    return await ctx.fail(
                        f"No command named `{category_or_command}` found."
                    )
                cog = self.bot.get_cog("Monitor")
                return await self.send_cog_help(ctx, cog)

            if category_or_command.lower() in ["database", "db"]:
                if not checks.is_admin(ctx):
                    return await ctx.fail(
                        f"No command named `{category_or_command}` found."
                    )
                cog = self.bot.get_cog("Database")
                return await self.send_cog_help(ctx, cog)

            ###############
            ## Beta help ##
            ###############
            if category_or_command.lower() in ["music", "player"] and self.bot.get_cog("Player"):
                cog = self.bot.get_cog("Player")
                return await self.send_cog_help(ctx, cog)

            if category_or_command.lower() in ["queue"] and self.bot.get_cog("Player"):
                cog = self.bot.get_cog("Queue")
                return await self.send_cog_help(ctx, cog)

            if category_or_command.lower() in ["voice"] and self.bot.get_cog("Player"):
                cog = self.bot.get_cog("Voice")
                return await self.send_cog_help(ctx, cog)

            if category_or_command.lower() in ["audio"] and self.bot.get_cog("Player"):
                cog = self.bot.get_cog("Audio")
                return await self.send_cog_help(ctx, cog)

            if category_or_command.lower() in ["playlists"] and self.bot.get_cog("Player"):
                cog = self.bot.get_cog("Playlists")
                return await self.send_cog_help(ctx, cog)

            ##########################
            ## Manages Command Help ##
            ##########################

            else:
                command = self.bot.get_command(category_or_command.lower())
                if not command:
                    return await ctx.fail(
                        f"No command named `{category_or_command}` found."
                    )
                else:
                    return await self.send_command_help(
                        ctx, command, category_or_command
                    )

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
            f"Command docstring for **{command.name}**:```yaml\n{command.help.format(ctx.clean_prefix)}```",
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
            return await ctx.fail(
                f"No examples are currently available for the command `{command}`"
            )
        examples = inspect.cleandoc(command.examples.format(ctx.clean_prefix))
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
        brief="Show all people who wrote for me.",
        implemented="2021-05-10 01:05:40.207559",
        updated="2021-05-10 01:05:40.207559",
    )
    async def writers(self, ctx):
        """
        Usage: {0}writers
        Output:
            Show all the developers
            who created commands for me.
        """
        heart = self.bot.emote_dict["heart"]
        writers = []
        for cmd in self.bot.commands:
            try:
                writers.append(cmd.writer)
            except AttributeError:
                continue
        writers = Counter(writers)
        writers = sorted(
            [
                (str(await self.bot.fetch_user(x)), x, count)
                for x, count in writers.items()
            ]
        )
        msg = ""
        width = max([len(name) for name, user_id, count in writers])
        id_width = max([len(str(user_id)) for name, user_id, count in writers])
        for name, user_id, count in writers:
            msg += f"{name.ljust(width)} ({str(user_id).ljust(id_width)}): {count}\n"

        await ctx.send_or_reply(f"**{heart} My writers**```prolog\n{msg}```")

    @decorators.command(
        brief="Show the parent category of a command.",
        aliases=["cog"],
        implemented="2021-05-07 18:12:17.837263",
        updated="2021-05-07 18:12:17.837263",
        examples="""
                {0}cog help
                {0}category prune
                """,
    )
    async def category(self, ctx, command: converters.DiscordCommand):
        """
        Usage: {0}category <command>
        Alias: {0}cog <command>
        Output:
            Show the parent category (cog)
            of a passed command.
        """
        right = self.bot.emote_dict["right"]
        await ctx.send_or_reply(
            f"{right} The command `{command}` resides in the `{command.cog_name}` {ctx.invoked_with.lower()}."
        )

    @decorators.command(
        brief="Get attribute info on a command.",
        aliases=["cmdinfo"],
        implemented="2021-05-05 18:41:26.960101",
        updated="2021-05-05 18:41:26.960101",
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
            collection.append(
                {
                    f"Alias{'' if len(command.aliases) == 1 else 'es'}": "|".join(
                        command.aliases
                    )
                }
            )
        collection.append(
            {"Usage": f"{ctx.clean_prefix}{command.qualified_name} {command.signature}"}
        )
        collection.append({"Status": f"{'Enabled' if command.enabled else 'Disabled'}"})
        collection.append({"Hidden": command.hidden})
        if uperms:
            pretty_uperms = [
                x.title().replace("_", " ").replace("Tts", "TTS") for x in uperms
            ]
            userperms = ", ".join(pretty_uperms)
        else:
            userperms = "No user permissions required."
        collection.append({"Permissions": userperms})
        if bperms:
            pretty_bperms = [
                x.title().replace("_", " ").replace("Tts", "TTS") for x in bperms
            ]
            botperms = ", ".join(pretty_bperms)
        else:
            botperms = "No bot permissions required."
        collection.append({"Bot Permissions": botperms})
        if hasattr(command, "implemented"):
            implemented = (
                utils.format_time(
                    datetime.strptime(command.implemented, "%Y-%m-%d %H:%M:%S.%f")
                )
                if command.implemented
                else "Not documented"
            )
            collection.append({"Implemented": implemented})
        if hasattr(command, "updated"):
            updated = (
                utils.format_time(
                    datetime.strptime(command.updated, "%Y-%m-%d %H:%M:%S.%f")
                )
                if command.updated
                else "Not documented"
            )
            collection.append({"Last Updated": updated})
        collection.append({"Last Run": last_run})
        collection.append({"Total Runs": total_runs})
        if hasattr(command, "writer"):
            collection.append({"Writer": writer})

        width = max(
            [len(x[0]) for x in [list(x) for x in [x.keys() for x in collection]]]
        )
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
        aliases=["dmonly", "serveronly", "guildonly"],
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
            if hasattr(x, "__qualname__"):
                checks.append(str(x.__qualname__).split(".")[0])
        if "dm_only" in checks:
            msg = f"The command `{command}` can only be run in direct messages."
        elif "guild_only" in checks:
            msg = f"The command `{command}` can only be run within servers."
        else:
            msg = (
                f"The command `{command}` can be run in servers and in direct messages."
            )
        await ctx.success(msg)

    @decorators.command(brief="Show the cooldown for a command.")
    async def cooldown(self, ctx, command: converters.DiscordCommand):
        """
        Usage: {0}cooldown <command>
        Output:
            Show the cooldown for a command.
        """
        cooldown = None
        for x in command.checks:
            if hasattr(x, "cooldown"):
                rate, per = x.cooldown
                cooldown = f"{rate} command{'' if rate == 1 else 's'} every {per} second{'' if rate == 1 else 's'}."
        msg = cooldown or f"The command `{command}` has no cooldown."
        await ctx.success(msg)

    @decorators.command(
        aliases=["cmdsearch"],
        brief="Search for a command by name.",
        implemented="2021-06-02 07:01:30.704411",
        updated="2021-06-02 07:01:30.704411",
        examples="""
                commandsearch cmd
                cmdsearch emoj
                """,
    )
    async def commandsearch(self, ctx, search: str):
        """
        Usage: {0}commandsearch <search>
        Alias: {0}cmdsearch
        Output:
            Searches for the most similar
            commands based off a search query.
            Outputs the results in tabular format.
        """
        option_list = utils.disambiguate(
            search, [c for x in self.bot.commands for c in x.aliases], None, 10
        )
        title_str = f"{self.bot.emote_dict['search']} **Similar command search results from `{search}`**"
        rows = [
            (idx, search["result"], f"{search['ratio']:.2%}")
            for idx, search in enumerate(option_list, start=1)
        ]
        table = formatting.TabularData()
        table.set_columns(["INDEX", "COMMAND", "SIMILARITY"])
        table.add_rows(rows)
        render = table.render()
        to_send = f"{title_str}\n```sml\n{render}```"
        await ctx.send_or_reply(to_send)

    @decorators.command(
        aliases=["alias"],
        brief="Show the aliases for a command",
        implemented="2021-06-02 07:01:30.704411",
        updated="2021-06-02 07:01:30.704411",
        examples="""
                {0}aliases help
                {0}alias emojistats
                """,
    )
    async def aliases(self, ctx, command: converters.DiscordCommand):
        """
        Usage: {0}aliases <command>
        Alias: {0}alias
        Output:
            Shows all the aliases
            for a given command
        """
        title_str = f"{self.bot.emote_dict['success']} **Aliases for `{command.name}`**"
        table = formatting.TabularData()
        table.set_columns(["ALIASES"])
        table.add_rows([[x] for x in sorted(command.aliases, key=len)])
        render = table.render()
        to_send = f"{title_str}\n```sml\n{render}```"
        await ctx.send_or_reply(to_send)

    @decorators.command(
        aliases=["bothasperms", "bothaspermissions", "botpermissions"],
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
                emote = self.bot.emote_dict["info"]
            else:
                channel_perms = [
                    x[0]
                    for x in ctx.channel.permissions_for(ctx.author)
                    if x[1] is True
                ]
                guild_perms = [
                    x[0] for x in ctx.author.guild_permissions if x[1] is True
                ]
                userperms = guild_perms + channel_perms
                if all([x in userperms for x in perms]):
                    emote = self.bot.emote_dict["success"]
                else:
                    emote = self.bot.emote_dict["failed"]
            pretty_perms = [
                x.title().replace("_", " ").replace("Tts", "TTS") for x in perms
            ]
            finalized = ", ".join(pretty_perms)
            return await ctx.send_or_reply(
                f"{emote} The command `{command}` requires me to have the permission{'' if len(pretty_perms) == 1 else 's'}: `{finalized}`"
            )
        else:
            return await ctx.success(
                f"I require no permissions to run the command `{command}`"
            )

    @decorators.command(
        aliases=[
            "userperms",
            "userhasperms",
            "authorhaspermissions",
            "authorhasperms",
            "userhaspermissions",
        ],
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
                emote = self.bot.emote_dict["info"]
            else:
                channel_perms = [
                    x[0]
                    for x in ctx.channel.permissions_for(ctx.author)
                    if x[1] is True
                ]
                guild_perms = [
                    x[0] for x in ctx.author.guild_permissions if x[1] is True
                ]
                userperms = guild_perms + channel_perms
                if all([x in userperms for x in perms]):
                    emote = self.bot.emote_dict["success"]
                else:
                    emote = self.bot.emote_dict["failed"]
            pretty_perms = [
                x.title()
                .replace("_", " ")
                .replace("Tts", "TTS")
                .replace("Guild", "Server")
                for x in perms
            ]
            finalized = ", ".join(pretty_perms)
            return await ctx.send_or_reply(
                f"{emote} The command `{command}` requires you to have the permission{'' if len(pretty_perms) == 1 else 's'}: `{finalized}`"
            )
        else:
            return await ctx.success(
                f"You require no permissions to run the command `{command}`"
            )

    async def required_permissions(self, command, bot_or_author="bot_"):
        checks = [x for x in command.checks]
        perms = []
        # Thanks Stella#2000
        for check in checks:
            if hasattr(check, "__qualname__"):
                if str(check.__qualname__).split(".")[0] == bot_or_author + "has_perms":
                    try:
                        await check(
                            0
                        )  # This would raise an error, because `0` is passed as ctx
                    except Exception as e:
                        frames = [
                            *traceback.walk_tb(e.__traceback__)
                        ]  # Iterate through the generator
                        last_trace = frames[-1]  # get the last trace
                        frame = last_trace[0]  # get the first element to get the trace
                        for x in frame.f_locals["perms"]:
                            perms.append(x)
        if perms:
            return perms
        return
