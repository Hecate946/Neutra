import io
import json
import os
import re
import time
import asyncio
import discord
import logging
import datetime
import traceback

from collections import Counter, defaultdict
from discord.ext import commands, tasks

from utilities import utils, converters
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
        self.avatar_webhook = None
        self.avatar_batch = list()
        self.command_batch = list()
        self.message_batch = list()
        self.tracker_batch = dict()
        self.snipe_batch = list()
        self.member_batch = defaultdict(list)
        self.emoji_batch = defaultdict(Counter)
        self.usernames_batch = defaultdict(list)
        self.nicknames_batch = defaultdict(list)
        self.roles_batch = defaultdict(list)
        self.status_batch = defaultdict(list)
        self.spammer_batch = dict()
        self.to_upload = list()
        self.batch_lock = asyncio.Lock(loop=bot.loop)
        self.spam_control = commands.CooldownMapping.from_cooldown(
            10, 12, commands.BucketType.user
        )
        self._auto_spam_count = Counter()
        self.bulk_inserter.start()
        self.dispatch_avatars.start()

    def cog_unload(self):
        self.background_task.stop()
        self.bulk_inserter.stop()

    @tasks.loop(seconds=2.0)
    async def bulk_inserter(self):
        self.bot.batch_inserts += 1
        # Insert all status changes
        if self.status_batch:
            async with self.batch_lock:
                for data in self.status_batch.items():
                    user_id = data[1]["user_id"]
                    bstatus = data[1]["bstatus"]
                    query = """
                            SELECT last_changed FROM userstatus;
                            """
                    res2 = await self.bot.cxn.fetchval(query)
                    if res2 is not None:
                        if time.time() < res2:
                            await self.bot.bot_channel.send(f"fuck res1 < res2")
                    query = """
                            INSERT INTO userstatus (user_id, last_changed)
                            VALUES ($1, $2)
                            ON CONFLICT (user_id)
                            DO UPDATE SET {0} = userstatus.{0} + ($2 - userstatus.last_changed),
                            last_changed = $2
                            WHERE userstatus.user_id = $1;
                            """.format(
                        bstatus
                    )

                    await self.bot.cxn.execute(query, user_id, time.time())
                self.status_batch.clear()
        # Insert all the commands executed.
        if self.command_batch:
            query = """
                    INSERT INTO commands (
                        server_id, channel_id,
                        author_id, timestamp,
                        prefix, command, failed
                    )
                    SELECT x.server, x.channel,
                           x.author, x.timestamp,
                           x.prefix, x.command, x.failed
                    FROM jsonb_to_recordset($1::jsonb)
                    AS x(
                        server BIGINT, channel BIGINT,
                        author BIGINT, timestamp TIMESTAMP,
                        prefix TEXT, command TEXT, failed BOOLEAN
                    )
                    """
            async with self.batch_lock:
                data = json.dumps(self.command_batch)
                await self.bot.cxn.execute(query, str(data))

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

        # Snipe command setup
        if self.snipe_batch:
            query = """
                    UPDATE messages
                    SET deleted = True
                    WHERE message_id = $1;
                    """
            async with self.batch_lock:
                await self.bot.cxn.executemany(query, ((x,) for x in self.snipe_batch))
            self.snipe_batch.clear()

        # mass inserts nicknames, usernames, and roles
        if self.member_batch:
            query = """
                    WITH username_insert AS (
                        INSERT INTO usernames(user_id, usernames)
                        VALUES ($1, $2)
                        ON CONFLICT (user_id)
                        DO NOTHING RETURNING user_id
                    ),
                    nickname_insert AS (
                        INSERT INTO nicknames(user_id, server_id, nicknames)
                        VALUES ($1, $3, $4)
                        ON CONFLICT (user_id, server_id)
                        DO NOTHING RETURNING user_id
                    )
                    INSERT INTO userroles(user_id, server_id, roles)
                    VALUES ($1, $3, $5)
                    ON CONFLICT (user_id, server_id) DO NOTHING;
                    """
            async with self.batch_lock:
                await self.bot.cxn.executemany(
                    query,
                    (
                        (
                            data[1][0]["user_id"],
                            data[1][0]["username"],
                            data[1][0]["server_id"],
                            data[1][0]["nickname"],
                            data[1][0]["roles"],
                        )
                        for data in self.member_batch.items()
                    ),
                )
            self.member_batch.clear()

        # Emoji usage tracking
        if self.emoji_batch:
            query = """
                    INSERT INTO emojistats (
                        serveremoji,
                        server_id,
                        emoji_id,
                        total
                    )
                    VALUES ($1, $2, $3, $4)
                    ON CONFLICT (serveremoji)
                    DO UPDATE SET total = emojistats.total + excluded.total;
                    """
            async with self.batch_lock:
                for data in self.emoji_batch.items():
                    server_id = data[0]
                    for key in data[1]:
                        emoji_id = key
                    count = data[1][emoji_id]
                    await self.bot.cxn.execute(
                        query, f"{server_id}:{emoji_id}", server_id, emoji_id, count
                    )
                self.bot.emojis_seen += len(self.emoji_batch.items())
            self.emoji_batch.clear()

        # Insert every single message into db
        if self.message_batch:
            query = """
                    INSERT INTO messages (
                        unix, timestamp, content,
                        message_id, author_id,
                        channel_id, server_id
                    )
                    SELECT x.unix, x.timestamp,
                           x.content, x.message_id, x.author_id,
                           x.channel_id, x.server_id
                    FROM jsonb_to_recordset($1::jsonb)
                    AS x(
                        unix REAL, timestamp TIMESTAMP, content TEXT,
                        message_id BIGINT, author_id BIGINT,
                        channel_id BIGINT, server_id BIGINT
                    )
                    """
            async with self.batch_lock:
                data = json.dumps(self.message_batch)
                await self.bot.cxn.execute(query, data)
                self.bot.messages += len(self.message_batch)
            self.message_batch.clear()

        # Track users who spam messages
        if self.spammer_batch:
            query = """
                    INSERT INTO spammers
                    VALUES ($1, $2, 1)
                    ON CONFLICT (user_id, server_id)
                    DO UPDATE SET spamcount = spammers.spamcount + 1;
                    """
            async with self.batch_lock:
                for entry in self.spammer_batch.items():
                    user_id = entry[0]
                    server_id = entry[1]
                    await self.bot.cxn.execute(query, user_id, server_id)
            self.spammer_batch.clear()

        # Track user last seen times
        if self.tracker_batch:
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
                    ((entry[0], entry[1][0], entry[1][1]) for entry in self.tracker_batch.items()),
                )
            self.tracker_batch.clear()

        if self.avatar_batch:
            # query = f"""UPDATE useravatars SET avatars = CONCAT_WS(',', avatars, cast($1 as text)) WHERE user_id = $2"""
            query = """
                    INSERT INTO useravatars (
                        user_id, avatar_id, unix
                    )
                    SELECT x.user_id, x.avatar_id, x.unix
                    FROM jsonb_to_recordset($1::jsonb)
                    AS x(
                        user_id BIGINT, avatar_id BIGINT, unix REAL
                    )
                    """
            async with self.batch_lock:
                data = json.dumps(self.avatar_batch)
                await self.bot.cxn.execute(query, data)
                self.bot.avchanges += len(self.avatar_batch)
            self.avatar_batch.clear()

        if self.usernames_batch:
            query = """
                    UPDATE usernames
                    SET usernames = CONCAT_WS(
                        ',', usernames, cast($1 as text)
                    )
                    WHERE user_id = $2;
                    """
            async with self.batch_lock:
                for data in self.usernames_batch.items():
                    user_id = data[1]["user_id"]
                    username = data[1]["username"]

                    await self.bot.cxn.execute(query, str(username), user_id)
                self.bot.namechanges += len(self.usernames_batch.items())
                self.usernames_batch.clear()

        if self.nicknames_batch:
            query = f"""
                    UPDATE nicknames
                    SET nicknames = CONCAT_WS(
                        ',', nicknames, cast($1 as text)
                    )
                    WHERE user_id = $2
                    AND server_id = $3;
                    """
            async with self.batch_lock:
                for data in self.nicknames_batch.items():
                    user_id = data[1]["user_id"]
                    server_id = data[1]["server_id"]
                    nickname = data[1]["nickname"]

                    await self.bot.cxn.execute(query, str(nickname), user_id, server_id)
                self.bot.nickchanges += len(self.nicknames_batch.items())
                self.nicknames_batch.clear()

        if self.roles_batch:
            query = """
                    UPDATE userroles
                    SET roles = $1
                    WHERE user_id = $2
                    AND server_id = $3;
                    """
            async with self.batch_lock:
                for data in self.roles_batch.items():
                    user_id = data[1]["user_id"]
                    server_id = data[1]["server_id"]
                    roles = data[1]["roles"]

                    await self.bot.cxn.execute(query, str(roles), user_id, server_id)
                self.bot.rolechanges += len(self.roles_batch.items())
                self.roles_batch.clear()

    @bulk_inserter.before_loop
    async def get_webhook(self):
        """
        This loads our existing
        avatar saving webhook
        from the db or creates
        it if it doesn't exist.
        Cancels avatar saving
        if no avchan is found
        in ./config.json
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
                webhook = discord.Webhook.partial(
                    id=wh_id,
                    token=wh_token,
                    adapter=discord.AsyncWebhookAdapter(self.bot.session),
                )
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

    @tasks.loop(seconds=0.5)
    async def dispatch_avatars(self):
        if len(self.to_upload) > 8:
            async with self.batch_lock:
                if len(self.to_upload) > 10:
                    await self.bot.bot_channel.send(f"FUCK worst nightmare")
                try:
                    upload_batch = await self.avatar_webhook.send(
                        files=self.to_upload, wait=True
                    )
                    for x in upload_batch.attachments:
                        self.avatar_batch.append(
                            {
                                "user_id": int(x.filename.split(".")[0]),
                                "avatar_id": x.id,
                                "unix": time.time(),
                            }
                        )
                except discord.errors.HTTPException:
                    pass
            self.to_upload.clear()

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
    async def on_message_delete(self, message):
        if not message.guild:
            return
        if message.author.bot:
            return

        async with self.batch_lock:
            self.snipe_batch.append(message.id)

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
    async def on_member_update(self, before, after):

        if before.status != after.status:
            async with self.batch_lock:
                self.status_batch[after.id] = {
                    "user_id": after.id,
                    "bstatus": str(before.status),
                }
        if after.bot:
            return

        if await self.status_changed(before, after):
            async with self.batch_lock:
                self.tracker_batch[before.id] = (time.time(), "updating their status")

        if await self.nickname_changed(before, after):
            async with self.batch_lock:
                self.nicknames_batch[after.id] = {
                    "user_id": after.id,
                    "server_id": after.guild.id,
                    "nickname": after.display_name,
                }

        if await self.roles_changed(before, after):
            async with self.batch_lock:
                roles = ",".join(
                    [str(x.id) for x in after.roles if x.name != "@everyone"]
                )
                self.roles_batch[after.id] = {
                    "user_id": after.id,
                    "server_id": after.guild.id,
                    "roles": roles,
                }

    @commands.Cog.listener()
    @decorators.wait_until_ready()
    async def on_user_update(self, before, after):
        """
        Here's where we get notified of avatar,
        username, and discriminator changes.
        """
        if after.bot:
            return  # Don't care about bots  # Update last seen time
        if await self.avatar_changed(before, after):
            async with self.batch_lock:
                self.tracker_batch[before.id] = (time.time(), "updating their avatar")
            if self.avatar_webhook:  # Check if we have the webhook set up.
                try:
                    avatar_url = str(after.avatar_url_as(format="png", size=1024))
                    resp = await self.bot.get((avatar_url), res_method="read")
                    data = io.BytesIO(resp)
                    dfile = discord.File(data, filename=f"{after.id}.png")
                    self.to_upload.append(dfile)
                    await self.dispatch_avatars()
                except Exception as e:
                    await self.bot.bot_channel.send(f"Error in avatar_batcher: {e}")
                    await self.bot.bot_channel.send(
                        "```prolog\n" + str(traceback.format_exc()) + "```"
                    )

        if await self.username_changed(before, after):
            async with self.batch_lock:
                self.usernames_batch[after.id] = {
                    "user_id": after.id,
                    "username": str(after),
                }
                self.tracker_batch[before.id] = (time.time(), "updating their username")

    @commands.Cog.listener()
    @decorators.wait_until_ready()
    async def on_message(self, message):

        if message.author.bot:
            return
        if not message.guild:
            return
        async with self.batch_lock:
            self.message_batch.append(
                {
                    "unix": message.created_at.timestamp(),
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

        ctx = await self.bot.get_context(message)
        author = message.author

        bucket = self.spam_control.get_bucket(message)
        current = message.created_at.replace(tzinfo=datetime.timezone.utc).timestamp()
        retry_after = bucket.update_rate_limit(current)
        if retry_after:
            self._auto_spam_count[author.id] += 1
            if self._auto_spam_count[author.id] >= 5:
                await ctx.bot_channel("Spammer")
                async with self.batch_lock:
                    self.spammer_batch[author.id] = message.guild.id
                del self._auto_spam_count[author.id]
            return
        else:
            self._auto_spam_count.pop(author.id, None)

    @commands.Cog.listener()
    @decorators.wait_until_ready()
    async def on_typing(self, channel, user, when):

        if user.bot:
            return
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
        if user.bot:
            return
        async with self.batch_lock:
            self.tracker_batch[payload.user_id] = (time.time(), "reacting to a message")

    @commands.Cog.listener()
    @decorators.wait_until_ready()
    async def on_voice_state_update(self, member, before, after):

        if member.bot:
            return
        async with self.batch_lock:
            self.tracker_batch[member.id] = (time.time(), "changing their voice state")

    @commands.Cog.listener()
    @decorators.wait_until_ready()
    async def on_invite_create(self, invite):

        if invite.inviter.bot:
            return
        async with self.batch_lock:
            self.tracker_batch[invite.inviter.id] = (time.time(), "creating an invite")

    @commands.Cog.listener()
    @decorators.wait_until_ready()
    async def on_member_join(self, member):

        if member.bot:
            return
        async with self.batch_lock:
            self.tracker_batch[member.id] = (time.time(), "joining a server")

        await asyncio.sleep(2)

        async with self.batch_lock:
            self.member_batch[member.id].append(
                {
                    "user_id": member.id,
                    "username": str(member),
                    "nickname": member.display_name,
                    "server_id": member.guild.id,
                    "roles": ",".join(
                        [str(x.id) for x in member.roles if x.name != "@everyone"]
                    ),
                }
            )

    @commands.Cog.listener()
    @decorators.wait_until_ready()
    async def on_member_leave(self, member):

        if member.bot:
            return
        async with self.batch_lock:
            self.tracker_batch[member.id] = (time.time(), "leaving a server")

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
        if last_spoke:
            last_spoke = utils.time_between(int(last_spoke), int(time.time()))
        if server_last_spoke:
            server_last_spoke = utils.time_between(
                int(server_last_spoke), int(time.time())
            )

        observed_data = {
            "action": action or None,
            "last_seen": last_seen or None,
            "last_spoke": last_spoke or None,
            "server_last_spoke": server_last_spoke or None,
        }
        return observed_data

    async def user_data(self, ctx, member: converters.DiscordUser):
        """Lookup name & avatar data."""

        usernames = (
            await self.bot.cxn.fetchval(
                "SELECT usernames from usernames WHERE user_id = $1 LIMIT 1", member.id
            )
            or None
        )

        query = """
                SELECT (avatar_id)
                FROM useravatars
                WHERE user_id = $1
                ORDER BY unix DESC;
                """
        avatars = await self.bot.cxn.fetch(query, member.id)
        if hasattr(member, "guild"):
            nicknames = (
                await self.bot.cxn.fetchval(
                    "SELECT nicknames FROM nicknames WHERE user_id = $1 AND server_id = $2 LIMIT 1",
                    member.id,
                    ctx.guild.id,
                )
                or None
            )

        else:
            nicknames = None

        if usernames:
            usernames = str(usernames).replace(",", ", ")
        if avatars:
            avatars = [
                f"https://cdn.discordapp.com/attachments/{self.bot.constants.avchan}/{x[0]}/{member.id}.png"
                for x in avatars
            ]
        if hasattr(member, "guild"):
            if nicknames:
                nicknames = str(nicknames).replace(",", ", ")

        observed_data = {
            "usernames": usernames or None,
            "nicknames": nicknames or None,
            "avatars": avatars or None,
        }
        return observed_data

    @commands.Cog.listener()
    @decorators.wait_until_ready()
    async def on_reaction_add(self, reaction, user):
        self.bot.dispatch("picklist_reaction", reaction, user)

    @commands.Cog.listener()
    @decorators.wait_until_ready()
    async def on_reaction_remove(self, reaction, user):
        self.bot.dispatch("picklist_reaction", reaction, user)
