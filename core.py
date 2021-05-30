import io
import traceback
import aiohttp
import discord
import collections
import json
import logging
import os
import re
import sys
import time

from colr import color
from datetime import datetime
from discord.ext import commands, tasks
from discord_slash.client import SlashCommand
from logging.handlers import RotatingFileHandler

from dislash.slash_commands import SlashClient
from dislash.interactions import ActionRow, ButtonStyle, Button

from settings import cleanup, database, constants
from utilities import utils, override

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
        self.batch_inserts = int()  # Counter for number of inserts.
        self.command_stats = collections.Counter()
        self.constants = constants
        self.cxn = database.postgres
        self.exts = [
            x[:-3] for x in sorted(os.listdir("././cogs")) if x.endswith(".py")
        ]
        self.dregex = re.compile(
            r"(?:https?://)?discord(?:app)?\.(?:com/invite|gg)/[a-zA-Z0-9]+/?"
        )  # discord invite regex
        self.emote_dict = constants.emotes
        self.prefixes = database.prefixes
        #self.command_config = database.command_config
        self.ready = False
        self.session = aiohttp.ClientSession(loop=self.loop)
        self.slash = SlashCommand(self, sync_commands=True)
        self.socket_events = collections.Counter()

        self.cog_exceptions = ["BOTCONFIG", "BOTADMIN", "MANAGER", "JISHAKU"]
        self.hidden_cogs = ["TESTING", "BATCH", "SLASH", "TASKS"]
        self.do_not_load = ["CONVERSION", "TESTING"]

        # Webhooks for monitering and data saving.
        self.avatar_webhook = None
        self.error_webhook = None
        self.icon_webhook = None
        self.logging_webhook = None
        self.testing_webhook = None

    @property
    def hecate(self):
        return self.get_user(self.owner_ids[0])

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
            and x.cog.qualified_name.upper not in self.hidden_cogs + self.cog_exceptions
        ]
        category_list = [
            x.qualified_name.capitalize()
            for x in [self.get_cog(cog) for cog in self.cogs]
            if x.qualified_name.upper() not in self.hidden_cogs + self.cog_exceptions
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

        try:  # Set up our webhooks
            await self.setup_webhooks()
        except Exception as e:
            print(f"Unable to setup webhooks: {e}")
            pass

        # The rest of the botvars that couldn't be set earlier
        await self.load_globals()

    async def setup_webhooks(self):
        self.avatar_webhook = await self.fetch_webhook(utils.config()["avatars"][1])
        self.error_webhook = await self.fetch_webhook(utils.config()["errors"][1])
        self.icon_webhook = await self.fetch_webhook(utils.config()["icons"][1])
        self.logging_webhook = await self.fetch_webhook(utils.config()["logging"][1])
        self.testing_webhook = await self.fetch_webhook(utils.config()["testing"][1])

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
            self.invites = {
                guild.id: await guild.invites()
                for guild in self.guilds
                if guild.me.guild_permissions.manage_guild
            }

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
        await cleanup.basic_cleanup(self.guilds)

        # Establish our webhooks
        await self.setup_webhooks()

        # load all initial extensions
        try:
            for cog in self.exts:
                if cog.upper() not in self.do_not_load:
                    self.load_extension(f"cogs.{cog}")
        except Exception as e:
            self.dispatch("error", "extension_error", tb=utils.traceback_maker(e))

        print(f"{self.user} ({self.user.id})")
        try:
            await self.logging_webhook.send(
                f"{self.emote_dict['success']} **Information** `{datetime.utcnow()}`\n"
                f"```prolog\nReady: {self.user} [{self.user.id}]```",
                username=f"{self.user.name} Logger",
                avatar_url=self.constants.avatars["green"],
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

    async def on_ready(self):
        # from discord_slash import utils
        # await utils.manage_commands.remove_all_commands_in(bot.user.id, bot.token, 740734113086177433)
        pass

    async def on_error(self, event, *args, **kwargs):
        """
        All event errors and dispatched errors
        will be logged via the error webhook.
        """
        title = f"**{self.emote_dict['failed']} Error `{datetime.utcnow()}`**"
        description = f"```prolog\n{event.upper()}:\n{kwargs.get('tb') or traceback.format_exc()}\n```"
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
            await self.error_webhook.send(
                title + description,
                file=dfile,
                username=f"{self.user.name} Monitor",
                avatar_url=self.constants.avatars["red"],
            )
            if arguments:
                await self.error_webhook.send(
                    arguments,
                    username=f"{self.user.name} Monitor",
                    avatar_url=self.constants.avatars["red"],
                )
        except Exception:
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
            if ctx.cog._get_overridden_method(ctx.cog.cog_command_error):
                return

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
            err = utils.traceback_maker(error.original, advance=True)
            self.dispatch("error", "command_error", vars(ctx), tb=err)
            if "or fewer" in str(error):  # Message was too long to send
                return await ctx.fail(f"Result was greater than the character limit.")
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
            self.dispatch("error", "command_error", vars(ctx), tb=err)
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
        if self.ready is False:
            return

        await database.update_server(guild, guild.members)
        await database.fix_server(guild.id)
        if guild.me.guild_permissions.manage_guild:
            self.invites[guild.id] = await guild.invites()
        try:
            await self.logging_webhook.send(
                f"{self.emote_dict['success']} **Information** `{datetime.utcnow()}`\n"
                f"```prolog\nServer join: {guild.name} [{guild.id}]```",
                username=f"{self.user.name} Logger",
                avatar_url=self.constants.avatars["green"],
            )
        except Exception:
            pass

    async def on_guild_remove(self, guild):
        if self.ready is False:
            return  # Wait until ready
        # This happens when the bot gets kicked from a server.
        # No need to waste any space storing their info anymore.
        await cleanup.destroy_server(guild.id)
        try:
            await self.logging_webhook.send(
                f"{self.emote_dict['success']} **Information** `{datetime.utcnow()}`\n"
                f"```prolog\nServer remove: {guild.name} [{guild.id}]```",
                username=f"{self.user.name} Logger",
                avatar_url=self.constants.avatars["green"],
            )
        except Exception:
            pass

    async def on_message(self, message):
        await self.process_commands(message)
        if not isinstance(message.channel, discord.DMChannel):
            return  # Only check for invite links in DMs
        if message.author.id == self.user.id:
            return  # Don't reply to ourselves
        if self.dregex.match(message.content):  # When a user DMs the bot an invite...
            button_row = ActionRow(Button(
                style=ButtonStyle.link,
                label="Click me!",
                url=self.bot.oauth
            ))
            await message.reply(f"Click the button below to invite me to your server.", components=[button_row])

    async def on_message_edit(self, before, after):
        if not self.ready:
            return  # Wait until bot is ready
        if before.content == after.content:
            return  # Only process new content not embeds & links.
        if not after.edited_at or not after.created_at:
            return  # Need these timestamps to check time since msg.
        if (after.edited_at - after.created_at).total_seconds() > 10:
            return  # We do not allow edit command invokations after 10s.
        await self.process_commands(after)


bot = Snowbot()
SlashClient(bot)