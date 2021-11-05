import re
import json
import time
import asyncio
import discord
import logging

from collections import Counter, defaultdict
from datetime import datetime
from discord.ext import commands, tasks

from utilities import utils
from utilities import decorators

command_logger = logging.getLogger("COMMAND_LOGGER")

EMOJI_REGEX = re.compile(r"<a?:.+?:([0-9]{15,21})>")
EMOJI_NAME_REGEX = re.compile(r"[0-9a-zA-Z\_]{2,32}")


def setup(bot):
    bot.add_cog(Batch(bot))


class Batch(commands.Cog):
    """
    Batch inserts all data
    """

    def __init__(self, bot):
        self.bot = bot

        self.whitelist = []  # Users that opted out
        bot.loop.create_task(self.load_whitelist())

        # Removed for now at least
        # self.activity_batch = defaultdict(dict)

        # Data holders
        self.command_batch = []
        self.emote_batch = defaultdict(dict)
        self.invite_batch = []
        self.message_batch = []
        self.nicknames_batch = []
        self.presence_batch = []
        self.roles_batch = defaultdict(dict)
        self.status_batch = defaultdict(dict)
        self.tracking_batch = defaultdict(dict)
        self.usernames_batch = []
        self.voice_batch = []

        self.batch_lock = asyncio.Lock(loop=bot.loop)
        self.queue = asyncio.Queue(loop=bot.loop)

        self.bulk_inserter.start()
        self.invite_tracker.start()
        self.message_inserter.start()
        self.status_inserter.start()

    def cog_unload(self):
        self.bulk_inserter.stop()
        self.message_inserter.stop()
        self.status_inserter.stop()
        self.invite_tracker.stop()

    async def load_whitelist(self):
        query = "SELECT ARRAY(SELECT user_id FROM whitelist);"
        self.whitelist = await self.bot.cxn.fetchval(query)

    async def opt_in(self, user_id):
        self.whitelist.remove(user_id)
        query = "DELETE FROM whitelist WHERE user_id = $1"
        await self.bot.cxn.execute(query, user_id)


    async def opt_out(self, user_id):
        query = "INSERT INTO whitelist VALUES ($1);"
        await self.bot.cxn.execute(query, user_id)
        self.whitelist.append(user_id)
        await self.delete_all(user_id)

    async def delete_all(self, user_id):
        queries = [
            """
            WITH data AS (
                DELETE FROM useravatars
                WHERE user_id = $1
                RETURNING avatar
            )
            DELETE FROM avatars
            WHERE hash IN (
                SELECT avatar
                FROM data
            );
            """,
            """
            DELETE FROM usernames
            WHERE user_id = $1; 
            """,
            """
            DELETE FROM usernicks
            WHERE user_id = $1;
            """,
            """
            DELETE FROM userstatus
            WHERE user_id = $1;
            """,
            """
            DELETE FROM tracker
            WHERE user_id = $1;
            """,
            """
            DELETE FROM voice
            WHERE user_id = $1;
            """,
            """
            DELETE FROM statuses
            WHERE user_id = $1;
            """,
            """
            DELETE FROM emojidata
            WHERE author_id = $1;
            """,
            """
            DELETE FROM messages
            WHERE author_id = $1;
            """,

        ]
        async with self.bot.cxn.acquire() as conn:      
            async with conn.transaction():
                for query in queries:
                    await conn.execute(query, user_id)

    @tasks.loop(minutes=1.0)
    async def invite_tracker(self):
        self.bot.invites = {
            guild.id: await guild.invites()
            for guild in self.bot.guilds
            if guild.me.guild_permissions.manage_guild
        }

    @tasks.loop(seconds=0.5)
    async def status_inserter(self):
        if self.status_batch:  # Insert all status changes
            async with self.batch_lock:
                if self.status_batch["online"]:
                    query = """
                            INSERT INTO userstatus (user_id)
                            SELECT x.user_id
                            FROM JSONB_TO_RECORDSET($1::JSONB)
                            AS x(user_id BIGINT, last_changed DOUBLE PRECISION)
                            ON CONFLICT (user_id)
                            DO UPDATE SET last_changed = EXCLUDED.last_changed,
                            online = userstatus.online + (EXCLUDED.last_changed - userstatus.last_changed);
                            """
                    data = json.dumps(
                        [
                            {"user_id": user_id, "last_changed": timestamp}
                            for user_id, timestamp in self.status_batch[
                                "online"
                            ].items()
                        ]
                    )
                    await self.bot.cxn.execute(query, data)
                    self.status_batch["online"].clear()
                if self.status_batch["idle"]:
                    query = """
                            INSERT INTO userstatus (user_id)
                            SELECT x.user_id
                            FROM JSONB_TO_RECORDSET($1::JSONB)
                            AS x(user_id BIGINT, last_changed DOUBLE PRECISION)
                            ON CONFLICT (user_id)
                            DO UPDATE SET last_changed = EXCLUDED.last_changed,
                            idle = userstatus.idle + (EXCLUDED.last_changed - userstatus.last_changed);
                            """
                    data = json.dumps(
                        [
                            {"user_id": user_id, "last_changed": timestamp}
                            for user_id, timestamp in self.status_batch["idle"].items()
                        ]
                    )
                    await self.bot.cxn.execute(query, data)
                    self.status_batch["idle"].clear()
                if self.status_batch["dnd"]:
                    query = """
                            INSERT INTO userstatus (user_id)
                            SELECT x.user_id
                            FROM JSONB_TO_RECORDSET($1::JSONB)
                            AS x(user_id BIGINT, last_changed DOUBLE PRECISION)
                            ON CONFLICT (user_id)
                            DO UPDATE SET last_changed = EXCLUDED.last_changed,
                            dnd = userstatus.dnd + (EXCLUDED.last_changed - userstatus.last_changed)
                            """
                    data = json.dumps(
                        [
                            {"user_id": user_id, "last_changed": timestamp}
                            for user_id, timestamp in self.status_batch["dnd"].items()
                        ]
                    )
                    await self.bot.cxn.execute(query, data)
                    self.status_batch["dnd"].clear()
                if self.status_batch["offline"]:
                    query = """
                            INSERT INTO userstatus (user_id)
                            SELECT x.user_id
                            FROM JSONB_TO_RECORDSET($1::JSONB)
                            AS x(user_id BIGINT, last_changed DOUBLE PRECISION)
                            ON CONFLICT (user_id)
                            DO UPDATE SET last_changed = EXCLUDED.last_changed;
                            """
                    data = json.dumps(
                        [
                            {"user_id": user_id, "last_changed": timestamp}
                            for user_id, timestamp in self.status_batch[
                                "offline"
                            ].items()
                        ]
                    )
                    await self.bot.cxn.execute(query, data)
                    self.status_batch["offline"].clear()

    @status_inserter.error
    async def loop_error(self, exc):
        self.bot.dispatch("error", "loop_error", tb=utils.traceback_maker(exc))

    @tasks.loop(seconds=0.5)
    async def message_inserter(self):
        """
        Main bulk message inserter
        """

        if self.message_batch:  # Insert every message into the db
            query = """
                    INSERT INTO messages (unix, timestamp,
                    message_id, author_id, channel_id, server_id)
                    SELECT x.unix, x.timestamp,
                    x.message_id, x.author_id, x.channel_id, x.server_id
                    FROM JSONB_TO_RECORDSET($1::JSONB)
                    AS x(unix REAL, timestamp TIMESTAMP,
                    message_id BIGINT, author_id BIGINT,
                    channel_id BIGINT, server_id BIGINT)
                    """
            async with self.batch_lock:
                data = json.dumps(self.message_batch)
                await self.bot.cxn.execute(query, data)
                self.message_batch.clear()

    @message_inserter.error
    async def loop_error(self, exc):
        self.bot.dispatch("error", "loop_error", tb=utils.traceback_maker(exc))

    @tasks.loop(seconds=2.0)
    async def bulk_inserter(self):
        # if self.activity_batch:
        #     query = """
        #                 INSERT INTO activities (user_id, activity, insertion)
        #                 SELECT x.user_id, x.activity, x.insertion
        #                 FROM JSONB_TO_RECORDSET($1::JSONB)
        #                 AS x(user_id BIGINT, activity TEXT, insertion TIMESTAMP)
        #                 """

        #     data = json.dumps(
        #         [
        #             {
        #                 "user_id": user_id,
        #                 "activity": activity,
        #                 "insertion": str(timestamp),
        #             }
        #             for user_id, data in self.activity_batch.items()
        #             for activity, timestamp in data.items()
        #         ]
        #     )
        #     await self.bot.cxn.execute(query, data)
        #     self.activity_batch.clear()

        if self.command_batch:  # Insert all the commands executed.
            query = """
                    INSERT INTO commands (server_id, channel_id,
                    author_id, timestamp, prefix, command, failed)
                    SELECT x.server, x.channel, x.author,
                    x.timestamp, x.prefix, x.command, x.failed
                    FROM JSONB_TO_RECORDSET($1::JSONB)
                    AS x(server BIGINT, channel BIGINT,
                    author BIGINT, timestamp TIMESTAMP,
                    prefix TEXT, command TEXT, failed BOOLEAN);
                    """
            async with self.batch_lock:
                data = json.dumps(self.command_batch)
                await self.bot.cxn.execute(query, data)

                # Command logger to ./data/logs/commands.log
                destination = None
                for x in self.command_batch:
                    if x["server"] is None:
                        destination = "Private Message"
                    else:
                        destination = f"#{self.bot.get_channel(x['channel'])} [{x['channel']}] ({self.bot.get_guild(x['server'])}) [{x['server']}]"
                    command_logger.info(
                        f"{self.bot.get_user(x['author'])} in {destination}: {x['content']}"
                    )
                self.command_batch.clear()

        # Emoji usage tracking
        if self.emote_batch:
            query = """
                    INSERT INTO emojidata (server_id, author_id, emoji_id, total)
                    SELECT x.server_id, x.author_id, x.emoji_id, x.added
                    FROM JSONB_TO_RECORDSET($1::JSONB)
                    AS x(server_id BIGINT, author_id BIGINT, emoji_id BIGINT, added INT)
                    ON CONFLICT (server_id, author_id, emoji_id) DO UPDATE
                    SET total = emojidata.total + EXCLUDED.total;
                    """
            async with self.batch_lock:
                data = json.dumps(
                    [
                        {
                            "server_id": server_id,
                            "author_id": author_id,
                            "emoji_id": emoji_id,
                            "added": count,
                        }
                        for server_id, data in self.emote_batch.items()
                        for author_id, stats in data.items()
                        for emoji_id, count in stats.items()
                    ]
                )
                await self.bot.cxn.execute(query, data)
                self.emote_batch.clear()

        if self.tracking_batch:  # Track user last seen times
            query = """
                    INSERT INTO tracker (user_id, unix, action)
                    VALUES ($1, $2, $3)
                    ON CONFLICT (user_id)
                    DO UPDATE SET unix = $2, action = $3
                    WHERE tracker.user_id = $1;
                    """
            async with self.batch_lock:
                await self.bot.cxn.executemany(
                    query,
                    (
                        (user_id, timestamp, description)
                        for user_id, data in self.tracking_batch.items()
                        for timestamp, description in data.items()
                    ),
                )
                self.tracking_batch.clear()

        if self.usernames_batch:  # Save usernames
            query = """
                    INSERT INTO usernames (user_id, username)
                    SELECT x.user_id, x.name
                    FROM JSONB_TO_RECORDSET($1::JSONB)
                    AS x(user_id BIGINT, name TEXT)
                    """
            async with self.batch_lock:
                data = json.dumps(self.usernames_batch)
                await self.bot.cxn.execute(query, data)
                self.usernames_batch.clear()

        if self.nicknames_batch:  # Save user nicknames
            query = """
                    INSERT INTO usernicks (user_id, server_id, nickname)
                    SELECT x.user_id, x.server_id, x.nickname
                    FROM JSONB_TO_RECORDSET($1::JSONB)
                    AS x(user_id BIGINT, server_id BIGINT, nickname TEXT)
                    """
            async with self.batch_lock:
                data = json.dumps(self.nicknames_batch)
                await self.bot.cxn.execute(query, data)
                self.nicknames_batch.clear()

        if self.roles_batch:  # Insert roles to reassign later.
            query = """
                    INSERT INTO userroles (user_id, server_id, roles)
                    SELECT x.user_id, x.server_id, x.roles
                    FROM JSONB_TO_RECORDSET($1::JSONB)
                    AS x(user_id BIGINT, server_id BIGINT, roles TEXT)
                    ON CONFLICT (user_id, server_id)
                    DO UPDATE SET roles = EXCLUDED.roles
                    """
            async with self.batch_lock:
                data = json.dumps(
                    [
                        {"server_id": server_id, "user_id": user_id, "roles": roles}
                        for server_id, data in self.roles_batch.items()
                        for user_id, roles in data.items()
                    ]
                )
                await self.bot.cxn.execute(query, data)
                self.roles_batch.clear()

        if self.invite_batch:  # Insert invite data for basic tracking
            query = """
                    INSERT INTO invites (invitee, inviter, server_id)
                    SELECT x.invitee, x.inviter, x.server_id
                    FROM JSONB_TO_RECORDSET($1::JSONB)
                    AS x(invitee BIGINT, inviter BIGINT, server_id BIGINT)
                    """
            async with self.batch_lock:
                data = json.dumps(self.invite_batch)
                await self.bot.cxn.execute(query, data)
                self.invite_batch.clear()

        if self.voice_batch:
            async with self.batch_lock:
                query = """
                        INSERT INTO voice (server_id, user_id, connected, first_seen)
                        SELECT x.server_id, x.user_id, x.connected, x.first_seen
                        FROM JSONB_TO_RECORDSET($1::JSONB)
                        AS x(server_id BIGINT, user_id BIGINT, connected BOOLEAN, first_seen TIMESTAMP);
                        """
                data = json.dumps(self.voice_batch)
                await self.bot.cxn.execute(query, data)
                self.voice_batch.clear()

        if self.presence_batch:
            async with self.batch_lock:
                query = """
                        INSERT INTO statuses (user_id, status, first_seen)
                        SELECT x.user_id, x.status, x.first_seen
                        FROM JSONB_TO_RECORDSET($1::JSONB)
                        AS x(user_id BIGINT, status TEXT, first_seen TIMESTAMP);
                        """
                data = json.dumps(self.presence_batch)
                await self.bot.cxn.execute(query, data)
                self.presence_batch.clear()

    @bulk_inserter.error
    async def loop_error(self, exc):
        self.bot.dispatch("error", "loop_error", tb=utils.traceback_maker(exc))

    @commands.Cog.listener()
    @decorators.wait_until_ready()
    async def on_command(self, ctx):
        command = ctx.command.qualified_name
        self.bot.command_stats[command] += 1
        if ctx.guild:
            server_id = ctx.guild.id
        else:
            server_id = None
        async with self.batch_lock:
            self.command_batch.append(
                {
                    "server": server_id,
                    "channel": ctx.channel.id,
                    "author": ctx.author.id,
                    "timestamp": str(ctx.message.created_at.utcnow()),
                    "prefix": ctx.prefix,
                    "command": ctx.command.name,
                    "failed": ctx.command_failed,
                    "content": ctx.message.clean_content.replace("\u0000", ""),
                }
            )

    # Helper functions to detect changes
    @staticmethod
    def status_changed(before, after):
        if before.status != after.status:
            return True

    @staticmethod
    def activity_changed(before, after):
        if not before.activity:
            return
        if str(after.status) == "offline":
            return
        if str(before.activity) == str(after.activity):
            return
        if before.activity.type is not discord.ActivityType.custom:
            return

        return True

    @staticmethod
    def avatar_changed(before, after):
        if before.avatar != after.avatar:
            return True

    @staticmethod
    def icon_changed(before, after):
        if before.icon != after.icon:
            return True

    @staticmethod
    def username_changed(before, after):
        if before.discriminator != after.discriminator:
            return True
        if before.name != after.name:
            return True

    @staticmethod
    def nickname_changed(before, after):
        if before.display_name != after.display_name:
            return True

    @staticmethod
    def roles_changed(before, after):
        if before.roles != after.roles:
            return True

    @commands.Cog.listener()
    @decorators.wait_until_ready()
    @decorators.event_check(lambda s, b, a: not a.bot)
    async def on_member_update(self, before, after):
        if after.id in self.whitelist:
            return

        if self.nickname_changed(before, after):
            async with self.batch_lock:
                self.nicknames_batch.append(
                    {
                        "user_id": after.id,
                        "server_id": after.guild.id,
                        "nickname": before.display_name.replace("\u0000", ""),
                    }
                )

    @commands.Cog.listener()
    @decorators.wait_until_ready()
    @decorators.event_check(lambda s, b, a: a.guild is not None and a.bot is False)
    async def on_presence_update(self, before, after):
        if after.id in self.whitelist:
            return

        if self.status_changed(before, after):
            async with self.batch_lock:
                self.status_batch[str(before.status)][after.id] = time.time()

                lowest = discord.utils.find(lambda x: x.get_member(after.id) is not None, sorted(self.bot.guilds, key=lambda x: x.id))
                if after.guild.id == lowest.id:
                    self.presence_batch.append(
                        {
                            "user_id": after.id,
                            "status": after.status.name,
                            "first_seen": str(datetime.utcnow())
                        }
                    )
                status_txt = (
                    f"updating their status: `{before.status}` ➔ `{after.status}`"
                )
                self.tracking_batch[before.id] = {time.time(): status_txt}

        if self.activity_changed(before, after):
            action = "updating their custom status"
            async with self.batch_lock:
                self.tracking_batch[before.id] = {time.time(): action}

                # self.activity_batch[before.id].update(
                #     {str(before.activity): datetime.utcnow()}
                # )

    @commands.Cog.listener()
    @decorators.wait_until_ready()
    @decorators.event_check(lambda s, b, a: not a.bot)
    async def on_user_update(self, before, after):
        """
        Here's where we get notified of avatar,
        username, and discriminator changes.
        """
        if after.id in self.whitelist:
            return
        if self.avatar_changed(before, after):
            async with self.batch_lock:
                self.tracking_batch[before.id] = {time.time(): "updating their avatar"}
                self.bot.avatar_saver.save(after)

        if self.username_changed(before, after):
            async with self.batch_lock:
                self.usernames_batch.append(
                    {
                        "user_id": before.id,
                        "name": str(before).replace("\u0000", ""),
                    }
                )
                self.tracking_batch[before.id] = {
                    time.time(): f"updating their username: `{before}` ➔ `{after}`"
                }

    @commands.Cog.listener()
    @decorators.wait_until_ready()
    @decorators.event_check(lambda s, b, a: a.icon is not None)
    async def on_guild_update(self, before, after):
        """
        Here's where we get notified of guild updates.
        """
        if self.icon_changed(before, after):
            self.bot.icon_saver.save(after)

    @commands.Cog.listener()
    @decorators.wait_until_ready()
    @decorators.event_check(lambda s, g: g.icon is not None)
    async def on_guild_join(self, guild):
        """
        Here's where we get notified of guild updates.
        """
        self.bot.icon_saver.save(guild)

    @commands.Cog.listener()
    @decorators.wait_until_ready()
    @decorators.event_check(lambda s, m: m.guild and not m.author.bot)
    async def on_message(self, message):
        if message.author.id in self.whitelist:
            return

        self.bot.message_stats[message.guild.id] += 1
        async with self.batch_lock:
            self.message_batch.append(
                {
                    "unix": message.created_at.timestamp(),
                    "timestamp": str(message.created_at.utcnow()),
                    "message_id": message.id,
                    "author_id": message.author.id,
                    "channel_id": message.channel.id,
                    "server_id": message.guild.id,
                }
            )
            self.tracking_batch[message.author.id] = {time.time(): "sending a message"}

        matches = EMOJI_REGEX.findall(message.content)
        if matches:
            async with self.batch_lock:
                counter = Counter(map(int, matches))
                self.emote_batch[message.guild.id].update({message.author.id: counter})

                # self.emoji_batch[message.guild.id].update(map(int, matches))

    @commands.Cog.listener()
    @decorators.wait_until_ready()
    @decorators.event_check(lambda s, c, u, w: not u.bot)
    async def on_typing(self, channel, user, when):
        if user.id in self.whitelist:
            return
        async with self.batch_lock:
            self.tracking_batch[user.id] = {time.time(): "typing"}

    @commands.Cog.listener()
    @decorators.wait_until_ready()
    async def on_raw_message_edit(self, payload):
        channel_obj = self.bot.get_channel(payload.channel_id)
        try:
            message = await channel_obj.fetch_message(payload.message_id)
        except (RuntimeError, RuntimeWarning):
            pass
        except Exception:
            return
        if message.author.bot:
            return
        if message.author.id in self.whitelist:
            return
        async with self.batch_lock:
            self.tracking_batch[message.author.id] = {time.time(): "editing a message"}

    @commands.Cog.listener()
    @decorators.wait_until_ready()
    async def on_raw_reaction_add(self, payload):
        if payload.user_id in self.whitelist:
            return
        user = self.bot.get_user(payload.user_id)
        if not user:
            return
        if user.bot:
            return
        async with self.batch_lock:
            self.tracking_batch[payload.user_id] = {
                time.time(): "reacting to a message"
            }

    @commands.Cog.listener()
    @decorators.wait_until_ready()
    @decorators.event_check(lambda s, m, b, a: not m.bot and m.guild)
    async def on_voice_state_update(self, member, before, after):
        if member.id in self.whitelist:
            return

        async with self.batch_lock:
            self.tracking_batch[member.id] = {time.time(): "changing their voice state"}

        if before.channel and not after.channel:
            # User left a voice channel.
            async with self.batch_lock:
                self.voice_batch.append(
                    {
                        "server_id": member.guild.id,
                        "user_id": member.id,
                        "connected": False,
                        "first_seen": str(datetime.utcnow()),
                    }
                )
        if not before.channel and after.channel:
            # User joined a voice channel.
            async with self.batch_lock:
                self.voice_batch.append(
                    {
                        "server_id": member.guild.id,
                        "user_id": member.id,
                        "connected": True,
                        "first_seen": str(datetime.utcnow()),
                    }
                )

    @commands.Cog.listener()
    @decorators.wait_until_ready()
    @decorators.event_check(lambda s, i: i.inviter and not i.inviter.bot)
    async def on_invite_create(self, invite):
        if invite.inviter.id in self.whitelist:
            return

        async with self.batch_lock:
            self.tracking_batch[invite.inviter.id] = {time.time(): "creating an invite"}
        if not invite.guild.me.guild_permissions.manage_guild:
            return
        self.bot.invites[invite.guild.id] = await invite.guild.invites()

    @commands.Cog.listener()
    @decorators.wait_until_ready()
    async def on_invite_delete(self, invite):
        if not invite.guild.me.guild_permissions.manage_guild:
            return
        self.bot.invites[invite.guild.id] = await invite.guild.invites()

    @commands.Cog.listener()
    @decorators.wait_until_ready()
    @decorators.event_check(lambda s, m: not m.bot)
    async def on_member_join(self, member):
        if member.id in self.whitelist:
            return

        async with self.batch_lock:
            self.tracking_batch[member.id] = {time.time(): "joining a server"}

        await asyncio.sleep(2)  # API rest.

        try:
            if not member.guild.me.guild_permissions.manage_guild:
                return
        except AttributeError:  # Sometimes if we're getting kicked as they join...
            return
        async with self.batch_lock:
            old_invites = self.bot.invites[member.guild.id]
            new_invites = await member.guild.invites()
            for invite in old_invites:
                if not self.get_invite(new_invites, invite.code):
                    continue
                if invite.uses < self.get_invite(new_invites, invite.code).uses:
                    self.invite_batch.append(
                        {
                            "invitee": member.id,
                            "inviter": invite.inviter.id,
                            "server_id": member.guild.id,
                        }
                    )
            self.bot.invites[member.guild.id] = new_invites

    def get_invite(self, invite_list, code):
        for invite in invite_list:
            if invite.code == code:
                return invite

    @commands.Cog.listener()
    @decorators.wait_until_ready()
    @decorators.event_check(lambda s, m: not m.bot)
    async def on_member_remove(self, member):
        async with self.batch_lock:

            roles = ",".join([str(x.id) for x in member.roles if x.name != "@everyone"])
            self.roles_batch[member.guild.id].update({member.id: roles})

            if member.id in self.whitelist:
                return
            self.tracking_batch[member.id] = {time.time(): "leaving a server"}

        if not member.guild.me.guild_permissions.manage_guild:
            return
        self.bot.invites[member.guild.id] = await member.guild.invites()

    '''
    @commands.Cog.listener()
    @decorators.wait_until_ready()
    async def on_loaded_extension(self, name):
        query = """
                UPDATE config
                SET load_count = reload_count + 1
                WHERE client_id = $1;
                """
        await self.bot.cxn.execute(query, self.bot.user.id)

    @commands.Cog.listener()
    @decorators.wait_until_ready()
    async def on_unloaded_extension(self, name):
        query = """
                UPDATE config
                SET unload_count = reload_count + 1
                WHERE client_id = $1;
                """
        await self.bot.cxn.execute(query, self.bot.user.id)

    @commands.Cog.listener()
    @decorators.wait_until_ready()
    async def on_reloaded_extension(self, name):
        query = """
                UPDATE config
                SET reload_count = reload_count + 1
                WHERE client_id = $1;
                """
        await self.bot.cxn.execute(query, self.bot.user.id)
    '''

    @commands.Cog.listener()
    @decorators.wait_until_ready()
    async def on_reaction_add(self, reaction, user):
        self.bot.dispatch("picklist_reaction", reaction, user)

    @commands.Cog.listener()
    @decorators.wait_until_ready()
    async def on_reaction_remove(self, reaction, user):
        self.bot.dispatch("picklist_reaction", reaction, user)

    async def last_observed(self, member):
        """Lookup last_observed data."""
        query = """
                SELECT DISTINCT ON (unix) unix, action
                FROM tracker
                WHERE user_id = $1
                ORDER BY unix DESC;
                """
        last_seen_data = await self.bot.cxn.fetchrow(query, member.id) or None

        last_spoke = await self.get_last_spoke(member)
        server_last_spoke = await self.get_server_last_spoke(member)

        if last_seen_data:
            unix, action = last_seen_data
            last_seen = utils.time_between(int(unix), int(time.time()))
        else:
            action = None
            last_seen = None

        observed_data = {
            "action": action,
            "last_seen": last_seen,
            "last_spoke": last_spoke,
            "server_last_spoke": server_last_spoke,
        }
        return observed_data

    async def get_names(self, user):
        """
        Lookup all saved usernames
        """
        usernames = [str(user)]  # Tack on their current username
        query = """
                SELECT ARRAY(
                    SELECT username
                    FROM usernames
                    WHERE user_id = $1
                    ORDER BY insertion DESC
                ) as name_list;
                """
        results = await self.bot.cxn.fetchval(query, user.id)
        if results:
            usernames.extend(results)
        return usernames

    async def get_nicks(self, user):
        """
        Lookup all saved nicknames
        """
        if not hasattr(user, "guild"):
            return []  # Not a 'member' object
        nicknames = [user.display_name]  # Tack on their current nickname
        query = """
                SELECT ARRAY(
                    SELECT nickname
                    FROM usernicks
                    WHERE user_id = $1
                    AND server_id = $2
                    ORDER BY insertion DESC
                ) as nick_list;
                """
        results = await self.bot.cxn.fetchval(query, user.id, user.guild.id)
        if results:
            nicknames.extend(results)
        return nicknames

    async def get_last_seen(self, user, *, raw=False):
        """
        Get when a user last performed
        an action across all of discord.
        """
        query = """
                SELECT DISTINCT ON (unix) unix, action
                FROM tracker
                WHERE user_id = $1
                ORDER BY unix DESC;
                """
        data = await self.bot.cxn.fetchrow(query, user.id)
        if not data:
            return
        last_seen = utils.time_between(int(data["unix"]), int(time.time())) + " ago."
        #last_seen = utils.format_relative(int(data["unix"]))
        if raw:
            return last_seen

        if data["action"]:
            msg = f"User **{user}** `{user.id}` was last seen {data['action']} **{last_seen}**"
        else:
            msg = f"User **{user}** `{user.id}` was last seen **{last_seen}**"

        return msg

    async def get_last_spoke(self, user):
        query = """
                SELECT MAX(unix)
                FROM messages
                WHERE author_id = $1;
                """
        last_spoke = await self.bot.cxn.fetchval(query, user.id)
        if last_spoke:
            return utils.time_between(int(last_spoke), int(time.time()))

    async def get_server_last_spoke(self, user):
        if not hasattr(user, "guild"):
            return
        query = """
                SELECT MAX(unix)
                FROM messages
                WHERE author_id = $1
                AND server_id = $2;
                """
        server_spoke = await self.bot.cxn.fetchval(query, user.id, user.guild.id)
        if server_spoke:
            return utils.time_between(int(server_spoke), int(time.time()))

    async def get_message_count(self, user):
        """
        Gets the number of messages
        sent by the user across discord.
        """
        query = """
                SELECT COUNT(*)
                FROM messages
                WHERE author_id = $1
                """
        return await self.bot.cxn.fetchval(query, user.id)

    async def get_server_message_count(self, user):
        """
        Gets the number of messages
        sent by the user in a server.
        """
        if not hasattr(user, "guild"):
            return 0

        query = """
                SELECT COUNT(*)
                FROM messages
                WHERE author_id = $1
                AND server_id = $2
                """
        return await self.bot.cxn.fetchval(query, user.id, user.guild.id)

    async def get_command_count(self, user):
        """
        Gets the number of commands run
        by the user across discord.
        """
        query = """
                SELECT COUNT(*)
                FROM commands
                WHERE author_id = $1
                """
        return await self.bot.cxn.fetchval(query, user.id)

    async def get_server_command_count(self, user):
        """
        Gets the number of commands
        run by the user in a server.
        """
        if not hasattr(user, "guild"):
            return 0

        query = """
                SELECT COUNT(*)
                FROM commands
                WHERE author_id = $1
                AND server_id = $2
                """
        return await self.bot.cxn.fetchval(query, user.id, user.guild.id)

    async def get_activities(self, user):
        """
        Gets all recorded activities for a user
        """
        query = """
                SELECT ARRAY(
                    SELECT activity
                    FROM activities
                    WHERE user_id = $1
                    ORDER BY insertion DESC
                ) as activity_list
                """
        record = await self.bot.cxn.fetchval(query, user.id)

        if user.activity and user.activity.type is discord.ActivityType.custom:
            return [str(user.activity)] + record
        return record
