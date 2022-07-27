import io
import os
import re
import sys
import json
import time
import aiohttp
import asyncio
import asyncpg
import discord
import logging
import traceback
import collections

from discord.ext import commands, tasks
from logging.handlers import RotatingFileHandler

from settings import constants
from utilities import utils, saver, override, http, db

import config

discord.http._set_api_version(9)

MAX_LOGGING_BYTES = 32 * 1024 * 1024  # 32 MiB

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
command_logger = logging.getLogger("COMMAND_LOGGER")
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
    in ./config.py
    """
    user_id = bot.user.id
    base = [f"<@!{user_id}> ", f"<@{user_id}> "]
    if msg.guild is None:
        base.extend([bot.mode.DEFAULT_PREFIX] + bot.common_prefixes)
    else:
        base.extend(bot.prefixes.get(msg.guild.id, [bot.mode.DEFAULT_PREFIX]))
    return base


# Main bot class. Heart of the application
class Neutra(commands.AutoShardedBot):
    def __init__(self):
        allowed_mentions = discord.AllowedMentions(
            roles=False, everyone=False, users=True, replied_user=True
        )
        super().__init__(
            allowed_mentions=allowed_mentions,
            command_prefix=get_prefixes,
            case_insensitive=True,
            strip_after_prefix=True,
            owner_ids=config.OWNERS,
            intents=discord.Intents.all(),
        )
        self.developer_id = 708584008065351681

        # Mode setters
        self.development = False
        self.production = False
        self.tester = False

        self.config = config

        self.command_stats = collections.Counter()
        self.message_stats = collections.Counter()
        self.constants = constants
        self.exts = [
            x[:-3] for x in sorted(os.listdir("././cogs")) if x.endswith(".py")
        ]
        self.dregex = re.compile(
            r"(?:https?://)?discord(?:app)?\.(?:com/invite|gg)/[a-zA-Z0-9]+/?"
        )  # discord invite regex
        self.emote_dict = constants.emotes
        self.common_prefixes = [
            "!",
            ".",
            ">",
            "<",
            "$",
            "&",
            "%",
            "*",
            "-",
            "+",
            "=",
            ",",
            "?",
            ";",
            ":",
        ]  # Common prefixes that are valid in DMs
        self.ready = False
        self.prefixes = {}

        self.socket_events = collections.Counter()

        self.admin_cogs = [
            "BOTCONFIG",
            "BOTADMIN",
            "EMAILER",
            "MANAGER",
            "JISHAKU",
            "DATABASE",
            "MONITOR",
        ]
        self.do_not_load = []
        self.music_cogs = []
        self.tester_cogs = ["CONVERSION", "MISC", "ANIMALS", "SPOTIFY", "RTFM"]

        self.home_guilds = [
            805638877762420786,  # Support server
            776345386482270209,  # Ajabs server
            740734113086177433,  # HamFam server
            743299744301973514,  # Renatuu's old server
            880581552650723378,  # Renatuu's new server
            110373943822540800,  # Dbots.gg server
            336642139381301249,  # Discord.py server
            824510213909512192,  # mwthecool's server
        ]  # My servers that have "beta" features.

        # Webhooks for monitering and data saving.
        self.avatar_webhook = None
        self.error_webhook = None
        self.icon_webhook = None
        self.logging_webhook = None
        self.testing_webhook = None

    @property
    def hecate(self):
        return self.get_user(self.developer_id)

    async def run(self):  # Everything starts from here
        self.setup()  # Setup json files.

        if self.development:
            self.mode = config.DEVELOPMENT
        elif self.tester:
            self.mode = config.TESTER
        elif self.production:
            self.mode = config.PRODUCTION
        try:
            async with aiohttp.ClientSession() as session:
                async with self:
                    self.session = session
                    self.status_loop.start()  # Start the task loop
                    await super().start(self.mode.TOKEN, reconnect=True)  # Run the bot
        except RuntimeError:  # Ignore errors
            pass
        finally:  # Write up our json files with the stats from the session.
            try:
                self.status_loop.stop()  # Stop the loop gracefully
                print("\n" + utils.prefix_log("Killed"))
                with open("./data/json/blacklist.json", "w", encoding="utf-8") as fp:
                    json.dump(
                        self.blacklist, fp, indent=2
                    )  # New blacklisted users from the session
            except AttributeError:
                pass  # Ignore errors

    def setup(self):

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

    async def load_extension(self, name, *, package=None):
        self.dispatch("loaded_extension", name)
        return await super().load_extension(name, package=package)

    async def unload_extension(self, name, *, package=None):
        self.dispatch("unloaded_extension", name)
        return await super().unload_extension(name, package=package)

    async def reload_extension(self, name, *, package=None):
        self.dispatch("reloaded_extension", name)
        return await super().reload_extension(name, package=package)

    async def close(self):  # Shutdown the bot cleanly
        try:
            runtime = time.time() - self.starttime
            query = """
                    UPDATE config
                    SET last_run = $1,
                    runtime = runtime + $1,
                    reboot_count = reboot_count + 1
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

    async def put(self, url, *args, **kwargs):
        return await self.query(url, "put", *args, **kwargs)

    async def patch(self, url, *args, **kwargs):
        return await self.query(url, "patch", *args, **kwargs)

    def public_stats(self):
        command_list = [
            x.name
            for x in self.commands
            if not x.hidden
            # and x.cog.qualified_name.upper not in self.admin_cogs + self.music_cogs
        ]
        category_list = [
            x
            for x in [self.get_cog(cog) for cog in self.cogs]
            # if x.qualified_name.upper() not in self.admin_cogs + self.music_cogs
            if len([c for c in x.walk_commands()]) > 0
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
        print(utils.prefix_log("Initializing Cache..."))
        await self.wait_until_ready()
        print(utils.prefix_log(f"Elapsed time: {str(time.time() - st)[:10]} s"))

        await self.create_db()

        # The rest of the botvars that couldn't be set earlier
        await self.load_globals()

        if self.production:
            self.do_not_load += self.tester_cogs + self.music_cogs
            self.website_stats_updater.start()
            await self.setup_webhooks()
            print(utils.prefix_log("Established Webhooks."))

        await self.finalize_startup()

    async def create_db(self):
        if self.development:
            self.cxn = await asyncpg.create_pool(config.DEVELOPMENT.POSTGRES.uri)
        elif self.tester:
            self.cxn = await asyncpg.create_pool(config.TESTER.POSTGRES.uri)
        elif self.production:
            self.cxn = await asyncpg.create_pool(config.PRODUCTION.POSTGRES.uri)

        self.database = db.Database(self.cxn)
        self.prefixes = self.database.prefixes
        self.server_settings = self.database.settings

        member_list = [x for x in self.get_all_members()]
        try:
            await self.database.initialize(self, member_list)
            print(utils.prefix_log("Initialized Database."))
        except Exception as e:
            print(utils.traceback_maker(e))

    async def setup_webhooks(self):
        try:
            self.avatar_webhook = await self.fetch_webhook(
                config.WEBHOOKS.AVATARS.webhook_id
            )
        except Exception as e:
            print(f"Unable to set up avatar webhook: {e}")
        try:
            self.error_webhook = await self.fetch_webhook(
                config.WEBHOOKS.ERRORS.webhook_id
            )
        except Exception as e:
            print(f"Unable to set up error webhook: {e}")
        try:
            self.icon_webhook = await self.fetch_webhook(
                config.WEBHOOKS.ICONS.webhook_id
            )
        except Exception as e:
            print(f"Unable to set up icon webhook: {e}")
        try:
            self.logging_webhook = await self.fetch_webhook(
                config.WEBHOOKS.LOGGING.webhook_id
            )
        except Exception as e:
            print(f"Unable to set up logging webhook: {e}")
        try:
            self.testing_webhook = await self.fetch_webhook(
                config.WEBHOOKS.TESTING.webhook_id
            )
        except Exception as e:
            print(f"Unable to set up testing webhook: {e}")

    def genoauth(self, user_id):
        # The permissions needed to use all commands.
        perms = discord.Permissions.none()
        perms.add_reactions = True
        perms.attach_files = True
        perms.ban_members = True
        perms.embed_links = True
        perms.external_emojis = True
        perms.kick_members = True
        perms.manage_channels = True
        perms.manage_messages = True
        perms.manage_nicknames = True
        perms.manage_roles = True
        perms.manage_webhooks = True
        perms.move_members = True
        perms.read_message_history = True
        perms.read_messages = True
        perms.send_messages = True
        perms.view_audit_log = True

        url = discord.utils.oauth_url(
            client_id=user_id,
            permissions=perms,
            scopes=("bot", "applications.commands"),
        )
        return url

    async def load_globals(self):
        """
        Sets up the remaining botvars
        """
        if not hasattr(self, "oauth"):
            self.oauth = self.genoauth(self.user.id)

        if not hasattr(self, "uptime"):
            self.uptime = discord.utils.utcnow()

        if not hasattr(self, "starttime"):
            self.starttime = time.time()

        if not hasattr(self, "http_utils"):
            self.http_utils = http.Utils(self.session)

        if not hasattr(self, "invites"):

            self.invites = {
                # TODO
                # guild.id: await guild.invites()
                # for guild in self.guilds
                # if guild.me.guild_permissions.manage_guild
            }
        if not hasattr(self, "listing_sites"):
            self.listing_sites = {
                "discord.bots.gg": {
                    "name": "Discord Bots",
                    "token": config.LISTING_SITES.dbotsgg,
                    "url": f"https://discord.bots.gg/api/v1/bots/{self.user.id}/stats",
                    "data": {"guildCount": len(self.guilds)},
                    "guild_count_name": "guildCount",
                },
                "discordbots.org": {
                    "name": "Discord Bot List",
                    "token": config.LISTING_SITES.topgg,
                    "url": f"https://discordbots.org/api/bots/{self.user.id}/stats",
                    "data": {"server_count": len(self.guilds)},
                    "guild_count_name": "server_count",
                },
            }

        print(utils.prefix_log("Established Globals."))

    async def set_status(self):
        """
        This sets the bot's presence, status, and activity
        based off of the values in the db
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
        if not status_values:
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
        await self.database.basic_cleanup(self.guilds)
        await self.update_all_listing_stats()

        self.avatar_saver = saver.AvatarSaver(
            self.avatar_webhook, self.cxn, self.session, self.loop
        )  # Start saving avatars.

        self.icon_saver = saver.IconSaver(
            self.icon_webhook, self.cxn, self.session, self.loop
        )  # Start saving icons.

        # load all initial extensions
        for cog in self.exts:
            if cog.upper() not in self.do_not_load:
                try:
                    await self.load_extension(f"cogs.{cog}")
                except Exception as e:
                    self.dispatch(
                        "error", "extension_error", tb=utils.traceback_maker(e)
                    )
                    continue

        print(utils.prefix_log(f"{self.user} ({self.user.id})"))
        try:
            await self.logging_webhook.send(
                f"**Information** `{discord.utils.utcnow()}`\n"
                f"```prolog\nReady: {self.user} [{self.user.id}]```",
            )
        except Exception:
            pass

        self.ready = True

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
                    content=f"{self.emote_dict['success']} {reboot_invoker}ed Successfully."
                )
            except Exception:
                pass

    async def get_context(self, message, *, cls=None):
        """Override get_context to use a custom Context"""
        context = await super().get_context(message, cls=override.BotContext)
        return context

    def get_guild_prefixes(self, guild, *, local_inject=get_prefixes):
        proxy_msg = discord.Object(id=0)
        proxy_msg.guild = guild
        return local_inject(self, proxy_msg)

    def get_raw_guild_prefixes(self, guild_id):
        return self.prefixes.get(guild_id, [self.mode.DEFAULT_PREFIX])

    async def set_guild_prefixes(self, guild, prefixes):
        if len(prefixes) == 0:
            await self.put_prefixes(guild.id, [None])
            self.prefixes[guild.id] = prefixes
        elif len(prefixes) > 10:
            raise RuntimeError("Cannot have more than 10 custom prefixes.")
        else:
            await self.put_prefixes(guild.id, prefixes)
            self.prefixes[guild.id] = prefixes

    async def put_prefixes(self, guild_id, prefixes):
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

    def get_cogs(self):
        """
        Helper function to return a list of cogs
        """
        return [self.get_cog(cog) for cog in self.cogs]

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

    async def get_or_fetch_user(self, user_id):
        """
        Looks up a user in cache or fetches if not found.
        Parameters
        -----------
        user_id: int
        Returns
        ---------
        Optional[discord.User]
            The user or None if not found.
        """

        member = self.get_user(user_id)
        if member is not None:
            return member

        return await self.fetch_user(user_id)

    async def on_error(self, event, *args, **kwargs):
        """
        All event errors and dispatched errors
        will be logged via the error webhook.
        """
        tb = kwargs.get("tb") or traceback.format_exc()
        title = f"**Error `{discord.utils.utcnow()}`**"
        description = f"```prolog\n{event.upper()}:\n{tb}\n```"
        dfile = None
        arguments = None
        args_str = []
        if args:
            for index, arg in enumerate(args):
                args_str.append(f"[{index}]: {arg!r}")
            result = "\n".join(args_str)
            if len(result) > 1994:
                fp = io.BytesIO("\n".join(args_str).encode("utf-8"))
                dfile = discord.File(fp, "arguments.txt")
            else:
                arguments = f"```py\n{result}```"

        try:
            if dfile:
                await self.error_webhook.send(
                    title + description,
                    file=dfile,
                )
            else:
                await self.error_webhook.send(
                    title + description,
                )
                await self.error_webhook.send(
                    arguments,
                )
        except Exception:
            print(tb, file=sys.stderr)

    async def on_command_error(self, ctx, error):
        """
        Here's where we handle all command errors
        so we can give the user feedback
        """
        if ctx.handled:
            return  # Already handled locally

        # This prevents any cogs with an overwritten cog_command_error being handled here.
        if ctx.cog:
            if ctx.cog._get_overridden_method(ctx.cog.cog_command_error):
                return

        if isinstance(error, commands.UnexpectedQuoteError):
            await ctx.fail(f"Unexpected quotation mark received.")

        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.usage()

        elif isinstance(error, commands.BadUnionArgument):
            await ctx.usage()

        elif isinstance(error, commands.BadBoolArgument):
            argument = str(error).split()[0]
            await ctx.fail(f"The argument `{argument}` is not a valid boolean.")

        elif isinstance(error, commands.BadArgument):
            if 'Converting to "int" failed for parameter' in str(error):
                arg = str(error).split()[-1].strip('."')
                error = f"The `{arg}` argument must be an integer."
            await ctx.fail(str(error))

        elif isinstance(error, commands.BadUnionArgument):
            await ctx.fail(str(error))

        elif isinstance(error, commands.BotMissingPermissions):
            await ctx.fail(str(error))

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
            await ctx.fail("This command is currently unavailable.")

        elif isinstance(error, commands.CheckFailure):
            # Previous checks didn't catch this one.
            # Readable error so just send it to where the error occurred.
            # await ctx.send_or_reply(content=f"{self.emote_dict['failed']} {error}")
            pass

        elif isinstance(error, commands.CommandInvokeError):
            if "or fewer" in str(error):  # Message was too long to send
                return await ctx.fail("Result was greater than the character limit.")
            err = utils.traceback_maker(error.original, advance=True)
            # Then we don't really know what this error is. Log it.
            self.dispatch("error", "command_error", vars(ctx), tb=err)
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
            self.dispatch("error", "command_error", vars(ctx), tb=err)
            # print(color(fore="FF0000", text="Error"))
            # print(error)
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
        if self.ready is False:
            return

        await self.update_all_listing_stats()
        await self.database.update_server(guild, guild.members)
        await self.database.fix_server(guild.id)
        if guild.me.guild_permissions.manage_guild:
            self.invites[guild.id] = await guild.invites()
        try:
            await self.logging_webhook.send(
                f"**Information** `{discord.utils.utcnow()}`\n"
                f"```prolog\nServer join: {guild.name} [{guild.id}]```",
            )
        except Exception:
            pass

    async def on_guild_remove(self, guild):
        if self.ready is False:
            return  # Wait until ready
        # This happens when the bot gets kicked from a server.
        # No need to waste any space storing their info anymore.

        await self.update_all_listing_stats()
        await self.database.destroy_server(guild.id)
        try:
            await self.logging_webhook.send(
                f"**Information** `{discord.utils.utcnow()}`\n"
                f"```prolog\nServer remove: {guild.name} [{guild.id}]```",
            )
        except Exception:
            pass

    async def on_message(self, message):
        await self.process_commands(message)
        if not isinstance(message.channel, discord.DMChannel):
            return  # Only check for invite links in DMs
        if message.author.id == self.user.id:
            return  # Don't reply to ourselves

        content = message.content

        def predicate(content):  # Check for key words in the message.
            triggers = ["invite", "join"]
            return any(trigger in content.lower() for trigger in triggers)

        if self.dregex.match(content) or predicate(
            content
        ):  # Invite link or keyword trigger.
            ctx = await self.get_context(message, cls=commands.Context)
            if not ctx.command:
                invite = self.get_command("invite")
                await ctx.invoke(invite)

    async def on_message_edit(self, before, after):
        if not self.ready:
            return  # Wait until bot is ready
        if before.content == after.content:
            return  # Only process new content not embeds & links.
        if not after.edited_at or not after.created_at:
            return  # Need these timestamps to check time since msg.
        if (after.edited_at - after.created_at).total_seconds() > 10:
            return  # We do not allow edit command invocations after 10s.
        await self.process_commands(after)

    # Update stats on sites listing Discord bots
    async def update_listing_stats(self, site):
        if self.production is False:
            return

        site = self.listing_sites.get(site)
        token = site["token"]
        url = site["url"]

        headers = {"authorization": token, "content-type": "application/json"}
        site["data"][site["guild_count_name"]] = len(self.guilds)
        data = json.dumps(site["data"])

        async with self.session.post(url, headers=headers, data=data) as resp:
            if resp.status != 200:
                return await resp.text()

    # Update stats on all bot lists
    async def update_all_listing_stats(self):
        tasks = [self.update_listing_stats(site) for site in self.listing_sites]
        return await asyncio.gather(*tasks)

    @tasks.loop(seconds=1)
    async def website_stats_updater(self):
        url = config.BASE_WEB_URL + "_stats"
        headers = {"content-type": "application/json"}
        data = {
            "uptime": utils.time_between(self.starttime, int(time.time())),
            "servers": len(self.guilds),
            "channels": sum(1 for c in self.get_all_channels()),
            "members": sum(1 for m in self.get_all_members()),
            "commands": sum(self.command_stats.values()),
            "messages": sum(self.message_stats.values()),
        }
        data = json.dumps(data)

        try:
            async with self.session.post(url, headers=headers, data=data) as resp:
                if resp.status == 200:
                    self.website_stats_updater.change_interval(seconds=1)
                else:
                    info_logger.info(
                        f"Invalid responce from website. Retrying in 10 minuts. Status: {resp.status} Response: {await resp.text()}"
                    )
                    self.website_stats_updater.change_interval(minutes=5)
        except aiohttp.ClientConnectorError:  # Website is down, retry in 5 minutes
            self.website_stats_updater.change_interval(minutes=5)

    @website_stats_updater.after_loop
    async def reset_website_stats(self):
        url = config.BASE_WEB_URL + "_stats"
        headers = {"content-type": "application/json"}
        data = {
            "uptime": "Currently Offline",
            "servers": len(self.guilds),
            "channels": sum(1 for c in self.get_all_channels()),
            "members": sum(1 for m in self.get_all_members()),
            "commands": sum(self.command_stats.values()),
            "messages": sum(self.message_stats.values()),
        }
        data = json.dumps(data)

        try:
            async with self.session.post(url, headers=headers, data=data) as resp:
                if resp.status != 200:
                    info_logger.info(
                        f"Invalid responce from website. Status: {resp.status} Response: {await resp.text()}"
                    )
        except aiohttp.ClientConnectorError:  # Website is down
            pass


bot = Neutra()
