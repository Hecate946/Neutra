import os
import re
import sys
import json
import time

import aiohttp
import discord
import logging
import traceback
import collections
import tracemalloc

from colr import color
from datetime import datetime
from discord.ext import commands, tasks
from discord_slash.client import SlashCommand
from logging.handlers import RotatingFileHandler

from settings import database, cleanup
from utilities import utils
from settings import constants


MAX_LOGGING_BYTES = 32 * 1024 * 1024  # 32 MiB
COGS = [x[:-3] for x in sorted(os.listdir("././cogs")) if x.endswith(".py")]

cxn = database.postgres

# Set up our command logger
command_logger = logging.getLogger("NGC0000")
command_logger.setLevel(logging.DEBUG)
command_logger_handler = RotatingFileHandler(
    filename="./data/logs/commands.log",
    encoding="utf-8",
    mode="w",
    maxBytes=MAX_LOGGING_BYTES,
    backupCount=5,
)
command_logger.addHandler(command_logger_handler)
command_logger_format = logging.Formatter(
    "\n{asctime}: [{levelname}] {name} || {message}", "%Y-%m-%d %H:%M:%S", style="{"
)
command_logger_handler.setFormatter(command_logger_format)

# Set up our basic info logger
info_logger = logging.getLogger("INFO_LOGGER")
info_logger.setLevel(logging.INFO)
info_logger_handler = RotatingFileHandler(
    filename="./data/logs/info.log",
    encoding="utf-8",
    mode="w",
    maxBytes=MAX_LOGGING_BYTES,
    backupCount=5,
)
info_logger.addHandler(info_logger_handler)
info_logger_format = logging.Formatter(
    "{asctime}: [{levelname}] {name} || {message}", "%Y-%m-%d %H:%M:%S", style="{"
)
info_logger_handler.setFormatter(info_logger_format)

# Set up the error logger
error_logger = logging.getLogger("ERROR_LOGGER")
error_logger.setLevel(logging.WARNING)
error_logger_handler = RotatingFileHandler(
    filename="./data/logs/errors.log",
    encoding="utf-8",
    mode="w",
    maxBytes=MAX_LOGGING_BYTES,
    backupCount=5,
)
error_logger.addHandler(error_logger_handler)
error_logger_format = logging.Formatter(
    "{asctime}: [{levelname}] {name} || {message}", "%Y-%m-%d %H:%M:%S", style="{"
)
error_logger_handler.setFormatter(error_logger_format)


# Set up the traceback logger this just dumps all the errors
traceback_logger = logging.getLogger("TRACEBACK_LOGGER")
traceback_logger.setLevel(logging.WARNING)
traceback_logger_handler = RotatingFileHandler(
    filename="./data/logs/traceback.log",
    encoding="utf-8",
    mode="w",
    maxBytes=MAX_LOGGING_BYTES,
    backupCount=5,
)
traceback_logger.addHandler(traceback_logger_handler)
traceback_logger_format = logging.Formatter(
    "{asctime}: [{levelname}] {name} || {message}", "%Y-%m-%d %H:%M:%S", style="{"
)
traceback_logger_handler.setFormatter(traceback_logger_format)


async def get_prefix(bot, message):
    if not message.guild:
        prefix = constants.prefix
        return commands.when_mentioned_or(prefix + " ", prefix)(bot, message)
    prefix = await database.fetch_prefix(message.guild.id)
    if prefix is None:
        await database.update_server(message.guild, message.guild.members)
        await database.fix_server(message.guild.id)
        prefix = await database.fetch_prefix(message.guild.id)
    return commands.when_mentioned_or(prefix + " ", prefix)(bot, message)


# Main bot class. Heart of the application
class NGC0000(commands.AutoShardedBot):
    def __init__(self):

        super().__init__(
            command_prefix=get_prefix,
            case_insensitive=True,
            owner_ids=constants.owners,
            intents=discord.Intents.all(),
        )

        self.session = aiohttp.ClientSession(loop=self.loop)
        # discord invite regex
        self.dregex = re.compile(
            r"(?:https?://)?discord(?:app)?\.(?:com/invite|gg)/[a-zA-Z0-9]+/?"
        )
        # Start the task loop
        self.status_loop.start()

    def setup(self):

        # Sets up all the global bot variables
        if not hasattr(self, "bot_ready"):
            self.bot_ready = False

        if not hasattr(self, "command_stats"):
            self.command_stats = collections.Counter()

        if not hasattr(self, "socket_events"):
            self.socket_events = collections.Counter()

        if not hasattr(self, "batch_inserts"):
            self.batch_inserts = int()

        if not hasattr(self, "messages"):
            self.messages = int()

        if not hasattr(self, "emojis_seen"):
            self.emojis_seen = int()

        if not hasattr(self, "nickchanges"):
            self.nickchanges = int()

        if not hasattr(self, "namechanges"):
            self.namechanges = int()

        if not hasattr(self, "avchanges"):
            self.avchanges = int()

        if not hasattr(self, "rolechanges"):
            self.rolechanges = int()

        if not hasattr(self, "uptime"):
            self.uptime = datetime.utcnow()

        if not hasattr(self, "starttime"):
            self.starttime = int(time.time())

        if not hasattr(self, "cxn"):
            self.cxn = cxn

        if not hasattr(self, "emote_dict"):
            self.emote_dict = constants.emotes

        if not hasattr(self, "server_settings"):
            self.server_settings = database.settings

        if not hasattr(self, "session"):
            self.session = self.session

        if not hasattr(self, "constants"):
            self.constants = constants

        if not hasattr(self, "slash"):
            self.slash = SlashCommand(self, sync_commands=True)

        if not hasattr(self, "bot_settings"):
            self.bot_settings = database.bot_settings

        # loads all the cogs in ./cogs and prints them on sys.stdout
        for cog in COGS:
            self.load_extension(f"cogs.{cog}")
            print(color(fore="#3EC4CD", text=f"Loaded: {str(cog).upper()}"))

    def run(self, mode="production"):
        # Startup function that gets called in starter.py

        self.setup()  # load the cogs

        self.token = constants.token
        try:
            super().run(self.token, reconnect=True)  # Run the bot
        finally:  # Write up our json files with the stats from the session.
            self.status_loop.stop()
            print("\nKilled")
            with open("./data/json/commands.json", "w", encoding="utf-8") as fp:
                json.dump(self.command_stats, fp, indent=2)
            with open("./data/json/sockets.json", "w", encoding="utf-8") as fp:
                json.dump(self.socket_events, fp, indent=2)
            with open("./data/json/stats.json", "w", encoding="utf-8") as fp:
                stats = {
                    "client name": self.user.name,
                    "client id": self.user.id,
                    "client age": utils.time_between(
                        self.user.created_at.timestamp(), time.time()
                    ),
                    "client owner": f"{self.owner_ids[0]}, {self.get_user(self.owner_ids[0])}",
                    "last run": utils.timeago(datetime.utcnow() - self.uptime),
                    "commands run": len(self.command_stats),
                    "messages seen": self.messages,
                    "server count": len(self.guilds),
                    "channel count": len([x for x in self.get_all_channels()]),
                    "member count": len([x for x in self.get_all_members()]),
                    "batch inserts": self.batch_inserts,
                    "username changes": self.namechanges,
                    "nickname changes": self.nickchanges,
                    "avatar changes": self.avchanges,
                }

                json.dump(stats, fp, indent=2)

            data = utils.load_json("config.json")
            if mode == "tester":
                utils.write_json("config_test.json", data)
            else:
                utils.write_json("config_prod.json", data)

    async def close(self):  # Shutdown the bot cleanly
        await super().close()
        await self.session.close()

    async def process_commands(self, message):
        await self.wait_until_ready()
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
            if check.get("Delete", False):
                delete = True
            if check.get("Ignore", False):
                ignore = True
            try:
                respond = check["Respond"]
            except KeyError:
                pass
            try:
                react = check["Reaction"]
            except KeyError:
                pass
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
    async def status_loop(self):
        # ( ͡° ͜ʖ ͡°) The real reason why I code ( ͡° ͜ʖ ͡°)
        # (っ´▽｀)っ So pretty...
        # self.index += 1

        # msg    = f"DATABASE TASK UPDATE #{self.index}"
        # top    = "##" + "#" * (len(msg) + 4)
        # middle = " ##" + f" {msg} " + "##"
        # bottom = "  ##"+ "#" * (len(msg) + 4)
        # sys.stdout.write("\033[F" * 3)
        # print(color(fore="#1EDA10", text=top))
        # print(color(fore="#1EDA10", text=middle))
        # print(color(fore="#1EDA10", text=bottom))

        # For some weird reason after awhile the status doesn't show up so...
        # updating it with the task loop.
        await self.set_status()

    @status_loop.before_loop
    async def before_status_loop(self):
        await self.wait_until_ready()
        await self.set_status()

        member_list = []
        for member in self.get_all_members():
            member_list.append(member)
        try:
            await database.initialize(self.guilds, member_list)
        except Exception as e:
            print(utils.traceback_maker(e))
        # Beautiful console logging on startup

        message = f"Client Name: {bot.user}"
        uid_message = f"Client ID:   {bot.user.id}"
        user_count_message = f"Users: {len([ x for x in self.get_all_members()])}   Servers: {len(self.guilds)}"
        separator = "=" * max(len(message), len(uid_message), len(user_count_message))
        print(color(fore="#ff008c", text=separator))
        try:
            print(color(fore="#ff008c", text=message))
        except Exception:
            print(color(fore="#ff008c", text=message.encode(errors="replace").decode()))
        print(color(fore="#ff008c", text=uid_message))
        print(color(fore="#ff008c", text=user_count_message))
        print(color(fore="#ff008c", text=separator))

        await cleanup.cleanup_servers(self.guilds)

        try:
            channel = self.get_channel(constants.reboot["channel"])
            msg = await channel.fetch_message(constants.reboot["message"])
            await msg.edit(
                content=self.emote_dict["success"]
                + " "
                + "{0}ed Successfully.".format(constants.reboot["invoker"])
            )
        except Exception:
            pass

        from settings import cache

        cache.Settings(self)

        self.bot_ready = True

    async def set_status(self):
        # This sets the bot's presence, status, and activity
        # based off of the values in ./config.json
        if self.constants.activity == "listening":
            a = discord.ActivityType.listening
        elif self.constants.activity == "watching":
            a = discord.ActivityType.watching
        elif self.constants.activity == "competing":
            a = discord.ActivityType.competing
        else:
            a = discord.ActivityType.playing

        if self.constants.presence == "":
            activity = discord.Activity(type=a)
        else:
            presence = self.constants.presence
            activity = discord.Activity(type=a, name=presence)

        status = self.constants.status
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

    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            name = (
                str(ctx.command.qualified_name)
                if ctx.command.parent is None
                else str(ctx.command.full_parent_name)
            )
            help_command = self.get_command("help")
            await help_command(ctx, invokercommand=name)

        elif isinstance(error, commands.BadArgument):
            await ctx.send(f"{self.emote_dict['failed']} {error}")

        elif isinstance(error, commands.NoPrivateMessage):
            # Debating whether or not to ignore this.
            await ctx.author.send(
                f"{self.emote_dict['failed']} This command cannot be used in private messages."
            )

        elif isinstance(error, commands.CommandOnCooldown):
            await ctx.send(
                f"{self.emote_dict['error']} This command is on cooldown... retry in {error.retry_after:.2f} seconds."
            )

        elif isinstance(error, commands.DisabledCommand):
            # This could get annoying so lets just comment out for now
            ctx.message.add_reaction(self.bot.emote_dict["failed"])
            await ctx.send(f"{self.emote_dict['failed']} This command is disabled.")
            pass

        elif isinstance(error, discord.errors.Forbidden):
            pass

        elif isinstance(error, commands.CommandInvokeError):
            err = utils.traceback_maker(error.original, advance=True)
            if "or fewer" in str(error):
                return await ctx.send(
                    f"{self.emote_dict['failed']} Result was greater than the character limit."
                )
            print(
                color(
                    fore="FF0000",
                    text=f"\nCommand {ctx.command.qualified_name} raised the error: {error.original.__class__.__name__}: {error.original}",
                ),
                file=sys.stderr,
            )
            if ctx.guild is None:
                destination = "Private Message"
            else:
                destination = (
                    "#{0.channel} [{0.channel.id}] ({0.guild}) [{0.guild.id}]".format(
                        ctx
                    )
                )
            error_logger.warning(
                "{0.author} in {1}:\n\tCONTENT: {0.message.content}\n\tERROR : {2.original.__class__.__name__}:{2.original}".format(
                    ctx, destination, error
                )
            )
            traceback_logger.warning(err)

        elif isinstance(error, commands.BotMissingPermissions):
            # Readable error so just send it to the channel where the error occurred.
            await ctx.send(f"{self.emote_dict['error']} {error}")

        elif isinstance(error, commands.CheckFailure):
            # Readable error so just send it to the channel where the error occurred.
            # Or not
            # await ctx.send(f"{self.emote_dict['error']} {error}")
            pass

        else:
            # Ok so here we don't really know what the error is, so lets print the basic error.
            # We can always check pm2.log for the full error later if necessary
            err = utils.traceback_maker(error, advance=True)
            print(color(fore="FF0000", text="Error"))
            print(error)
            if ctx.guild is None:
                destination = "Private Message"
            else:
                destination = (
                    "#{0.channel} [{0.channel.id}] ({0.guild}) [{0.guild.id}]".format(
                        ctx
                    )
                )
            error_logger.warning(
                "{0.author} in {1}:\n\tCONTENT: {0.message.content}\n\tERROR : {2}\n".format(
                    ctx, destination, error
                )
            )
            traceback_logger.warning(str(err) + "\n")

    async def on_guild_join(self, guild):
        if self.bot_ready is False:
            return

        await database.update_server(guild, guild.members)
        await database.fix_server(guild.id)

    async def on_guild_remove(self, guild):
        if self.bot_ready is False:
            return
        # This happens when the bot gets kicked from a server.
        # No need to waste any space storing their info anymore.
        await cleanup.cleanup_servers(self.guilds)

    async def on_ready(self):
        # from discord_slash import utils
        # await utils.manage_commands.remove_all_commands_in(bot.user.id, bot.token, 740734113086177433)
        await cleanup.cleanup_servers(self.guilds)

    async def on_message(self, message):
        if self.bot_ready is False:
            return
        await self.process_commands(message)
        if isinstance(message.channel, discord.DMChannel):
            if self.dregex.match(message.content):
                await message.channel.send(
                    f"Hey {message.author.mention}! if you're looking to invite me to your server, use this link:\n<{self.constants.oauth}>"
                )


bot = NGC0000()
