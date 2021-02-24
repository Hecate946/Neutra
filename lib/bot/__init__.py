import asyncio
import discord
import os
import sys
import traceback
import logging

from datetime import datetime
from discord.ext import commands, tasks
from discord.ext.commands import Bot as BotBase


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

owners = default.config()["owners"]

COGS = [x[:-3] for x in sorted(os.listdir('././cogs')) if x.endswith('.py') and x != "__init__.py"]

async def get_prefix(bot, message):
    if not message.guild:
        prefix = default.config()["prefix"]
        return commands.when_mentioned_or(prefix)(bot, message)
    prefix = db.field("SELECT Prefix FROM guilds WHERE GuildID = ?", message.guild.id)
    return commands.when_mentioned_or(prefix)(bot, message)

        
class Bot(BotBase):
    def __init__(self):

        self.db_updater.start()

        super().__init__(command_prefix=get_prefix, case_insensitive=True, owner_ids=owners, intents=discord.Intents.all(),)


    def setup(self):
        for cog in COGS:
            print(f"Loaded: {str(cog).upper()}")
            self.load_extension(f"cogs.{cog}")
        

    def run(self, version):
        self.VERSION = default.config()["version"]

        self.setup()

        self.token = default.config()["token"]

        super().run(self.token, reconnect=True)

    
    async def process_commands(self, message):
        ctx = await self.get_context(message, cls=commands.Context)
        if ctx.command is not None:
            await self.invoke(ctx)


    @tasks.loop(minutes=1)
    async def db_updater(self):
        await self.update_db()

    @db_updater.before_loop
    async def before_some_task(self):
        await self.wait_until_ready()
        #Not pretty but might as well set the bots status here
        await self.set_status()

    async def set_status(self):

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


    async def update_db(self):
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
            user_info = db.records(
                """ SELECT *
                    FROM users 
                    WHERE id=? 
                    AND server=?
                """, member.id, member.guild.id
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
        await self.update_db()


    async def on_ready(self):
        if not hasattr(self, 'uptime'):
            self.uptime = datetime.utcnow()

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
        except:
            print(message.encode(errors='replace').decode())
        print(uid_message)
        print(separator)


    async def on_message(self, message):
        if message.author.bot:
            return
        if not message.guild:
            # This wasn't said in a server, process commands, then return
            await bot.process_commands(message)
            return
        try:
            message.author.roles
        except AttributeError:
            # Not a User
            await bot.process_commands(message)
            return
        # Check if we need to ignore or delete or react to the message
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