import aiohttp
import discord
import asyncio
import collections
import json
import logging
import os
import re
import sys
import time
import traceback

from colr import color
from datetime import datetime
from discord.ext import commands, tasks
from discord_slash.client import SlashCommand
from logging.handlers import RotatingFileHandler

from settings import cleanup, database, constants
from utilities import utils, override as cx

MAX_LOGGING_BYTES = 32 * 1024 * 1024  # 32 MiB
COGS = [x[:-3] for x in sorted(os.listdir("././cogs")) if x.endswith(".py")]

cxn = database.postgres

# Set up our data folders
if not os.path.exists("./data/txts"):
    os.mkdir("./data/txts")
if not os.path.exists("./data/logs"):
    os.mkdir("./data/logs")
if not os.path.exists("./data/pm2"):
    os.mkdir("./data/pm2")
if not os.path.exists("./data/json"):
    os.mkdir("./data/json")

# Set up our command logger
command_logger = logging.getLogger("Snowbot")
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


def get_prefixes(bot, msg):
    """
    This fetches all custom prefixes
    and defaults to mentions & the prefix
    in ./config.json.
    """
    user_id = bot.user.id
    base = [f"<@!{user_id}> ", f"<@{user_id}> "]
    if msg.guild is None:
        base.append(constants.prefix)
    else:
        base.extend(bot.prefixes.get(msg.guild.id, [constants.prefix]))
    return base


# Main bot class. Heart of the application
class Snowbot(commands.AutoShardedBot):
    def __init__(self):
        allowed_mentions = discord.AllowedMentions(
            roles=False, everyone=False, users=True, replied_user=True
        )
        super().__init__(
            allowed_mentions=allowed_mentions,
            command_prefix=get_prefixes,
            case_insensitive=True,
            strip_after_prefix=True,
            owner_ids=constants.owners,
            intents=discord.Intents.all(),
        )
        self.avchanges = int()
        self.batch_inserts = int()
        self.command_stats = collections.Counter()
        self.constants = constants
        self.cxn = cxn
        self.dregex = re.compile(
            r"(?:https?://)?discord(?:app)?\.(?:com/invite|gg)/[a-zA-Z0-9]+/?"
        )  # discord invite regex
        self.emote_dict = constants.emotes
        self.emojis_seen = int()
        self.messages = int()
        self.namechanges = int()
        self.nickchanges = int()
        self.prefixes = database.prefixes
        self.ready = False
        self.rolechanges = int()
        self.session = aiohttp.ClientSession(loop=self.loop)
        self.slash = SlashCommand(self, sync_commands=True)
        self.socket_events = collections.Counter()

        self.cog_exceptions = ["CONFIG", "BOTADMIN", "MANAGER", "JISHAKU"]
        self.useless_cogs = ["TESTING", "BATCH", "SLASH", "TASKS"]

    def run(self, token):  # Everything starts from here
        self.setup()  # load the cogs
        try:
            super().run(token, reconnect=True)  # Run the bot
        finally:  # Write up our json files with the stats from the session.
            try:
                self.status_loop.stop()  # Stop the loop gracefully
                print(color(text="\nKilled", fore="FF0000"))
                with open("./data/json/blacklist.json", "w", encoding="utf-8") as fp:
                    json.dump(
                        self.blacklist, fp, indent=2
                    )  # New blacklisted users from the session
            except AttributeError:
                pass  # Killed the bot before it established attributes so ignore errors

    def setup(self):
        # Start the task loop
        self.status_loop.start()

        # load all blacklisted discord objects
        if not os.path.exists("./data/json/blacklist.json"):
            with open("./data/json/blacklist.json", mode="w", encoding="utf-8") as fp:
                fp.write(r"{}")
        with open("./data/json/blacklist.json", mode="r", encoding="utf-8") as fp:
            data = json.load(fp)
        blacklist = {}
        for key, value in data.items():
            blacklist[key] = value

        if not hasattr(self, "blacklist"):
            self.blacklist = blacklist

    async def close(self):  # Shutdown the bot cleanly
        try:
            runtime = time.time() - self.starttime
            query = """
                    UPDATE config SET last_run = $1,
                    runtime = runtime + $1
                    WHERE client_id = $2;
                    """
            await self.cxn.execute(query, runtime, self.user.id)
        except AttributeError:
            # Probably because the process was killed before
            # the bot attrs were set. Let's silence errors.
            pass

        await super().close()
        await self.session.close()

    ##############################
    ## Aiohttp Helper Functions ##
    ##############################

    async def query(self, url, method="get", res_method="text", *args, **kwargs):
        async with getattr(self.session, method.lower())(url, *args, **kwargs) as res:
            return await getattr(res, res_method)()

    async def get(self, url, *args, **kwargs):
        return await self.query(url, "get", *args, **kwargs)

    async def post(self, url, *args, **kwargs):
        return await self.query(url, "post", *args, **kwargs)

    def public_stats(self):
        command_list = [
            x.name
            for x in self.commands
            if not x.hidden
            and x.cog.qualified_name.upper
            not in self.useless_cogs + self.cog_exceptions
        ]
        category_list = [
            x.qualified_name.capitalize()
            for x in [self.get_cog(cog) for cog in self.cogs]
            if x.qualified_name.upper() not in self.useless_cogs + self.cog_exceptions
        ]
        return (self.hecate, command_list, category_list)

    async def process_commands(self, message):
        ctx = await self.get_context(message, cls=commands.Context)
        if ctx.command is None:
            return
        if message.author.bot:
            return
        if str(message.author.id) in self.blacklist:
            try:
                await message.add_reaction(self.emote_dict["failed"])
            except Exception:
                pass
            return
        if not self.ready:
            return await ctx.send_or_reply(
                f"{self.emote_dict['warn']} I am currently rebooting. Please wait a moment."
            )
        if not message.guild:
            # These are DM commands
            await self.invoke(ctx)
            return
        try:
            message.author.roles
        except AttributeError:
            # Not discord.Member
            await self.invoke(ctx)
            return

        if str(message.guild.id) in self.blacklist:
            try:
                await message.add_reaction(self.emote_dict["failed"])
            except Exception:
                pass
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
                react = check["React"]
            except KeyError:
                pass
        if delete:
            # Delete the message
            await message.delete()
        if respond:
            # We have something to say
            await message.channel.send(respond)
        if react:
            # We have something to react with
            for r in react:
                await message.add_reaction(r)
        if not ignore:
            await self.invoke(ctx)

    @tasks.loop(minutes=10)
    async def status_loop(self):
        """
        A status loop to keep
        whatever current status,
        presence & activity we have
        """
        await self.set_status()

    @status_loop.before_loop
    async def before_status_loop(self):
        st = time.time()
        print("Initializing Cache...")
        await self.wait_until_ready()
        print(f"Elapsed time: {str(time.time() - st)[:10]} s")
        SEPARATOR = "=" * 33
        print(color(fore="#46648F", text=SEPARATOR))
        st = time.time()
        member_list = []
        for member in self.get_all_members():
            member_list.append(member)
        print(
            color(
                fore="#46648F",
                text=f"Member   iteration : {str(time.time() - st)[:10]} s",
            )
        )
        st = time.time()
        member_list = [x for x in self.get_all_members()]
        print(
            color(
                fore="#46648F",
                text=f"Member   iteration : {str(time.time() - st)[:10]} s",
            )
        )
        try:
            await database.initialize(self, member_list)
        except Exception as e:
            print(utils.traceback_maker(e))

        # The rest of the botvars that couldn't be set earlier
        await self.load_globals()

    async def load_globals(self):
        """
        Sets up the remaining botvars
        """
        # The permissions needed to use all commands.
        perms = discord.Permissions.none()
        perms.add_reactions = True
        perms.attach_files = True
        perms.ban_members = True
        perms.embed_links = True
        perms.external_emojis = True
        perms.kick_members = True
        perms.manage_channels = True
        perms.manage_guild = True
        perms.manage_messages = True
        perms.manage_nicknames = True
        perms.manage_roles = True
        perms.manage_webhooks = True
        perms.move_members = True
        perms.read_message_history = True
        perms.read_messages = True
        perms.send_messages = True
        perms.view_audit_log = True
        if not hasattr(self, "oauth"):
            self.oauth = discord.utils.oauth_url(
                client_id=self.user.id,
                permissions=perms,
                scopes=("bot", "applications.commands"),
            )

        if not hasattr(self, "uptime"):
            self.uptime = datetime.utcnow()

        if not hasattr(self, "starttime"):
            self.starttime = time.time()

        if not hasattr(self, "statustime"):
            self.statustime = time.time()

        if not hasattr(self, "server_settings"):
            self.server_settings = database.settings

        if not hasattr(self, "invites"):
            self.invites = {}
            for guild in self.guilds:
                if guild.me.guild_permissions.manage_guild:
                    self.invites[guild.id] = await guild.invites()

        # We need to have a "home" server. So lets create one if not exists.
        if not self.constants.home:
            try:
                home = await self.create_guild(f"{self.user.name}'s Home Server.")
            except discord.errors.HTTPException:
                raise RuntimeError(
                    "I am currently in too many servers to run properly."
                )
            avchan = await home.create_text_channel("avchan")
            botlog = await home.create_text_channel("botlog")
            utils.modify_config("home", int(home.id))
            utils.modify_config("avchan", int(avchan.id))
            utils.modify_config("botlog", int(botlog.id))
            self.constants.home = home.id
            self.constants.avchan = avchan.id
            self.constants.botlog = botlog.id

        await self.finalize_startup()

    async def set_status(self):
        """
        This sets the bot's presence, status, and activity
        based off of the values in ./config.json
        """
        query = """
                SELECT (
                    activity,
                    presence,
                    status
                )
                FROM config
                WHERE client_id = $1;
                """
        status_values = await self.cxn.fetchval(query, self.user.id)
        if status_values is None:
            activity = "playing"
            presence = ""
            status = "online"
        else:
            activity, presence, status = status_values
        if activity == "listening":
            a = discord.ActivityType.listening
        elif activity == "watching":
            a = discord.ActivityType.watching
        elif activity == "competing":
            a = discord.ActivityType.competing
        else:
            a = discord.ActivityType.playing

        activity = discord.Activity(type=a, name=presence)

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

    async def finalize_startup(self):
        # Delete all records of servers that kicked the bot
        await cleanup.cleanup_servers(self.guilds)
        self.ready = True

        # loads all the cogs in ./cogs and prints them on sys.stdout
        try:
            for cog in COGS:
                self.load_extension(f"cogs.{cog}")
        except Exception as e:
            print(utils.traceback_maker(e))
            # print(color(fore="#88ABB4", text=f"Loaded: {str(cog).upper()}"))

        print(f"{self.user} ({self.user.id})")

        # See if we were rebooted by a command and send confirmation if we were.
        query = """
                SELECT (
                    reboot_invoker,
                    reboot_message_id,
                    reboot_channel_id
                ) FROM config
                WHERE client_id = $1;
                """
        reboot = await self.cxn.fetchval(query, self.user.id)
        if reboot:
            if any((item is None for item in reboot)):
                return
            reboot_invoker, reboot_message_id, reboot_channel_id = reboot
            try:
                channel = await self.fetch_channel(reboot_channel_id)
                msg = channel.get_partial_message(reboot_message_id)
                await msg.edit(
                    content=self.emote_dict["success"]
                    + " "
                    + "{0}ed Successfully.".format(reboot_invoker)
                )
            except Exception as e:
                await self.hecate.send(e)
                pass

    async def on_command_error(self, ctx, error):
        """
        Here's where we handle all command errors
        so we can give the user feedback
        """
        # This prevents any commands with local handlers being handled here in on_command_error.
        if hasattr(ctx.command, "on_error"):
            return

        # This prevents any cogs with an overwritten cog_command_error being handled here.
        if ctx.cog:
            if ctx.cog._get_overridden_method(ctx.cog.cog_command_error) is not None:
                return

        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.usage()

        elif isinstance(error, commands.BadUnionArgument):
            await ctx.usage()

        elif isinstance(error, commands.BadBoolArgument):
            argument = str(error).split()[0]
            await ctx.send_or_reply(
                f"{self.emote_dict['failed']} The argument `{argument}` is not a valid boolean."
            )

        elif isinstance(error, commands.BadArgument):
            if 'Converting to "int" failed for parameter' in str(error):
                arg = str(error).split()[-1].strip('."')
                error = f"The `{arg}` argument must be an integer."
            await ctx.send_or_reply(
                content=f"{self.emote_dict['failed']} {error}",
            )

        elif isinstance(error, commands.BadUnionArgument):
            await ctx.fail(error)

        elif isinstance(error, commands.BotMissingPermissions):
            await ctx.fail(error)

        elif isinstance(error, commands.NoPrivateMessage):
            await ctx.author.send(
                f"{self.emote_dict['failed']} This command cannot be used in private messages."
            )

        elif isinstance(error, commands.PrivateMessageOnly):
            await ctx.fail("This command can only be used in private messages.")

        elif isinstance(error, commands.CommandOnCooldown):
            await ctx.fail(
                f"This command is on cooldown... retry in {error.retry_after:.2f} seconds."
            )

        elif isinstance(error, commands.DisabledCommand):
            await ctx.message.add_reaction(self.emote_dict["failed"])
            await ctx.fail(f"This command is currently unavailable.")

        elif isinstance(error, commands.CheckFailure):
            # Previous checks didn't catch this one.
            # Readable error so just send it to where the error occurred.
            pass
            # await ctx.send_or_reply(content=f"{self.emote_dict['failed']} {error}")

        elif isinstance(error, commands.CommandInvokeError):
            err = utils.traceback_maker(error.original, advance=True)
            if "or fewer" in str(error):  # Message was too long to send
                return await ctx.fail(f" Result was greater than the character limit.")
            # Then we don't really know what this error is. Log it.
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
            print(err)

        else:
            # Ok so here we don't really know what the error is, so lets print the basic error.
            # We can always check ./pm2 logs for the full error later if necessary
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
            # destination = f"\n\tLocation: {str(ctx.author)} in #{ctx.channel} [{ctx.channel.id}] ({ctx.guild}) [{ctx.guild.id}]:\n"
            # message = f"\tContent: {ctx.message.clean_content}\n"
            # tb = traceback.format_exc().split("\n")
            # location = "./" + "/".join(tb[3].split("/")[-4:])
            # error = f'\tFile: "{location + tb[4]}:\n\tException: {sys.exc_info()[0].__name__}: {sys.exc_info()[1]}\n'
            # content = destination + message + error + "\n"
            # await ctx.log("e", content)

    async def on_guild_join(self, guild):
        if self.ready is False:
            return

        await database.update_server(guild, guild.members)
        await database.fix_server(guild.id)

    async def on_guild_remove(self, guild):
        if self.ready is False:
            return
        # This happens when the bot gets kicked from a server.
        # No need to waste any space storing their info anymore.
        await cleanup.cleanup_servers(self.guilds)

    async def on_ready(self):
        # from discord_slash import utils
        # await utils.manage_commands.remove_all_commands_in(bot.user.id, bot.token, 740734113086177433)
        pass

    async def on_message(self, message):
        await self.process_commands(message)
        if isinstance(message.channel, discord.DMChannel):
            if message.author.id != self.user.id:
                # Sometimes users DM the bot their server invite... Lets send them ours
                if self.dregex.match(message.content):
                    await message.channel.send(
                        f"Hey {message.author.mention}! if you're looking to invite me to your server, use this link:\n<{self.oauth}>"
                    )

    async def on_message_edit(self, before, after):
        if self.ready is False:
            return
        created_at = ((before.id >> 22) + 1420070400000) / 1000
        if (time.time() - created_at) > 7:
            return
        if before.content == after.content:
            return
        await self.process_commands(after)

    # async def on_error(self, event, *args, **kwargs):
    #     print(traceback.format_exc())
    #     print(args)
    #     ctx = await self.get_context(args[0])
    #     destination = f"\n\tLocation: {str(ctx.author)} in #{ctx.channel} [{ctx.channel.id}] ({ctx.guild}) [{ctx.guild.id}]:\n"
    #     message = f"\tContent: {args[0].clean_content}\n"
    #     tb = traceback.format_exc().split("\n")
    #     location = "./" + "/".join(tb[3].split("/")[-4:])
    #     error = f'\tFile: "{location + tb[4]}:\n\tException: {sys.exc_info()[0].__name__}: {sys.exc_info()[1]}\n'
    #     content = destination + message + error + "\n"
    #     await ctx.log("e", content)

    async def get_context(self, message, *, cls=None):
        """Override get_context to use a custom Context"""
        context = await super().get_context(message, cls=cx.BotContext)
        return context

    def get_guild_prefixes(self, guild, *, local_inject=get_prefixes):
        proxy_msg = discord.Object(id=0)
        proxy_msg.guild = guild
        return local_inject(self, proxy_msg)

    def get_raw_guild_prefixes(self, guild_id):
        return self.prefixes.get(guild_id, [self.constants.prefix])

    async def set_guild_prefixes(self, guild, prefixes):
        if len(prefixes) == 0:
            await self.put(guild.id, [None])
            self.prefixes[guild.id] = prefixes
        elif len(prefixes) > 10:
            raise RuntimeError("Cannot have more than 10 custom prefixes.")
        else:
            await self.put(guild.id, prefixes)
            self.prefixes[guild.id] = prefixes

    async def put(self, guild_id, prefixes):
        query = """
                DELETE FROM prefixes
                WHERE server_id = $1
                """
        await self.cxn.execute(query, guild_id)
        query = """
                INSERT INTO prefixes
                VALUES ($1, $2)
                """
        await self.cxn.executemany(query, ((guild_id, prefix) for prefix in prefixes))
        self.prefixes[guild_id] = prefixes

    async def get_or_fetch_member(self, guild, member_id):
        """Looks up a member in cache or fetches if not found.
        Parameters
        -----------
        guild: Guild
            The guild to look in.
        member_id: int
            The member ID to search for.
        Returns
        ---------
        Optional[Member]
            The member or None if not found.
        """

        member = guild.get_member(member_id)
        if member is not None:
            return member

        shard = self.get_shard(guild.shard_id)
        if shard.is_ws_ratelimited():
            try:
                member = await guild.fetch_member(member_id)
            except discord.HTTPException:
                return None
            else:
                return member

        members = await guild.query_members(limit=1, user_ids=[member_id], cache=True)
        if not members:
            return None
        return members[0]

    @property
    def hecate(self):
        return self.get_user(self.owner_ids[0])

    @property
    def home(self):
        home = self.get_guild(self.constants.home)
        return home

    @property
    def bot_channel(self):
        return self.get_channel(self.constants.botlog)


bot = Snowbot()
