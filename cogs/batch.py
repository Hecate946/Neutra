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

from utilities import utils, converters, decorators

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
        self.command_batch = defaultdict(list)
        self.snipe_batch = defaultdict(list)
        self.member_batch = defaultdict(list)
        self.emoji_batch = defaultdict(Counter)
        self.message_batch = defaultdict(list)
        self.tracker_batch = defaultdict(list)
        self.avatar_batch = defaultdict(list)
        self.usernames_batch = defaultdict(list)
        self.nicknames_batch = defaultdict(list)
        self.roles_batch = defaultdict(list)
        self.status_batch = defaultdict(list)
        self.spammer_batch = dict()
        self.batch_lock = asyncio.Lock(loop=bot.loop)
        self.spam_control = commands.CooldownMapping.from_cooldown(
            10, 12, commands.BucketType.user
        )
        self._auto_spam_count = Counter()
        self.bulk_inserter.start()
        # self.status_inserter.start()

    def cog_unload(self):
        self.bulk_inserter.stop()

    @discord.utils.cached_property
    def avatar_saver(self):
        wh_id, wh_token, wh_channel = self.bot.constants.avsaver
        webhook = discord.Webhook.partial(
            id=wh_id,
            token=wh_token,
            adapter=discord.AsyncWebhookAdapter(self.bot.session),
        )
        return (webhook, int(wh_channel))

    @tasks.loop(seconds=2.0)
    async def bulk_inserter(self):
        self.bot.batch_inserts += 1
        # Insert all status changes
        if self.status_batch:
            async with self.batch_lock:
                for data in self.status_batch.items():
                    user_id = data[1]["user_id"]
                    bstatus = data[1]["bstatus"]
                    res1 = time.time()
                    query = """
                            SELECT last_changed FROM userstatus;
                            """
                    res2 = await self.bot.cxn.fetchval(query)
                    if res2 is not None:
                        if res1 < res2:
                            await self.bot.bot_channel.send(F"fuck res1 < res2")
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
                        server_id, channel_id, author_id,
                        timestamp, prefix, command, failed
                    )
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                    """
            async with self.batch_lock:
                # print([x[1][0] for x in self.command_batch.items()])
                # print([y.values() for y in [x[1][0] for x in self.command_batch.items()]])
                # await self.bot.cxn.executemany(
                #     query,
                #     [y for y in [x[1][0].keys() for x in self.command_batch.items()]]
                # )
                for data in self.command_batch.items():
                    server_id = data[1][0]["server_id"]
                    channel_id = data[1][0]["channel_id"]
                    author_id = data[1][0]["author_id"]
                    timestamp = data[1][0]["timestamp"]
                    prefix = data[1][0]["prefix"]
                    command = data[1][0]["command"]
                    failed = data[1][0]["failed"]
                    content = data[1][0]["content"]

                    await self.bot.cxn.execute(
                        query,
                        server_id,
                        channel_id,
                        author_id,
                        timestamp,
                        prefix,
                        command,
                        failed,
                    )

                    # Command logger to ./data/logs/commands.log
                    destination = None
                    if server_id is None:
                        destination = "Private Message"
                    else:
                        destination = f"#{self.bot.get_channel(channel_id)} [{channel_id}] ({self.bot.get_guild(server_id)}) [{server_id}]"
                    command_logger.info(
                        f"{self.bot.get_user(author_id)} in {destination}: {content}"
                    )
                self.command_batch.clear()

        # Snipe command setup
        if self.snipe_batch:
            query = """
                    UPDATE messages
                    SET deleted = True
                    WHERE message_id = $1
                    AND author_id = $2
                    AND channel_id = $3;
                    """
            async with self.batch_lock:
                for data in self.snipe_batch.items():
                    channel_id = data[1][0]["channel_id"]
                    message_id = data[1][0]["message_id"]
                    author_id = data[1][0]["author_id"]

                    await self.bot.cxn.execute(query, message_id, author_id, channel_id)
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
                for data in self.member_batch.items():
                    user_id = data[1][0]["user_id"]
                    server_id = data[1][0]["server_id"]
                    username = data[1][0]["username"]
                    nickname = data[1][0]["nickname"]
                    roles = data[1][0]["roles"]

                    await self.bot.cxn.execute(
                        query,
                        user_id,
                        username,
                        server_id,
                        nickname,
                        roles,
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
                        unix, timestamp,
                        content, message_id,
                        author_id, channel_id,
                        server_id
                    )
                    VALUES (
                        $1, $2,
                        $3, $4,
                        $5, $6,
                        $7
                    );
                    """
            async with self.batch_lock:
                for data in self.message_batch.items():
                    unix = data[1][0]["unix"]
                    timestamp = data[1][0]["timestamp"]
                    content = data[1][0]["content"]
                    message_id = data[1][0]["message_id"]
                    author_id = data[1][0]["author_id"]
                    channel_id = data[1][0]["channel_id"]
                    server_id = data[1][0]["server_id"]

                    await self.bot.cxn.execute(
                        query,
                        unix,
                        timestamp,
                        content,
                        message_id,
                        author_id,
                        channel_id,
                        server_id,
                    )
                self.bot.messages += len(self.message_batch.items())
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
                    INSERT INTO tracker
                    VALUES ($1, $2)
                    ON CONFLICT (user_id)
                    DO UPDATE SET unix = $2
                    WHERE tracker.user_id = $1;
                    """
            async with self.batch_lock:
                for data in self.tracker_batch.items():
                    user_id = data[1]["user_id"]
                    unix = data[1]["unix"]

                    await self.bot.cxn.execute(query, user_id, unix)
                self.tracker_batch.clear()

        # query = f"""UPDATE useravatars SET avatars = CONCAT_WS(',', avatars, cast($1 as text)) WHERE user_id = $2"""
        query = """
                INSERT INTO useravatars
                VALUES ($1, $2, $3);
                """
        async with self.batch_lock:
            for data in self.avatar_batch.items():
                user_id = data[1]["user_id"]
                avatar = data[1]["avatar"]

                await self.bot.cxn.execute(query, user_id, avatar, time.time())
            self.bot.avchanges += len(self.avatar_batch.items())
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
            self.command_batch[ctx.message.id].append(
                {
                    "server_id": server_id,
                    "channel_id": ctx.channel.id,
                    "author_id": ctx.author.id,
                    "timestamp": ctx.message.created_at.utcnow(),
                    "prefix": ctx.prefix,
                    "command": ctx.command.qualified_name,
                    "failed": ctx.command_failed,
                    "content": ctx.message.clean_content,
                }
            )

    @commands.Cog.listener()
    @decorators.wait_until_ready()
    async def on_message_delete(self, message):
        if message.author.bot or not message.guild:
            return
        if message.author.bot:
            return

        async with self.batch_lock:
            self.snipe_batch[message.id].append(
                {
                    "message_id": message.id,
                    "author_id": message.author.id,
                    "channel_id": message.channel.id,
                }
            )

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
                self.tracker_batch[after.id] = {
                    "unix": time.time(),
                    "user_id": after.id,
                }

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

        if after.bot:
            return
        async with self.batch_lock:
            self.tracker_batch[after.id] = {"unix": time.time(), "user_id": after.id}

        if await self.avatar_changed(before, after):
            try:
                avatar_url = str(after.avatar_url_as(format="png", size=1024))
                resp = await self.bot.get((avatar_url), res_method="read")
                data = io.BytesIO(resp)
                dfile = discord.File(data, filename=f"{after.id}.png")
                upload = await self.avatar_saver[0].send(
                    content=f"**UID: {after.id}**", file=dfile, wait=True
                )
                attachment_id = upload.attachments[0].id
                async with self.batch_lock:
                    self.avatar_batch[after.id] = {
                        "user_id": after.id,
                        "avatar": attachment_id,
                    }
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

    @commands.Cog.listener()
    @decorators.wait_until_ready()
    async def on_message(self, message):

        if message.author.bot:
            return
        if not message.guild:
            return
        async with self.batch_lock:
            self.message_batch[message.id].append(
                {
                    "unix": message.created_at.timestamp(),
                    "timestamp": message.created_at.utcnow(),
                    "content": message.clean_content,
                    "message_id": message.id,
                    "author_id": message.author.id,
                    "channel_id": message.channel.id,
                    "server_id": message.guild.id,
                }
            )
            self.tracker_batch[message.author.id] = {
                "unix": message.created_at.timestamp(),
                "user_id": message.author.id,
            }

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
            self.tracker_batch[user.id] = {"unix": time.time(), "user_id": user.id}

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
            self.tracker_batch[author_id] = {"unix": time.time(), "user_id": author_id}

    @commands.Cog.listener()
    @decorators.wait_until_ready()
    async def on_raw_reaction_add(self, payload):

        user = self.bot.get_user(payload.user_id)
        if user.bot:
            return
        async with self.batch_lock:
            self.tracker_batch[user.id] = {
                "unix": time.time(),
                "user_id": payload.user_id,
            }

    @commands.Cog.listener()
    @decorators.wait_until_ready()
    async def on_voice_state_update(self, member, before, after):

        if member.bot:
            return
        async with self.batch_lock:
            self.tracker_batch[member.id] = {"unix": time.time(), "user_id": member.id}

    @commands.Cog.listener()
    @decorators.wait_until_ready()
    async def on_invite_create(self, invite):

        if invite.inviter.bot:
            return
        async with self.batch_lock:
            self.tracker_batch[invite.inviter.id] = {
                "unix": time.time(),
                "user_id": invite.inviter.id,
            }

    @commands.Cog.listener()
    @decorators.wait_until_ready()
    async def on_member_join(self, member):

        if member.bot:
            return
        async with self.batch_lock:
            self.tracker_batch[member.id] = {"unix": time.time(), "user_id": member.id}

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
            self.tracker_batch[member.id] = {"unix": time.time(), "user_id": member.id}

    async def last_observed(self, member: converters.DiscordUser):
        """Lookup last_observed data."""

        last_seen = (
            await self.bot.cxn.fetchval(
                "SELECT unix from tracker WHERE user_id = $1 LIMIT 1", member.id
            )
            or None
        )
        # TODO MAX(unix)? Really? think of a better way.
        last_spoke = (
            await self.bot.cxn.fetchval(
                "SELECT MAX(unix) FROM messages WHERE author_id = $1 LIMIT 1", member.id
            )
            or None
        )
        if hasattr(member, "guild"):
            server_last_spoke = (
                await self.bot.cxn.fetchval(
                    "SELECT MAX(unix) FROM messages WHERE author_id = $1 and server_id = $2 LIMIT 1",
                    member.id,
                    member.guild.id,
                )
                or None
            )
        else:
            server_last_spoke = None

        if last_seen:
            # last_seen = utils.format_time(datetime.datetime.utcfromtimestamp(last_seen))
            last_seen = utils.time_between(int(last_seen), int(time.time()))
        if last_spoke:
            last_spoke = utils.time_between(int(last_spoke), int(time.time()))
        if server_last_spoke:
            server_last_spoke = utils.time_between(
                int(server_last_spoke), int(time.time())
            )

        observed_data = {
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
        # avatars = await self.bot.cxn.fetchval(
        #     "SELECT avatars from useravatars WHERE user_id = $1 LIMIT 1", member.id) or None
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
                f"https://cdn.discordapp.com/attachments/{self.avatar_saver[1]}/{x[0]}/{member.id}.png"
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
