import discord
import re

from utilities import default
from discord.ext import commands
from lib.bot import owners


COG_EXCEPTIONS = ['OWNER','HELP','CONFIG']
COMMAND_EXCEPTIONS = ['EYES']


def setup(bot):
    bot.remove_command("help")
    bot.add_cog(Help(bot))


class Help(commands.Cog):
    """
    Help command cog
    """
    def __init__(self, bot):
        self.bot = bot


      ############################
     ## Get Commands From Cogs ##
    ############################

    async def helper_func(self, ctx, cog, name, pm):
        the_cog = sorted(cog.get_commands(), key=lambda x:x.name)
        cog_commands = []
        for c in the_cog:
            if c.hidden and ctx.author.id not in owners: continue
            if str(c.name).upper() in COMMAND_EXCEPTIONS and ctx.author.id not in owners: continue
            cog_commands.append(c)
        if cog_commands:
            await self.category_embed(ctx, cog=cog.qualified_name, list=cog_commands, pm=pm)
        else:
            return await ctx.send(f":warning: No command named `{name}` found.")


      ##########################
     ## Build Category Embed ##
    ##########################
    

    async def category_embed(self, ctx, cog, list, pm):
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
        if pm is True:
            if not ctx.guild: 
                return await ctx.send(embed=embed)
            try:
                await ctx.author.send(embed=embed)
                try:
                    await ctx.message.add_reaction("<:mailbox1:811303021492305990>")
                except: return
            except:
                await ctx.send(embed=embed)
        else:
            await ctx.send(embed=embed)


    @commands.command(name="help", brief="NGC0000's Help Command")
    async def _help(self, ctx, invokercommand:str = None, pm = True):
        """
        Usage:  -help [command/category] [pm = true]
        Output: HELP!
        """
        if str(invokercommand).upper() in ["NO","FALSE"]:
            trigger = None
            pm = False

        elif invokercommand and str(pm).upper() in ["NO","FALSE"]:
            trigger = True
            pm = False

        else:
            if invokercommand:
                trigger = True
                pm = True
            else:
                trigger = None
                pm = True

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
                if c.qualified_name.upper() in COG_EXCEPTIONS: continue
                valid_cogs.append(c)
            for c in valid_cogs:
                line = f"\n`{c.qualified_name}` {c.description}\n"
                msg += line

            embed.add_field(name=f"**Current Categories**", value=f"** **{msg}")

            if pm is True:
                if not ctx.guild: 
                    return await ctx.send(embed=embed)
                try:
                    await ctx.author.send(embed=embed)
                    try:
                        await ctx.message.add_reaction("<:mailbox1:811303021492305990>")
                    except: return
                except:
                    await ctx.send(embed=embed)
            else:
                await ctx.send(embed=embed)

        elif trigger is True:

              ######################
             ## Manages Cog Help ##
            ######################

            if invokercommand.lower() in ["auto","automod","automoderation"]:
                cog = self.bot.get_cog("Automoderation")
                return await self.helper_func(ctx, cog=cog, name=invokercommand, pm = pm)

            if invokercommand.lower() in ["channel","channels","channeling","channelling"]:
                cog = self.bot.get_cog("Channels")
                return await self.helper_func(ctx, cog=cog, name=invokercommand, pm = pm)

            if invokercommand.lower() in ["config","conf"]:
                cog = self.bot.get_cog("Config")
                return await self.helper_func(ctx, cog=cog, name=invokercommand, pm = pm)

            if invokercommand.lower() in ["info","general","information"]:
                cog = self.bot.get_cog("General")
                return await self.helper_func(ctx, cog=cog, name=invokercommand, pm = pm)

            if invokercommand.lower() in ["message","messages","cleanup","msg","msgs"]:
                cog = self.bot.get_cog("Messages")
                return await self.helper_func(ctx, cog=cog, name=invokercommand, pm = pm)

            if invokercommand.lower() in ["logging","logger","logs"]:
                cog = self.bot.get_cog("Logging")
                return await self.helper_func(ctx, cog=cog, name=invokercommand, pm = pm)

            if invokercommand.lower() in ["mod","moderator","punishment","moderation"]:
                cog = self.bot.get_cog("Moderation")
                return await self.helper_func(ctx, cog=cog, name=invokercommand, pm = pm)

            if invokercommand.lower() in ["owner","master","creator","owners","hidden","own"]:
                cog = self.bot.get_cog("Owner")
                return await self.helper_func(ctx, cog=cog, name=invokercommand, pm = pm)
                
            if invokercommand.lower() in ["roles","role","serverroles"]:
                cog = self.bot.get_cog("Roles")
                return await self.helper_func(ctx, cog=cog, name=invokercommand, pm = pm)

            if invokercommand.lower() in ["admin","administration","administrator","settings","setup","configuration"]:
                cog = self.bot.get_cog("Settings")
                return await self.helper_func(ctx, cog=cog, name=invokercommand, pm = pm)

            if invokercommand.lower() in ["stats","statistics","track","tracking"]:
                cog = self.bot.get_cog("Statistics")
                return await self.helper_func(ctx, cog=cog, name=invokercommand, pm = pm)

            if invokercommand.lower() in ["warner","warning","warnings"]:
                cog = self.bot.get_cog("Warnings")
                return await self.helper_func(ctx, cog=cog, name=invokercommand, pm = pm)
    
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
                            if command.hidden and ctx.author.id not in owners: continue
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
                    if pm is True:
                        if not ctx.guild: 
                            return await ctx.send(embed=help_embed)
                        try:
                            await ctx.author.send(embed=help_embed)
                            try:
                                await ctx.message.add_reaction("<:mailbox:811303021492305990>")
                            except: return
                        except:
                            await ctx.send(embed=help_embed)
                    else:
                        await ctx.send(embed=help_embed)
                else:
                    
                    await ctx.send(f":warning: No command named `{invokercommand}` found.")


            



        

            
