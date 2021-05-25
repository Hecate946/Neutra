import io
import re
import json
import time
import asyncio
import discord
import logging
import traceback

from collections import Counter, defaultdict
from datetime import datetime, timezone
from discord.ext import commands, tasks

from utilities import utils
from utilities import converters
from utilities import decorators

command_logger = logging.getLogger("Snowbot")

EMOJI_REGEX = re.compile(r"<a?:.+?:([0-9]{15,21})>")
EMOJI_NAME_REGEX = re.compile(r"[0-9a-zA-Z\_]{2,32}")


def setup(bot):
    bot.add_cog(Batch(bot))


class Batch(commands.Cog):
    """
    Manage batch inserts
    """

    def __init__(self, bot):
        self.bot = bot
        # Data holders
        self.avatar_batch = list()
        self.command_batch = list()
        self.emoji_batch = defaultdict(Counter)
        self.invite_batch = list()
        self.message_batch = list()
        self.nicknames_batch = list()
        self.roles_batch = list()
        self.snipe_batch = list()
        self.spammer_batch = list()
        self.status_batch = defaultdict(dict)
        self.tracker_batch = dict()
        self.usernames_batch = list()

        self.avatar_webhook = None
        self.batch_lock = asyncio.Lock(loop=bot.loop)
        self._auto_spam_count = Counter()
        self.queue = asyncio.Queue(loop=bot.loop)
        self.spam_control = commands.CooldownMapping.from_cooldown(
            10, 12, commands.BucketType.user
        )

        self.bulk_inserter.start()
        self.dispatch_avatars.start()
        self.status_inserter.start()

    def cog_unload(self):
        self.background_task.stop()
        self.bulk_inserter.stop()
        self.dispatch_avatars.stop()
        self.status_inserter.stop()

    @tasks.loop(seconds=0.0)
    async def dispatch_avatars(self):
        while True:
            files = [await self.queue.get() for _ in range(10)]
            try:
                upload_batch = await self.avatar_webhook.send(files=files, wait=True)
                for x in upload_batch.attachments:
                    self.avatar_batch.append(
                        {
                            "user_id": int(x.filename.split(".")[0]),
                            "avatar_id": x.id,
                            "unix": time.time(),
                        }
                    )
            except discord.HTTPException as e:
                # Here the combined files likely went over the 8mb file limit
                # Lets divide them up into 2 parts and send them separately.
                await self.bot.bot_channel.send(e)
                upload_batch_1 = await self.avatar_webhook.send(
                    files=files[:5], wait=True
                )
                upload_batch_2 = await self.avatar_webhook.send(
                    files=files[5:], wait=True
                )
                new_upload_batch = (
                    upload_batch_1.attachments + upload_batch_2.attachments
                )
                for x in new_upload_batch:
                    self.avatar_batch.append(
                        {
                            "user_id": int(x.filename.split(".")[0]),
                            "avatar_id": x.id,
                            "unix": time.time(),
                        }
                    )
                await self.bot.bot_channel.send(
                    f"**Payload size error successfully dealt with.**"
                )
            except Exception as e:
                await self.bot.bot_channel.send(e)

    @tasks.loop(seconds=0.2)
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

    @tasks.loop(seconds=2.0)
    async def bulk_inserter(self):
        self.bot.batch_inserts += 1
        if self.command_batch:  # Insert all the commands executed.
            query = """
                    INSERT INTO commands (
                        server_id, channel_id,
                        author_id, timestamp,
                        prefix, command, failed
                    )
                    SELECT x.server, x.channel,
                           x.author, x.timestamp,
                           x.prefix, x.command, x.failed
                    FROM JSONB_TO_RECORDSET($1::JSONB)
                    AS x(
                        server BIGINT, channel BIGINT,
                        author BIGINT, timestamp TIMESTAMP,
                        prefix TEXT, command TEXT, failed BOOLEAN
                    )
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

        if self.snipe_batch:  # Snipe command setup
            query = """
                    UPDATE messages
                    SET deleted = True
                    WHERE message_id = $1;
                    """  # Updates already stored messages.
            async with self.batch_lock:
                await self.bot.cxn.executemany(query, ((x,) for x in self.snipe_batch))
                self.snipe_batch.clear()

        # Emoji usage tracking
        if self.emoji_batch:
            query = """
                    INSERT INTO emojistats (server_id, emoji_id, total)
                    SELECT x.server_id, x.emoji_id, x.added
                    FROM JSONB_TO_RECORDSET($1::JSONB)
                    AS x(server_id BIGINT, emoji_id BIGINT, added INT)
                    ON CONFLICT (server_id, emoji_id) DO UPDATE
                    SET total = emojistats.total + excluded.total;
                    """
            async with self.batch_lock:
                data = json.dumps(
                    [
                        {"server_id": server_id, "emoji_id": emoji_id, "added": count}
                        for server_id, data in self.emoji_batch.items()
                        for emoji_id, count in data.items()
                    ]
                )
                await self.bot.cxn.execute(query, data)
                self.emoji_batch.clear()

        if self.message_batch:  # Insert every message into the db
            query = """
                    INSERT INTO messages (unix, timestamp, content,
                    message_id, author_id, channel_id, server_id)
                    SELECT x.unix, x.timestamp, x.content,
                    x.message_id, x.author_id, x.channel_id, x.server_id
                    FROM JSONB_TO_RECORDSET($1::JSONB)
                    AS x(unix REAL, timestamp TIMESTAMP, content TEXT,
                    message_id BIGINT, author_id BIGINT,
                    channel_id BIGINT, server_id BIGINT)
                    """
            async with self.batch_lock:
                data = json.dumps(self.message_batch)
                await self.bot.cxn.execute(query, data)
                self.message_batch.clear()

        if self.spammer_batch:  # Track users who spam messages
            query = """
                    INSERT INTO spammers (user_id, server_id)
                    SELECT x.user_id, x.server_id
                    FROM JSONB_TO_RECORDSET($1::JSONB)
                    as x(user_id BIGINT, server_id BIGINT)
                    ON CONFLICT (user_id, server_id)
                    DO UPDATE SET spamcount = spammers.spamcount + 1;
                    """
            async with self.batch_lock:
                data = json.dumps(self.spammer_batch)
                await self.bot.cxn.execute(query, data)
                self.spammer_batch.clear()

        if self.tracker_batch:  # Track user last seen times
            query = """
                    INSERT INTO tracker (
                        user_id,
                        unix,
                        action
                    )
                    VALUES ($1, $2, $3)
                    ON CONFLICT (user_id)
                    DO UPDATE SET unix = $2, action = $3
                    WHERE tracker.user_id = $1;
                    """
            async with self.batch_lock:
                await self.bot.cxn.executemany(
                    query,
                    (
                        (entry[0], entry[1][0], entry[1][1])
                        for entry in self.tracker_batch.items()
                    ),
                )
                self.tracker_batch.clear()

        if self.avatar_batch:  # Save user avatars
            query = """
                    INSERT INTO useravatars (user_id, avatar_id, unix)
                    SELECT x.user_id, x.avatar_id, x.unix
                    FROM JSONB_TO_RECORDSET($1::JSONB)
                    AS x(user_id BIGINT, avatar_id BIGINT, unix REAL)
                    """
            async with self.batch_lock:
                data = json.dumps(self.avatar_batch)
                await self.bot.cxn.execute(query, data)
                self.avatar_batch.clear()

        if self.usernames_batch:  # Save usernames
            query = """
                    INSERT INTO usernames (user_id, name, changed_at)
                    SELECT x.user_id, x.name, x.changed_at
                    FROM JSONB_TO_RECORDSET($1::JSONB)
                    AS x(user_id BIGINT, name TEXT, changed_at TIMESTAMP)
                    ON CONFLICT (user_id, name)
                    DO UPDATE SET changed_at = EXCLUDED.changed_at
                    """
            async with self.batch_lock:
                data = json.dumps(self.usernames_batch)
                await self.bot.cxn.execute(query, data)
                self.usernames_batch.clear()

        if self.nicknames_batch:  # Save user nicknames
            query = """
                    INSERT INTO usernicks (user_id, server_id, nickname, changed_at)
                    SELECT x.user_id, x.server_id, x.nickname, x.changed_at
                    FROM JSONB_TO_RECORDSET($1::JSONB)
                    AS x(user_id BIGINT, server_id BIGINT, nickname TEXT, changed_at TIMESTAMP)
                    ON CONFLICT (user_id, server_id, nickname)
                    DO UPDATE SET changed_at = EXCLUDED.changed_at;
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
                data = json.dumps(self.roles_batch)
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


    @bulk_inserter.before_loop
    async def get_webhook(self):
        """
        This loads our existing avatar saving webhook
        from the db or creates it if it doesn't exist.
        Stops avatar saving if no avatar channel exists.
        """
        query = """
                SELECT (
                    avatar_saver_webhook_id,
                    avatar_saver_webhook_token
                ) FROM config
                WHERE client_id = $1;
                """
        webhook_data = await self.bot.cxn.fetchval(query, self.bot.user.id)
        if not webhook_data:
            boolean = False
        if any([x is None for x in webhook_data]):
            boolean = False
        else:
            boolean = True
        if boolean:
            wh_id, wh_token = webhook_data
            try:
                webhook = await self.bot.fetch_webhook(wh_id)
                self.avatar_webhook = webhook
            except Exception:
                webhook = await self.do_webhook()
                self.avatar_webhook = webhook
        else:
            webhook = await self.do_webhook()
            self.avatar_webhook = webhook

    async def do_webhook(self):
        if not self.bot.constants.avchan:
            return
        avchan = self.bot.get_channel(self.bot.constants.avchan)
        if not avchan or not avchan.guild:
            print(f"Invalid avatar saver channel.")
            return
        bytes_avatar = await self.bot.get(
            str(self.bot.user.avatar_url), res_method="read"
        )
        try:
            webhook = await avchan.create_webhook(
                name=self.bot.user.name + " Avatar Saver",
                avatar=bytes_avatar,
                reason="Webhook created to store avatars.",
            )
        except Exception as e:
            print(e)
            return
        query = """
                UPDATE config SET
                avatar_saver_webhook_id = $1,
                avatar_saver_webhook_token = $2
                WHERE client_id = $3;
                """
        await self.bot.cxn.execute(query, webhook.id, webhook.token, self.bot.user.id)
        return webhook

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
                    "command": ctx.command.qualified_name,
                    "failed": ctx.command_failed,
                    "content": ctx.message.clean_content,
                }
            )

    @commands.Cog.listener()
    @decorators.wait_until_ready()
    async def on_raw_message_delete(self, payload):
        async with self.batch_lock:
            self.snipe_batch.append(payload.message_id)

    # Helper functions to detect changes
    @staticmethod
    async def status_changed(before, after):
        if before.status != after.status:
            return True

        try:
            if before.activity != after.activity:
                return True
        except KeyError:
            pass

    @staticmethod
    async def avatar_changed(before, after):
        if before.avatar_url != after.avatar_url:
            return True

    @staticmethod
    async def username_changed(before, after):
        if before.discriminator != after.discriminator:
            return True
        if before.name != after.name:
            return True

    @staticmethod
    async def nickname_changed(before, after):
        if before.display_name != after.display_name:
            return True

    @staticmethod
    async def roles_changed(before, after):
        if before.roles != after.roles:
            return True

    @commands.Cog.listener()
    @decorators.wait_until_ready()
    @decorators.event_check(lambda s, b, a: not a.bot)
    async def on_member_update(self, before, after):

        if before.status != after.status:
            async with self.batch_lock:
                self.status_batch[str(before.status)][after.id] = time.time()

        if await self.status_changed(before, after):
            async with self.batch_lock:
                self.tracker_batch[before.id] = (time.time(), "updating their status")

        if await self.nickname_changed(before, after):
            async with self.batch_lock:
                self.nicknames_batch.append(
                    {
                        "user_id": after.id,
                        "server_id": after.guild.id,
                        "nickname": after.display_name,
                        "changed_at": str(datetime.utcnow()),
                    }
                )

    @commands.Cog.listener()
    @decorators.wait_until_ready()
    @decorators.event_check(lambda s, b, a: not a.bot)
    async def on_user_update(self, before, after):
        """
        Here's where we get notified of avatar,
        username, and discriminator changes.
        """
        if await self.avatar_changed(before, after):
            async with self.batch_lock:
                self.tracker_batch[before.id] = (time.time(), "updating their avatar")
            if self.avatar_webhook:  # Check if we have the webhook set up.
                try:
                    avatar_url = str(after.avatar_url_as(format="png", size=1024))
                    resp = await self.bot.get((avatar_url), res_method="read")
                    data = io.BytesIO(resp)
                    dfile = discord.File(data, filename=f"{after.id}.png")
                    self.queue.put_nowait(dfile)
                except Exception as e:
                    await self.bot.bot_channel.send(f"Error in avatar_batcher: {e}")
                    await self.bot.bot_channel.send(
                        "```prolog\n" + str(traceback.format_exc()) + "```"
                    )

        if await self.username_changed(before, after):
            async with self.batch_lock:
                self.usernames_batch.append(
                    {
                        "user_id": after.id,
                        "name": str(after),
                        "changed_at": str(datetime.utcnow()),
                    }
                )
                self.tracker_batch[before.id] = (time.time(), "updating their username")

    @commands.Cog.listener()
    @decorators.wait_until_ready()
    @decorators.event_check(lambda s, m: not m.author.bot and m.guild)
    async def on_message(self, message):
        async with self.batch_lock:
            self.message_batch.append(
                {
                    "unix": message.created_at.replace(tzinfo=timezone.utc).timestamp(),
                    "timestamp": str(message.created_at.utcnow()),
                    "content": message.clean_content,
                    "message_id": message.id,
                    "author_id": message.author.id,
                    "channel_id": message.channel.id,
                    "server_id": message.guild.id,
                }
            )
            self.tracker_batch[message.author.id] = (time.time(), "sending a message")

        matches = EMOJI_REGEX.findall(message.content)
        if matches:
            async with self.batch_lock:
                self.emoji_batch[message.guild.id].update(map(int, matches))

        author = message.author
        bucket = self.spam_control.get_bucket(message)
        current = message.created_at.replace(tzinfo=timezone.utc).timestamp()
        retry_after = bucket.update_rate_limit(current)
        if retry_after:
            self._auto_spam_count[author.id] += 1
            if self._auto_spam_count[author.id] >= 5:
                async with self.batch_lock:  # Log them as spammers
                    self.spammer_batch.append(
                        {"user_id": author.id, "server_id": message.guild.id}
                    )
                del self._auto_spam_count[author.id]
            return
        else:
            self._auto_spam_count.pop(author.id, None)

    @commands.Cog.listener()
    @decorators.wait_until_ready()
    @decorators.event_check(lambda s, c, u, w: not u.bot)
    async def on_typing(self, channel, user, when):
        async with self.batch_lock:
            self.tracker_batch[user.id] = (time.time(), "typing")

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
        author_id = message.author.id
        async with self.batch_lock:
            self.tracker_batch[author_id] = (time.time(), "editing a message")

    @commands.Cog.listener()
    @decorators.wait_until_ready()
    async def on_raw_reaction_add(self, payload):

        user = self.bot.get_user(payload.user_id)
        if not user:
            return
        if user.bot:
            return
        async with self.batch_lock:
            self.tracker_batch[payload.user_id] = (time.time(), "reacting to a message")

    @commands.Cog.listener()
    @decorators.wait_until_ready()
    @decorators.event_check(lambda s, m, b, a: not m.bot)
    async def on_voice_state_update(self, member, before, after):
        async with self.batch_lock:
            self.tracker_batch[member.id] = (time.time(), "changing their voice state")

    @commands.Cog.listener()
    @decorators.wait_until_ready()
    @decorators.event_check(lambda s, i: not i.inviter.bot)
    async def on_invite_create(self, invite):
        async with self.batch_lock:
            self.tracker_batch[invite.inviter.id] = (time.time(), "creating an invite")
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
        async with self.batch_lock:
            self.tracker_batch[member.id] = (time.time(), "joining a server")

        await asyncio.sleep(2)  # API rest.

        async with self.batch_lock:
            self.usernames_batch.append(
                {
                    "user_id": member.id,
                    "name": str(member),
                    "changed_at": None,
                }
            )
            self.nicknames_batch.append(
                {
                    "user_id": member.id,
                    "server_id": member.guild.id,
                    "nickname": member.display_name,
                    "changed_at": str(datetime.utcnow()),
                }
            )
        if not member.guild.me.guild_permissions.manage_guild:
            return
        old_invites = self.bot.invites[member.guild.id]
        new_invites = await member.guild.invites()
        for invite in old_invites:
            if invite.uses < self.get_invite(new_invites, invite.code).uses:
                self.invite_batch.append({
                    "invitee": member.id,
                    "inviter": invite.inviter.id,
                    "server_id": member.guild.id
                })
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
            self.tracker_batch[member.id] = (time.time(), "leaving a server")
            roles = ",".join([str(x.id) for x in member.roles if x.name != "@everyone"])
            self.roles_batch.append(
                {
                    "user_id": member.id,
                    "server_id": member.guild.id,
                    "roles": roles,
                }
            )
        if not member.guild.me.guild_permissions.manage_guild:
            return
        self.bot.invites[member.guild.id] = await member.guild.invites()

    @commands.Cog.listener()
    @decorators.wait_until_ready()
    async def on_reaction_add(self, reaction, user):
        self.bot.dispatch("picklist_reaction", reaction, user)

    @commands.Cog.listener()
    @decorators.wait_until_ready()
    async def on_reaction_remove(self, reaction, user):
        self.bot.dispatch("picklist_reaction", reaction, user)

    async def last_observed(self, member: converters.DiscordUser):
        """Lookup last_observed data."""
        query = """
                SELECT DISTINCT ON (unix) unix, action
                FROM tracker
                WHERE user_id = $1
                ORDER BY unix DESC;
                """
        last_seen = await self.bot.cxn.fetchrow(query, member.id) or None

        query = """
                SELECT MAX(unix)
                FROM messages
                WHERE author_id = $1;
                """
        last_spoke = await self.bot.cxn.fetchval(query, member.id) or None

        if hasattr(member, "guild"):
            query = """
                    SELECT MAX(unix)
                    FROM messages
                    WHERE author_id = $1
                    AND server_id = $2;
                    """
            server_last_spoke = (
                await self.bot.cxn.fetchval(
                    query,
                    member.id,
                    member.guild.id,
                )
                or None
            )
        else:
            server_last_spoke = None

        if last_seen:
            action = last_seen[1]
            last_seen = last_seen[0]
            last_seen = utils.time_between(int(last_seen), int(time.time()))
        else:
            action = None
            last_seen = None
        if last_spoke:
            last_spoke = utils.time_between(int(last_spoke), int(time.time()))
        else:
            last_spoke = None
        if server_last_spoke:
            server_last_spoke = utils.time_between(
                int(server_last_spoke), int(time.time())
            )
        else:
            server_last_spoke = None

        observed_data = {
            "action": action,
            "last_seen": last_seen,
            "last_spoke": last_spoke,
            "server_last_spoke": server_last_spoke,
        }
        return observed_data

    async def user_data(self, ctx, member: converters.DiscordUser):
        """Lookup name & avatar data."""
        query = """
                SELECT name
                FROM usernames
                WHERE user_id = $1
                ORDER BY changed_at DESC NULLS LAST;
                """
        usernames = await self.bot.cxn.fetch(query, member.id)

        query = """
                SELECT avatar_id
                FROM useravatars
                WHERE user_id = $1
                ORDER BY unix DESC NULLS LAST;
                """
        avatars = await self.bot.cxn.fetch(query, member.id)

        if hasattr(member, "guild"):
            query = """
                    SELECT nickname
                    FROM usernicks
                    WHERE user_id = $1
                    AND server_id = $2
                    ORDER BY changed_at DESC NULLS LAST;
                    """
            nicknames = await self.bot.cxn.fetch(query, member.id, ctx.guild.id)
        else:
            nicknames = None

        if avatars:
            avatars = [
                f"https://cdn.discordapp.com/attachments/{self.avatar_webhook.channel.id}/{x[0]}/{member.id}.png"
                for x in avatars
            ]
        if nicknames:
            nicknames = ", ".join([record["nickname"] for record in nicknames])
        if usernames:
            usernames = ", ".join([record["name"] for record in usernames])

        observed_data = {
            "usernames": usernames or None,
            "nicknames": nicknames or None,
            "avatars": avatars or None,
        }
        return observed_data
