import os
import asyncio
import discord

from datetime import datetime
from discord.ext import commands

from utilities import permissions

USELESS_COGS = ["HELP", "TESTING", "TRACKER", "UPDATER", "SLASH"]
COG_EXCEPTIONS = ["CONFIG", "BOTADMIN", "MANAGER", "JISHAKU"]
COMMAND_EXCEPTIONS = ["EYECOUNT"]


def setup(bot):
    bot.remove_command("help")
    bot.add_cog(Help(bot))


class Help(commands.Cog):
    """
    My help category.
    """

    def __init__(self, bot):
        self.bot = bot

        self.emote_dict = bot.emote_dict

    ############################
    ## Get Commands From Cogs ##
    ############################

    async def send_help(self, ctx, embed, pm, delete_after):
        if pm is True:
            if not ctx.guild:
                msg = await ctx.send(reference=self.bot.rep_ref(ctx), embed=embed)
                return
            try:
                msg = await ctx.author.send(embed=embed)
                try:
                    await ctx.message.add_reaction(self.emote_dict["letter"])
                except Exception:
                    return
            except Exception:
                msg = await ctx.send(reference=self.bot.rep_ref(ctx), embed=embed, delete_after=delete_after)
        else:
            msg = await ctx.send(reference=self.bot.rep_ref(ctx), embed=embed, delete_after=delete_after)

        def reaction_check(m):
            if (
                m.message_id == msg.id
                and m.user_id == ctx.author.id
                and str(m.emoji) == self.emote_dict["trash"]
            ):
                return True
            return False

        try:
            await msg.add_reaction(self.emote_dict["trash"])
        except discord.Forbidden:
            return

        try:
            await self.bot.wait_for(
                "raw_reaction_add", timeout=60.0, check=reaction_check
            )
            await msg.delete()
        except asyncio.TimeoutError:
            try:
                await msg.clear_reactions()
            except Exception:
                await msg.remove_reaction(self.bot.emote_dict["trash"], self.bot.user)

    async def helper_func(self, ctx, cog, name, pm, delete_after):
        the_cog = sorted(cog.get_commands(), key=lambda x: x.name)
        cog_commands = []
        for c in the_cog:
            if c.hidden and not permissions.is_admin(ctx):
                continue
            if str(c.name).upper() in COMMAND_EXCEPTIONS and not permissions.is_admin(
                ctx
            ):
                await ctx.send(
                    f"{self.emote_dict['error']} No command named `{name}` found."
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
            return await ctx.send(
                f"{self.emote_dict['error']} No command named `{name}` found."
            )

    ##########################
    ## Build Category Embed ##
    ##########################

    async def category_embed(self, ctx, cog, list, pm, delete_after):
        embed = discord.Embed(
            title=f"Category: `{cog}`",
            description=f"**Bot Invite Link:** [https://ngc.discord.bot]({self.bot.constants.oauth})\n"
            f"**Support Server:**  [https://discord.gg/ngc]({self.bot.constants.support})\n",
            color=self.bot.constants.embed,
        )
        embed.set_footer(
            text=f'Use "{ctx.prefix}help command" for information on a command.\n'
        )

        msg = ""
        for i in list:
            if i.brief is None or i.brief == "":
                i.brief = "No description"
            line = f"\n`{i.name}` {i.brief}\n"
            if ctx.guild:
                if (
                    i.name
                    not in self.bot.server_settings[ctx.guild.id]["disabled_commands"]
                ):
                    msg += line
                else:
                    msg += f"\n:no_entry: `{i.name}` ~~{i.brief}~~\n"
            else:
                msg += line

        embed.add_field(name=f"**{cog} Commands**", value=f"** **{msg}")
        try:
            await self.send_help(ctx, embed, pm, delete_after)
        except discord.Forbidden:
            pass

    @commands.command(name="help", brief="NGC0000's Help Command")
    async def _help(self, ctx, invokercommand: str = None, pm=False, delete_after=None):
        """
        Usage:  -help [command/category] [pm = true]
        Output: HELP!
        """
        if str(invokercommand).upper() in ["YES", "TRUE"]:
            trigger = None
            pm = True

        elif invokercommand and str(pm).upper() in ["YES", "TRUE"]:
            trigger = True
            pm = True

        else:
            if invokercommand:
                trigger = True
                pm = False
            else:
                trigger = None
                pm = False

        if trigger is None:

            ##########################
            ## Manages General Help ##
            ##########################

            embed = discord.Embed(
                title=f"{self.bot.user.name}'s Help Command",
                url="https://discord.gg/947ramn",
                description=f"**Bot Invite Link:** [https://ngc.discord.bot]({self.bot.constants.oauth})\n"
                f"**Support Server:**  [https://discord.gg/ngc]({self.bot.constants.support})",
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
                if c.qualified_name.upper() in COG_EXCEPTIONS:
                    continue
                if c.qualified_name.upper() in USELESS_COGS or len(command_list) == 0:
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
                        msg += (
                            f"\n:no_entry: `{c.qualified_name}` ~~{c.description}~~\n"
                        )
                    else:
                        msg += line
                else:
                    msg += line

            embed.add_field(name=f"**Current Categories**", value=f"** **{msg}**\n**")
            if not permissions.is_admin(ctx):
                await self.send_help(ctx, embed, pm, delete_after)
            else:
                hidden_cogs = []
                msg = ""
                for cog in sorted(self.bot.cogs):
                    c = self.bot.get_cog(cog)
                    command_list = c.get_commands()
                    if c.qualified_name.upper() in COG_EXCEPTIONS:
                        hidden_cogs.append(c)
                for c in hidden_cogs:
                    if c.qualified_name.upper() == "JISHAKU":
                        continue  # Honestly we don't need jishaku showing up in help
                    line = f"\n`{c.qualified_name}` {c.description}\n"
                    msg += line
                embed.add_field(
                    name=f"**Hidden Categories**", value=f"** **{msg}", inline=False
                )

                await self.send_help(ctx, embed, pm, delete_after)

        elif trigger is True:

            ######################
            ## Manages Cog Help ##
            ######################

            # cog = self.bot.get_cog(invokercommand.capitalize())
            # if cog is not None:
            #     return await self.helper_func(ctx, cog=cog, name=invokercommand, pm = pm, delete_after=delete_after)

            if invokercommand.lower() in [
                "admin",
                "administration",
                "administrator",
                "settings",
                "setup",
                "configuration",
                "auto",
                "automod",
                "automoderation",
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
                cog = self.bot.get_cog("Bot")
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
                cog = self.bot.get_cog("Moderation")
                return await self.helper_func(
                    ctx, cog=cog, name=invokercommand, pm=pm, delete_after=delete_after
                )

            if invokercommand.lower() in [
                "general",
                "misc",
                "utility",
                "utils",
                "util",
                "utilities",
                "timezones",
            ]:
                cog = self.bot.get_cog("Utility")
                return await self.helper_func(
                    ctx, cog=cog, name=invokercommand, pm=pm, delete_after=delete_after
                )

            if invokercommand.lower() in ["restrict", "restriction", "disabling"]:
                cog = self.bot.get_cog("Restrict")
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
                cog = self.bot.get_cog("Server")
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
                cog = self.bot.get_cog("Users")
                return await self.helper_func(
                    ctx, cog=cog, name=invokercommand, pm=pm, delete_after=delete_after
                )

            if invokercommand.lower() in ["jsk", "jish", "jishaku"]:
                if not permissions.is_owner(ctx):
                    return await ctx.send(
                        f"{self.emote_dict['error']} No command named `{invokercommand}` found."
                    )
                return await ctx.send_help("jishaku")

            if invokercommand.lower() in ["conf", "config", "owner", "owners"]:
                if not permissions.is_owner(ctx):
                    return await ctx.send(
                        f"{self.emote_dict['error']} No command named `{invokercommand}` found."
                    )
                cog = self.bot.get_cog("Config")
                return await self.helper_func(
                    ctx, cog=cog, name=invokercommand, pm=pm, delete_after=delete_after
                )

            if invokercommand.lower() in ["hidden", "botadmin", "admins", "botadmins"]:
                if not permissions.is_admin(ctx):
                    return await ctx.send(
                        f"{self.emote_dict['error']} No command named `{invokercommand}` found."
                    )
                cog = self.bot.get_cog("Botadmin")
                return await self.helper_func(
                    ctx, cog=cog, name=invokercommand, pm=pm, delete_after=delete_after
                )

            if invokercommand.lower() in ["manage", "manager", "master", "heart"]:
                if not permissions.is_owner(ctx):
                    return await ctx.send(
                        f"{self.emote_dict['error']} No command named `{invokercommand}` found."
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
                            valid_commands += command.name
                            valid_help += command.help
                            if not command.brief:
                                command.brief = "None"
                            valid_brief += command.brief
                            valid_cog += str(command.cog.qualified_name)

                if valid_commands != "":
                    help_embed = discord.Embed(
                        title=f"Category: `{valid_cog.title()}`",
                        description=f"**Bot Invite Link:** [https://ngc.discord.bot]({self.bot.constants.oauth})\n"
                        f"**Support Server:**  [https://discord.gg/ngc]({self.bot.constants.support})",
                        color=self.bot.constants.embed,
                    )
                    help_embed.set_footer(
                        text=f'Use "{ctx.prefix}help command" for information on a command.'
                    )
                    help_embed.add_field(
                        name=f"**Command Name:** `{valid_commands.title()}`",
                        value=f"\n**Description:** `{valid_brief}`\n"
                        f"```yaml\n{valid_help}```",
                    )
                    await self.send_help(ctx, help_embed, pm, delete_after)
                    return
                else:
                    await ctx.send(
                        f"{self.emote_dict['error']} No command named `{invokercommand}` found."
                    )
