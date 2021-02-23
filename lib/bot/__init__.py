import asyncio
import discord
import os
import sys
import traceback
import logging

from datetime import datetime
from discord.ext import commands
from discord.ext.commands import Bot as BotBase
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from utilities import default
from ..db import db


discord_logger = logging.getLogger('discord')
discord_logger.setLevel(logging.CRITICAL)
error_handler = logging.FileHandler(filename="././data/logs/errors.log", encoding='utf-8')
discord_logger.addHandler(error_handler)


log = logging.getLogger()
log.setLevel(logging.DEBUG)
handler = logging.FileHandler(filename="././data/logs/ngc0000.log", encoding='utf-8')
log.addHandler(handler)
log = logging.getLogger(__name__)

logging.getLogger('asyncio').propagate = False
logging.getLogger('apscheduler').propagate = False
logging.getLogger('requests').propagate = False
#logging.getLogger('io').propagate = False

owners = default.config()["owners"]

COGS = [x[:-3] for x in os.listdir('././cogs') if x.endswith('.py') and x != "__init__.py"]

async def get_prefix(bot, message):
    if not message.guild:
        prefix = default.config()["prefix"]
        return commands.when_mentioned_or(prefix)(bot, message)
    prefix = db.field("SELECT Prefix FROM guilds WHERE GuildID = ?", message.guild.id)
    return commands.when_mentioned_or(prefix)(bot, message)

        
class Bot(BotBase):
    def __init__(self):
        self.ready = False
        self.scheduler = AsyncIOScheduler()

        db.autosave(self.scheduler)


        super().__init__(command_prefix=get_prefix, case_insensitive=True, owner_ids=owners, intents=discord.Intents.all(),)


    def setup(self):
        for cog in COGS:
            self.load_extension(f"cogs.{cog}")
            print(f"{cog} cog loaded")
        print("setup complete")


    def update_db(self):
        db.multiexec("INSERT OR IGNORE INTO guilds (GuildID, GuildName, GuildOwnerID, GuildOwner) VALUES (?, ?, ?, ?)",
        ((guild.id, guild.name, guild.owner.id, str(guild.owner)) for guild in self.guilds))

        db.commit()

        db.multiexec("INSERT OR IGNORE INTO roleconfig (server, whitelist, autoroles, reassign) VALUES (?, ?, ?, ?)",
        ((guild.id, None, None, True) for guild in self.guilds))

        db.commit()

        db.multiexec("INSERT OR IGNORE INTO logging VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        ((str(guild.id), 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, None, None) for guild in self.guilds))

        db.commit()

        member_list = self.get_all_members()
        for member in member_list:
            print("member: {}{}".format(member.name, member.id))
            user_info = db.records(
                """ SELECT *
                    FROM users 
                    WHERE id=? 
                    AND server=?
                """, str(member.id), member.guild.id
            )

            if user_info == []:
                roles = ','.join([str(x.id)
                                  for x in member.roles if x.name != "@everyone"])
                names = member.display_name
                db.execute(
                    """ INSERT INTO users
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, roles, str(member.guild.id), None, str(member.id), names, 0, 0, 0
                )
                db.commit()

        
    def run(self, version):
        self.VERSION = default.config()["version"]

        print("running setup...")
        self.setup()

        self.token = default.config()["token"]

        print("running bot...")
        super().run(self.token, reconnect=True)

    
    async def process_commands(self, message):
        ctx = await self.get_context(message, cls=commands.Context)
        if ctx.command is not None:
            if self.ready:
                await self.invoke(ctx)

            elif not self.ready:
                await ctx.send("I'm not ready to receive commands. Try again in a few seconds.")

            else:
                await self.invoke(ctx)
                

    async def on_connect(self):
        print("bot connected")

    async def on_disconnect(self):
        print("bot disconnected")

    async def monday(self):
        await self.job.send("Good Morning and Happy Monday HAMFAM!")


    #async def on_error(self, err, *args, **kwargs):
    #    #if isinstance(err, discord.ext.commands.context.Context.BotMissingPermissions):
    #    #await args[0].send(f"I am missing the {kwargs} permission")
    #    if err == "on_command_error":
    #        await args[0].send("Error occurred.")
    #    await self.stdout.send(f"```py\n{err}{args}{kwargs}```")


#    async def on_command_error(self, ctx, err):
#        if isinstance(err, errors.CommandInvokeError):
#            await ctx.send(err)
#            error = default.traceback_maker(err.original).replace('siamakasasi', 'X')
#            await self.stdout.send(error)
#        else:
#            await ctx.send(err)

        """

        elif isinstance(err, errors.MissingRequiredArgument) or isinstance(err, errors.BadArgument):
            helper = str(ctx.invoked_subcommand) if ctx.invoked_subcommand else str(ctx.command)
            await ctx.send_help(helper)

        elif isinstance(err, errors.CommandInvokeError):
            error = default.traceback_maker(err.original).replace('siamakasasi', 'X')

            if "2000 or fewer" in str(err) and len(ctx.message.clean_content) > 1900:
                return await ctx.send("That command requires me to display more than 2,000 characters...")

        elif isinstance(err, discord.Forbidden):
            await ctx.send("I do not have permission to do that.")

        elif isinstance(err, errors.MaxConcurrencyReached):
            await ctx.send("You've reached max capacity of command usage at once, please finish the previous one...")

        elif isinstance(err, errors.CommandOnCooldown):
            await ctx.send(f"This command is on cooldown... try again in {err.retry_after:.2f} seconds.")

        else:
            error = f"```py\n{self}{err}```".replace("siamakasasi","X")
            em=discord.Embed(description=f"**> There was an error processing the command.\n> Click [here](https://discord.gg/947ramn) then head over to {self.stdout_channel.mention} for more details.**",
                             color=ctx.guild.me.color, timestamp=datetime.utcnow())
            em.set_author(name=bot, icon_url=ctx.guild.me.avatar_url)
            await ctx.send(embed=em)
            await self.stdout_channel.send(error)
        """


#
 #   async def on_error(self, err, *args, **kwargs):
##        if err == "on_command_error":
##            await args[0].send("Error occurred.")
#
 #       await self.stdout.send(f"```py\n {self}{err}{args}{kwargs}```")
 #       raise
#
 #   @commands.Cog.listener()
 #   async def on_command_error(self, ctx, ex):
 #       print(ex)
 #       await ctx.send("Please check with the >help command or talk with a staff member")
    # @commands.Cog.listener()
    # async def on_command_error(self, ctx, exc):
    #     if any([isinstance(exc, error) for error in IGNORE_EXCEPTION]):
    #         pass
# 
    #     elif isinstance(exc, MissingRequiredArgument):
    #         await ctx.send("One or more required arguments are missing.")
# 
# 
# 
    #     elif hasattr(exc, "original"):
    #         # if isinstance(exc.original, HTTPException):
    #         #     await ctx.send("Unable to send message.")
# 
    #         if isinstance(exc.original, Forbidden):
    #             await ctx.send("I do not have permission to do that.")
# 
    #         else:
    #             raise exc.original

    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.NoPrivateMessage):
            await ctx.author.send('<:fail:812062765028081674> This command cannot be used in private messages.')
        elif isinstance(error, commands.DisabledCommand):
            await ctx.author.send('<:fail:812062765028081674> This command is disabled and cannot be used.')
        elif isinstance(error, commands.CommandInvokeError):
            print(f'In {ctx.command.qualified_name}:', file=sys.stderr)
            traceback.print_tb(error.original.__traceback__)
            print(f'{error.original.__class__.__name__}: {error.original}', file=sys.stderr)


    async def on_guild_join(self, guild):
        self.update_db()


    async def on_ready(self):
        if not self.ready:
            self.stdout = self.get_channel(805638877762420789)
            self.job = self.get_channel(793941369282494494)
            self.scheduler.add_job(self.monday, CronTrigger(day_of_week=0, hour=10, minute=0, second=0))
            self.scheduler.start()

            self.update_db()


            if default.config()["activity"] == "listening":
                a = discord.ActivityType.listening
            elif default.config()["activity"] == "watching":
                a = discord.ActivityType.watching
            elif default.config()["activity"] == "competing":
                a = discord.ActivityType.competing
            else:
                a = discord.ActivityType.playing

            activity = discord.Activity(type=a, name=default.config()["presence"])
            await self.change_presence(status=default.config()["status"], activity=activity)

            print("bot ready")
            if not hasattr(self, 'uptime'):
                self.uptime = datetime.utcnow()
            await asyncio.sleep(1)
            if os.name == 'nt':
                os.system('cls')
            else:
                try:
                    os.system('clear')
                except Exception:
                    for _ in range(100):
                        print()

            message = 'Logged in as %s.' % bot.user
            uid_message = 'User ID: %s.' % bot.user.id
            separator = '-' * max(len(message), len(uid_message))
            print(separator)
            try:
                print(message)
            except: # some bot usernames with special chars fail on shitty platforms
                print(message.encode(errors='replace').decode())
            print(uid_message)
            print(separator)
            self.ready = True
            await self.stdout.send(f"{bot.user.name} Ready")
        else:
            print("bot reconnected")


    async def on_message(self, message):
        if not message.author.bot:
            #toignore = db.record("SELECT UserID FROM ignored WHERE UserID = ?", message.author.id) or (None)
            #toignore = str(toignore).strip("(,)")
            #if str(toignore) == str(message.author.id): return None
            # Post the context too
            context = await bot.get_context(message)
            bot.dispatch("message_context", context, message)
            if not message.guild:
                # This wasn't said in a server, process commands, then return
                await bot.process_commands(message)
                return
            if message.author.bot:
                return
            try:
                message.author.roles
            except AttributeError:
                # Not a User
                await bot.process_commands(message)
                return
            # Check if we need to ignore or delete the message
            # or respond or replace
            ignore, delete, react = False, False, False
            respond = None
            for cog in bot.cogs:
                cog = bot.get_cog(cog)
                try:
                    check = await cog.message(message)
                except AttributeError:
                    # Onto the next
                    continue
                # Make sure we have things formatted right
                if not type(check) is dict:
                    check = {}
                if check.get("Delete",False):
                    delete = True
                if check.get("Ignore",False):
                    ignore = True
                try: respond = check['Respond']
                except KeyError: pass
                try: react = check['Reaction']
                except KeyError: pass
            if delete:
                # We need to delete the message - top priority
                await message.delete()
            if not ignore:
                # We're processing commands here
                if respond:
                    # We have something to say
                    await message.channel.send(respond)
                if react:
                    # We have something to react with
                    for r in react:
                        await message.add_reaction(r)
                await bot.process_commands(message)
bot = Bot()