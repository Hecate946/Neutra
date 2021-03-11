import os
import sys
import time
import aiohttp
import asyncio
import asyncpg
import discord
import logging
import traceback

from logging.handlers import RotatingFileHandler
from datetime import datetime
from discord.ext import commands, tasks
from colr import color

from utilities import default

MAX_LOGGING_BYTES = 32 * 1024 * 1024 # 32 MiB
BUILD_PATH        = "data/db/script.sql"
COGS              = [x[:-3] for x in sorted(os.listdir('././cogs')) if x.endswith('.py') and x != "__init__.py"]
OWNERS            = default.config()["owners"]
CONNECTION        = asyncio.get_event_loop().run_until_complete(asyncpg.create_pool(default.config()["database"]))

# Set up our command logger

command_logger = logging.getLogger("NGC0000")
command_logger.setLevel(logging.DEBUG)
command_logger_handler = RotatingFileHandler(
    filename="./data/logs/commands.log",
    encoding="utf-8",
    mode="w",
    maxBytes=MAX_LOGGING_BYTES,
    backupCount=5
    )
command_logger.addHandler(command_logger_handler)
command_logger_format = logging.Formatter(
    '{asctime}: [{levelname}] {name} || {message}', '%Y-%m-%d %H:%M:%S', style='{'
    )
command_logger_handler.setFormatter(command_logger_format)

# This basically clears my console and beautifies the startup
try:
    os.system('clear')
except Exception:
    for _ in range(100):
        print()

connection = CONNECTION

async def get_prefix(bot, message):
    if not message.guild:
        prefix = default.config()["prefix"]
        return commands.when_mentioned_or(prefix)(bot, message)
    query = '''SELECT prefix FROM servers WHERE server_id = $1;'''
    prefix = await connection.fetchrow(query, message.guild.id)
    return commands.when_mentioned_or(prefix[0])(bot, message)

#Main bot class. Heart of the application
class NGC0000(commands.AutoShardedBot):
    def __init__(self):

        super().__init__(command_prefix=get_prefix, case_insensitive=True, owner_ids=OWNERS, intents=discord.Intents.all(),)
        # Just an index to show how many database updates have taken place
        self.index = 0

    def setup(self):
        for cog in COGS:
            self.load_extension(f"cogs.{cog}")
            print(color(fore="#3EC4CD", text=f"Loaded: {str(cog).upper()}"))


    async def scriptexec(self, path):
        with open(path, "r", encoding="utf-8") as script:
            await connection.execute(script.read())


    def run(self):
        self.setup()

        self.token = default.config()["token"]

        super().run(self.token, reconnect=True)

    
    async def process_commands(self, message):
        ctx = await self.get_context(message, cls=commands.Context)
        if ctx.command is None:
            return
        if message.author.bot:
            return
        if not message.guild:
            # These are DM commands
            await self.invoke(ctx)
            return
        try:
            message.author.roles
        except AttributeError:
            # Not a User
            await self.invoke(ctx)
            return

        # Check if we need to ignore, delete or react to the message
        ignore, delete, react = False, False, False
        respond = None
        for cog in self.cogs:
            cog = self.get_cog(cog)
            try:
                check = await cog.message(message)
            except AttributeError:
                continue

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
            # Delete the message
            await message.delete()
        if not ignore:
            if respond:
                # We have something to say
                await message.channel.send(respond)
            if react:
                # We have something to react with
                for r in react:
                    await message.add_reaction(r)
            await self.invoke(ctx)


    @tasks.loop(minutes=10)
    async def db_updater(self):
        await self.update_db()
        # The real 
        self.index += 1
        msg    = f"DATABASE TASK UPDATE #{self.index}"
        top    = "##" + "#" * (len(msg) + 4)
        middle = " ##" + f" {msg} " + "##"
        bottom = "  ##"+ "#" * (len(msg) + 4)
        print(color(fore="#1EDA10", text=top))
        print(color(fore="#1EDA10", text=middle))
        print(color(fore="#1EDA10", text=bottom))
        sys.stdout.write("\033[F" * 3)
        # Not pretty but might as well set the bot status here
        # For some weird reason after awhile the status doesn't show up so... updating it every minute.
        await self.set_status()

    @db_updater.before_loop
    async def before_some_task(self):
        SEPARATOR = '================================'
        await self.wait_until_ready()
        # After the bot is ready, but before the task loop for the DB updater starts,
        # We can execute the SQL script to make sure we have all our tables.
        if os.path.isfile(BUILD_PATH):
            print(color(fore="#830083", text=SEPARATOR))
            print(color(fore="#830083", text="Executing data/db/script.sql..."))
            print(color(fore="#830083", text=SEPARATOR))
            await self.scriptexec(BUILD_PATH)
            await asyncio.sleep(0.7)
            sys.stdout.write("\033[F" * 2)
            print(color(fore="#830083", text="Successfully executed SQL script"))
            print(color(fore="#830083", text=SEPARATOR))
            await asyncio.sleep(0.7)
            sys.stdout.write("\033[F" * 2)
            if CONNECTION is not None:
                print(color(fore="#830083", text=f"Established Database Connection."))
                print(color(fore="#830083", text=SEPARATOR))

    async def set_status(self):
        if default.config()["activity"] == "listening":
            a = discord.ActivityType.listening
        elif default.config()["activity"] == "watching":
            a = discord.ActivityType.watching
        elif default.config()["activity"] == "competing":
            a = discord.ActivityType.competing
        else:
            a = discord.ActivityType.playing

        if default.config()["presence"] == "":
            activity = discord.Activity(type=a)
        else:
            presence = default.config()["presence"]
            activity = discord.Activity(type=a, name=presence)

        status = default.config()["status"]
        if status == "idle":
            s = discord.Status.idle
        elif status == "dnd":
            s = discord.Status.dnd
        elif status == "offline":
            s = discord.Status.invisible
        else:
            # Online when in doubt
            s = discord.Status.online

        await self.change_presence(status=s, activity=activity)


    async def update_db(self):

        await connection.executemany("""
        INSERT INTO servers (server_id, server_name, server_owner_id, server_owner_name) VALUES ($1, $2, $3, $4)
        ON CONFLICT (server_id) DO UPDATE SET server_id = $1, server_name = $2, server_owner_id = $3, server_owner_name = $4
        """, ((server.id, server.name, server.owner.id, str(server.owner)) for server in self.guilds))


        await connection.executemany("""INSERT INTO roleconfig (server_id, whitelist, autoroles, reassign) VALUES ($1, $2, $3, $4)
        ON CONFLICT (server_id) DO NOTHING""",
        ((server.id, None, None, True) for server in self.guilds))


        await connection.executemany("INSERT INTO logging VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13) ON CONFLICT (server_id) DO NOTHING",
        ((server.id, True, True, True, True, True, True, True, True, True, True, None, None) for server in self.guilds))


        await connection.executemany("""INSERT INTO moderation VALUES ($1, $2, $3, $4)
        ON CONFLICT (server_id) DO NOTHING""", ((server.id, False, None, None) for server in self.guilds))


        member_list = self.get_all_members()
        for member in member_list:
            query = '''SELECT * FROM users WHERE user_id = $1 AND server_id = $2'''
            result = await connection.fetch(query, member.id, member.guild.id) or None
            if result is not None:
                continue
            roles = ','.join([str(x.id) for x in member.roles if x.name != "@everyone"])
            names = member.display_name

            query = '''
                    INSERT INTO users (
                        user_id, 
                        server_id,
                        nicknames, 
                        roles,
                        eyecount
                    ) 
                    VALUES ($1, $2, $3, $4, $5)
                    '''
            await connection.execute(
                query,
                member.id,
                member.guild.id,
                names,
                roles,
                0
            )

    @commands.Cog.listener()
    async def on_command(self, ctx):
        message = ctx.message
        destination = None
        if ctx.guild is None:
            destination = 'Private Message'
        else:
            destination = '#{0.channel} [{0.channel.id}] ({0.guild}) [{0.guild.id}]'.format(message)
        command_logger.info('{0.author} in {1}: {0.content}'.format(message, destination))

    async def on_command_error(self, ctx, error):

        if isinstance(error, commands.MissingRequiredArgument) or isinstance(error, commands.BadArgument):
            name = str(ctx.command.qualified_name) if ctx.command.parent is None else str(ctx.command.full_parent_name)
            help_command = self.get_command("help")
            await help_command(ctx, invokercommand=name)

        elif isinstance(error, commands.NoPrivateMessage):
            await ctx.author.send('<:fail:816521503554273320> This command cannot be used in private messages.')

        elif isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"<:error:816456396735905844> This command is on cooldown... retry in {error.retry_after:.2f} seconds.")

        elif isinstance(error, commands.DisabledCommand):
            await ctx.author.send('<:fail:816521503554273320> This command is disabled.')

        elif isinstance(error, commands.CommandInvokeError):
            err = default.traceback_maker(error.original, advance=True)
            if "2000 or fewer" in str(error) and len(ctx.message.clean_content) > 1900:
                return await ctx.send("<:fail:816521503554273320> Result was greater than 2000 characters. Aborting...")
            print(color(fore="FF0000", text=f'\nCommand {ctx.command.qualified_name} raised the error: {error.original.__class__.__name__}: {error.original}'), file=sys.stderr)
            print(err, file=sys.stderr)

        elif isinstance(error, commands.BotMissingPermissions):
            await ctx.send(f"<:error:816456396735905844> {error}")

        else:
            print(color(fore="FF0000", text="Error"))
            print(error)


    async def on_guild_join(self, guild):
        await self.update_db()


    async def on_guild_remove(self, guild):
        # This happens when the bot gets kicked from a server. 
        # No need to waste any space storing their info anymore.
        connection.execute("""
        DELETE FROM servers WHERE server_id = $1
        """, guild.id)

        connection.execute("""
        DELETE FROM users WHERE server_id = $1
        """, guild.id)

        connection.execute("""
        DELETE FROM roleconfig WHERE server_id = $1
        """, guild.id)

        connection.execute("""
        DELETE FROM mutes WHERE server_id = $1
        """, guild.id)

        connection.execute("""
        DELETE FROM logging WHERE server_id = $1
        """, guild.id)

        connection.execute("""
        DELETE FROM lockedchannels WHERE server_id = $1
        """, guild.id)

        connection.execute("""
        DELETE FROM warn WHERE server_id = $1
        """, guild.id)

        connection.execute("""
        DELETE FROM messages WHERE server_id = $1
        """, guild.id)

        connection.execute("""
        DELETE FROM ignored WHERE server_id = $1
        """, guild.id)

        connection.execute("""
        DELETE FROM snipe WHERE server_id = $1
        """, guild.id)

        connection.execute("""
        DELETE FROM profanity WHERE server_id = $1
        """, guild.id)

        connection.execute("""
        DELETE FROM moderation WHERE server_id = $1
        """, guild.id) 


    async def on_ready(self):

        if not hasattr(self, 'uptime'):
            self.uptime = datetime.utcnow()
        if not hasattr(self, 'starttime'):
            self.starttime = int(time.time())
        if not hasattr(self, 'owner'):
            self.owner = await self.fetch_user(OWNERS[0]) or "I can't find my owner"

        # Beautiful console logging on startup

        message = f'Client Name: {bot.user}'
        uid_message = f'Client ID:   {bot.user.id}'
        user_count_message = f'Users: {len([ x for x in self.get_all_members()])}   Servers: {len(self.guilds)}'
        separator = '=' * max(len(message), len(uid_message), len(user_count_message))
        print(color(fore="#ff008c", text=separator))
        try:
            print(color(fore="#ff008c", text=message))
        except:
            print(color(fore="#ff008c", text=message.encode(errors='replace').decode()))
        print(color(fore="#ff008c", text=uid_message))
        print(color(fore="#ff008c", text=user_count_message))
        print(color(fore="#ff008c", text=separator))

        # Start task loop
        await self.db_updater.start()

    async def on_message(self, message):
        await self.process_commands(message)

bot = NGC0000()
