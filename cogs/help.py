import os
import asyncio
import discord

from datetime import datetime
from discord.ext import commands

from core import OWNERS
from utilities import default


COG_EXCEPTIONS = ['CONFIG','HELP']
COMMAND_EXCEPTIONS = ['EYECOUNT']


def setup(bot):
    bot.remove_command("help")
    bot.add_cog(Help(bot))


class Help(commands.Cog):
    """
    My help category.
    """
    def __init__(self, bot):
        self.bot = bot
        self.cxn = bot.connection


      ############################
     ## Get Commands From Cogs ##
    ############################


    async def send_help(self, ctx, embed, pm, delete_after):
        if pm is True:
            if not ctx.guild: 
                msg = await ctx.send(embed=embed)
                return
            try:
                msg = await ctx.author.send(embed=embed)
                try:
                    await ctx.message.add_reaction("<:letter:816520981396193280>")
                except: return
            except:
                msg = await ctx.send(embed=embed, delete_after=delete_after)
        else:
            msg = await ctx.send(embed=embed, delete_after=delete_after)

        def reaction_check(m):
            if m.message_id == msg.id and m.user_id == ctx.author.id and str(m.emoji) == "<:trash:816463111958560819>":
                return True
            return False

        try:
            await msg.add_reaction("<:trash:816463111958560819>")
            await self.bot.wait_for('raw_reaction_add', timeout=120.0, check=reaction_check)
            await msg.delete()
        except asyncio.TimeoutError:
            try:
                await msg.delete()
            except discord.NotFound:
                return
        except discord.Forbidden:
            return


    async def helper_func(self, ctx, cog, name, pm, delete_after):
        the_cog = sorted(cog.get_commands(), key=lambda x:x.name)
        cog_commands = []
        for c in the_cog:
            if c.hidden and ctx.author.id not in OWNERS: continue
            if str(c.name).upper() in COMMAND_EXCEPTIONS and ctx.author.id not in OWNERS: continue
            cog_commands.append(c)
        if cog_commands:
            await self.category_embed(ctx, cog=cog.qualified_name, list=cog_commands, pm=pm, delete_after=delete_after)
        else:
            return await ctx.send(f"<:error:816456396735905844> No command named `{name}` found.")

      ##########################
     ## Build Category Embed ##
    ##########################
    
    async def category_embed(self, ctx, cog, list, pm, delete_after):
        embed = discord.Embed(title=f"Category: `{cog}`",
        description=f"**Bot Invite Link:** [https://ngc.discord.bot](https://discord.com/oauth2/authorize?client_id=810377376269205546&scope=bot&permissions=8)\n"
                    f"**Support Server:**  [https://discord.gg/ngc](https://discord.gg/947ramn)\n", color=default.config()["embed_color"])
        embed.set_footer(text=f"Use \"{ctx.prefix}help command\" for information and usage examples on a command.\n")

        msg = ""
        for i in list:
            if i.brief is None:
                i.brief = "No description"
            line = f"\n`{i.name}` {i.brief}\n"
            msg += line
        embed.add_field(name=f"**{cog} Commands**", value=f"** **{msg}")
        
        await self.send_help(ctx, embed, pm, delete_after)


    @commands.command(name="help", brief="NGC0000's Help Command")
    async def _help(self, ctx, invokercommand:str = None, pm = False, delete_after=None):
        """
        Usage:  -help [command/category] [pm = true]
        Output: HELP!
        """
        if str(invokercommand).upper() in ["YES","TRUE"]:
            trigger = None
            pm = True

        elif invokercommand and str(pm).upper() in ["YES","TRUE"]:
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

            embed = discord.Embed(title=f"{self.bot.user.name}'s Help Command", url="https://discord.gg/947ramn",
            description=f"**Bot Invite Link:** [https://ngc.discord.bot](https://discord.com/oauth2/authorize?client_id=810377376269205546&scope=bot&permissions=8)\n"
                        f"**Support Server:**  [https://discord.gg/ngc](https://discord.gg/947ramn)", color=default.config()["embed_color"])

            embed.set_footer(text=f"Use \"{ctx.prefix}help category\" for specific information on a category.")

            valid_cogs = []
            msg = ""
            for cog in sorted(self.bot.cogs):
                c = self.bot.get_cog(cog)
                if c.qualified_name.upper() in COG_EXCEPTIONS and ctx.author.id not in OWNERS: continue
                valid_cogs.append(c)
            for c in valid_cogs:
                line = f"\n`{c.qualified_name}` {c.description}\n"
                msg += line

            embed.add_field(name=f"**Current Categories**", value=f"** **{msg}")

            await self.send_help(ctx, embed, pm, delete_after)

        elif trigger is True:

              ######################
             ## Manages Cog Help ##
            ######################

            if invokercommand.lower() in ["info","general","information","utils","util","misc","utilities","utility"]:
                cog = self.bot.get_cog("General")
                return await self.helper_func(ctx, cog=cog, name=invokercommand, pm = pm, delete_after=delete_after)

            if invokercommand.lower() in ["logging","logger","logs"]:
                cog = self.bot.get_cog("Logging")
                return await self.helper_func(ctx, cog=cog, name=invokercommand, pm = pm, delete_after=delete_after)

            if invokercommand.lower() in ["mod","moderator","punishment","moderation","cleanup"]:
                cog = self.bot.get_cog("Moderation")
                return await self.helper_func(ctx, cog=cog, name=invokercommand, pm = pm, delete_after=delete_after)

            if invokercommand.lower() in ["owner","master","creator","owners","hidden","own","config","conf"]:
                cog = self.bot.get_cog("Config")
                return await self.helper_func(ctx, cog=cog, name=invokercommand, pm = pm, delete_after=delete_after)
                
            if invokercommand.lower() in ["roles","role","serverroles"]:
                cog = self.bot.get_cog("Roles")
                return await self.helper_func(ctx, cog=cog, name=invokercommand, pm = pm, delete_after=delete_after)

            if invokercommand.lower() in ["admin","administration","administrator","settings","setup","configuration","auto","automod","automoderation"]:
                cog = self.bot.get_cog("Settings")
                return await self.helper_func(ctx, cog=cog, name=invokercommand, pm = pm, delete_after=delete_after)

            if invokercommand.lower() in ["stats","statistics","track","tracking"]:
                cog = self.bot.get_cog("Statistics")
                return await self.helper_func(ctx, cog=cog, name=invokercommand, pm = pm, delete_after=delete_after)
    
            else:

                  ##########################
                 ## Manages Command Help ##
                ##########################

                valid_cog = ""
                valid_commands = ""
                valid_help = ""
                valid_brief = ""
                for cog in sorted(self.bot.cogs):
                    cog_commands = sorted(self.bot.get_cog(cog).get_commands(), key=lambda x:x.name)
                    for command in cog_commands:
                        if str(command.name) == invokercommand.lower() or invokercommand.lower() in command.aliases:
                            if command.hidden and ctx.author.id not in OWNERS: continue
                            valid_commands += (command.name)
                            valid_help += (command.help)
                            if not command.brief:
                                command.brief = "None"
                            valid_brief += (command.brief)
                            valid_cog += (str(command.cog.qualified_name))

                if valid_commands != "":
                    help_embed = discord.Embed(title=f"Category: `{valid_cog.title()}`", 
                    description=f"**Bot Invite Link:** [https://ngc.discord.bot](https://discord.com/oauth2/authorize?client_id=810377376269205546&scope=bot&permissions=8)\n"
                                f"**Support Server:**  [https://discord.gg/ngc](https://discord.gg/947ramn)", 
                    color=default.config()["embed_color"])
                    help_embed.set_footer(text=f"Use \"{ctx.prefix}help command\" for information and usage examples on a command.")
                    help_embed.add_field(name=f"**Command Name:** `{valid_commands.title()}`", 
                    value=f"\n**Description:** `{valid_brief}`\n"
                          f"```yaml\n{valid_help}```")
                    await self.send_help(ctx, help_embed, pm, delete_after)
                else: 
                    await ctx.send(f"<:error:816456396735905844> No command named `{invokercommand}` found.")


    def _get_help(self, command, max_len = 0):
        # A helper method to return the command help - or a placeholder if none
        if max_len == 0:
            # Get the whole thing
            if command.help == None:
                return "No description..."
            else:
                return command.help
        else:
            if command.help == None:
                c_help = "No description..."
            else:
                c_help = command.help.split("\n")[0]
            return (c_help[:max_len-3]+"...") if len(c_help) > max_len else c_help

    def _is_submodule(self, parent, child):
        return parent == child or child.startswith(parent + ".")

    @commands.command(
        brief   = "Dumps a timestamped, formatted list of commands and descriptions.", 
        aliases = ["txthelp","helpfile"]
    )
    async def dumphelp(self, ctx):
        """
        Usage: -dumphelp
        Aliases: -txthelp, -helpfile
        Output: List of commands and descriptions
        """
        timestamp = datetime.today().strftime("%m-%d-%Y")

        help_txt = './data/wastebin/Help-{}.txt'.format(timestamp)

        message = await ctx.send('Uploading help list...')
        msg = ''
        prefix = ctx.prefix
        
        # Get and format the help
        for cog in sorted(self.bot.cogs):
            if cog.upper() in COG_EXCEPTIONS:
                continue
            cog_commands = sorted(self.bot.get_cog(cog).get_commands(), key=lambda x:x.name)
            cog_string = ""
            # Get the extension
            the_cog = self.bot.get_cog(cog)
            # Make sure there are non-hidden commands here
            visible = []
            for command in self.bot.get_cog(cog).get_commands():
                if not command.hidden:
                    visible.append(command)
            if not len(visible):
                # All hidden - skip
                continue
            cog_count = "1 command" if len(visible) == 1 else "{} commands".format(len(visible))
            for e in self.bot.extensions:
                b_ext = self.bot.extensions.get(e)
                if self._is_submodule(b_ext.__name__, the_cog.__module__):
                    # It's a submodule
                    cog_string += "{}{} Cog ({}) - {}.py Extension:\n".format(
                        "    ",
                        cog,
                        cog_count,
                        e[5:]
                    )
                    break
            if cog_string == "":
                cog_string += "{}{} Cog ({}):\n".format(
                    "    ",
                    cog,
                    cog_count
                )
            for command in cog_commands:
                cog_string += "{}  {}\n".format("    ", prefix + command.name + " " + command.signature)
                cog_string += "\n{}  {}  {}\n\n".format(
                    "\t",
                    " "*len(prefix),
                    self._get_help(command, 80)
                )
            cog_string += "\n"
            msg += cog_string
        
        # Encode to binary
        # Trim the last 2 newlines
        msg = msg[:-2].encode("utf-8")
        with open(help_txt, "wb") as myfile:
            myfile.write(msg)

        await ctx.send(file=discord.File(help_txt))
        await message.edit(content='<:checkmark:816534984676081705> Uploaded Help-{}.txt'.format(timestamp))
        os.remove(help_txt)




        

            
