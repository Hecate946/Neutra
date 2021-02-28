import os
import sys
import asyncio
import asyncpg
import discord
import logging
import traceback

from datetime import datetime
from discord.ext import commands, tasks

from utilities import default


BUILD_PATH = "data/db/script.sql"
COGS = [x[:-3] for x in sorted(os.listdir('././cogs')) if x.endswith('.py') and x != "__init__.py"]
CONNECTION = asyncio.get_event_loop().run_until_complete(asyncpg.create_pool(default.config()["database"]))
OWNERS = default.config()["owners"]

#This basically clears my console and beautifies the startup
try:
    os.system('clear')
except Exception:
    for _ in range(100):
        print()
SEPARATOR = '=' * len(str(CONNECTION))
print(SEPARATOR)
print(CONNECTION)
print(SEPARATOR)


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

        self.db_updater.start()


    def setup(self):
        for cog in COGS:
            print(f"Loaded: {str(cog).upper()}")
            self.load_extension(f"cogs.{cog}")


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

        # Check if we need to ignore or delete or react to the message
        ignore, delete, react = False, False, False
        respond = None
        for cog in bot.cogs:
            cog = bot.get_cog(cog)
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
        #Not pretty but might as well set the bot status here
        await self.set_status()      


    @db_updater.before_loop
    async def before_some_task(self):
        await self.wait_until_ready()
        if os.path.isfile(BUILD_PATH):
            await self.scriptexec(BUILD_PATH)


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
            presence = None
        else:
            presence = default.config()["presence"]

        activity = discord.Activity(type=a, name=presence)
        await self.change_presence(status=default.config()["status"], activity=activity)


    async def update_db(self):

        await connection.executemany("""
        INSERT INTO servers (server_id, server_name, server_owner_id, server_owner_name) VALUES ($1, $2, $3, $4) ON CONFLICT (server_id) DO NOTHING
        """, ((server.id, server.name, server.owner.id, str(server.owner)) for server in self.guilds))


        await connection.executemany("INSERT INTO roleconfig (server, whitelist, autoroles, reassign) VALUES ($1, $2, $3, $4) ON CONFLICT DO NOTHING",
        ((server.id, None, None, True) for server in self.guilds))


        await connection.executemany("INSERT INTO logging VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13) ON CONFLICT DO NOTHING",
        ((server.id, True, True, True, True, True, True, True, True, True, True, None, None) for server in self.guilds))


        member_list = self.get_all_members()
        for member in member_list:
            query = '''SELECT * FROM users WHERE id = $1 AND server_id = $2'''
            result = await connection.fetch(query, member.id, member.guild.id)
            if result !=[]: continue
            roles = ','.join([str(x.id) for x in member.roles if x.name != "@everyone"])
            names = member.display_name
            await connection.execute("INSERT INTO users VALUES ($1, $2, $3, $4, $5, $6, $7, $8)",
            member.id, roles, member.guild.id, names, 0, 0, 0, None)


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

        message = 'Logged in as %s.' % bot.user
        uid_message = 'Client ID: %s.' % bot.user.id
        user_count_message = f'Users: {len([ x for x in self.get_all_members()])}     Servers: {len(self.guilds)}'
        separator = '=' * max(len(message), len(uid_message), len(user_count_message))
        print(separator)
        try:
            print(message)
        except:
            print(message.encode(errors='replace').decode())
        print(uid_message)
        print(user_count_message)
        print(separator)


    async def on_message(self, message):
        await self.process_commands(message)

bot = NGC0000()
