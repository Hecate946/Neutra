import time
import discord
import asyncio
import datetime
from discord.ext import commands, tasks
from collections import defaultdict
from utilities import utils, converters


def setup(bot):
    bot.add_cog(Tracker(bot))


class Tracker(commands.Cog):
    """
    Track user stats
    """

    def __init__(self, bot):
        self.bot = bot

        self.message_batch = defaultdict(list)
        self.tracker_batch = defaultdict(list)
        self.avatar_batch = defaultdict(list)
        self.usernames_batch = defaultdict(list)
        self.nicknames_batch = defaultdict(list)
        self.roles_batch = defaultdict(list)

        self.batch_lock = asyncio.Lock(loop=bot.loop)

        self.bulk_inserter.start()

    def cog_unload(self):
        self.bulk_inserter.stop()

    @tasks.loop(seconds=2.0)
    async def bulk_inserter(self):
        self.bot.batch_inserts += 1

        # ============#
        # On Message #
        # ============#
        query = """INSERT INTO messages (unix, timestamp, content, message_id, author_id, channel_id, server_id)
                   VALUES ($1, $2, $3, $4, $5, $6, $7);
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

        # ===============#
        # On Everything #
        # ===============#
        query = """INSERT INTO tracker VALUES ($1, $2)
                   ON CONFLICT (user_id) DO UPDATE SET unix = $2 WHERE tracker.user_id = $1
                """
        async with self.batch_lock:
            for data in self.tracker_batch.items():
                user_id = data[1]["user_id"]
                unix = data[1]["unix"]

                await self.bot.cxn.execute(query, user_id, unix)
            self.tracker_batch.clear()

        # ================#
        # On User Update #
        # ================#
        # query = f"""UPDATE useravatars SET avatars = CONCAT_WS(',', avatars, cast($1 as text)) WHERE user_id = $2"""
        # async with self.batch_lock:
        #     for data in self.avatar_batch.items():
        #         user_id = data[1]['user_id']
        #         avatar  = data[1]['avatar']

        #         await self.bot.cxn.execute(query, str(avatar), user_id)
        #     self.bot.avchanges += len(self.avatar_batch.items())
        #     self.avatar_batch.clear()

        query = f"""UPDATE usernames SET usernames = CONCAT_WS(',', usernames, cast($1 as text)) WHERE user_id = $2"""
        async with self.batch_lock:
            for data in self.usernames_batch.items():
                user_id = data[1]["user_id"]
                username = data[1]["username"]

                await self.bot.cxn.execute(query, str(username), user_id)
            self.bot.namechanges += len(self.usernames_batch.items())
            self.usernames_batch.clear()

        # ==================#
        # On Member Update #
        # ==================#
        query = f"""UPDATE nicknames SET nicknames = CONCAT_WS(',', nicknames, cast($1 as text)) WHERE user_id = $2 AND server_id = $3"""
        async with self.batch_lock:
            for data in self.nicknames_batch.items():
                user_id = data[1]["user_id"]
                server_id = data[1]["server_id"]
                nickname = data[1]["nickname"]

                await self.bot.cxn.execute(query, str(nickname), user_id, server_id)
            self.bot.nickchanges += len(self.nicknames_batch.items())
            self.nicknames_batch.clear()

        query = (
            f"""UPDATE userroles SET roles = $1 WHERE user_id = $2 AND server_id = $3"""
        )
        async with self.batch_lock:
            for data in self.roles_batch.items():
                user_id = data[1]["user_id"]
                server_id = data[1]["server_id"]
                roles = data[1]["roles"]

                await self.bot.cxn.execute(query, str(roles), user_id, server_id)
            self.bot.rolechanges += len(self.roles_batch.items())
            self.roles_batch.clear()

    # =================#
    # Check Functions #
    # =================#
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

    # =================#
    # Event Listeners #
    # =================#
    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        if self.bot.bot_ready is False:
            return

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
    async def on_user_update(self, before, after):
        if self.bot.bot_ready is False:
            return
        if after.bot:
            return
        async with self.batch_lock:
            self.tracker_batch[after.id] = {"unix": time.time(), "user_id": after.id}

        # if await self.avatar_changed(before, after):
        #     async with self.batch_lock:
        #         self.avatar_batch[after.id] = {
        #             "user_id": after.id,
        #             "avatar": after.avatar_url
        #         }

        if await self.username_changed(before, after):
            async with self.batch_lock:
                self.usernames_batch[after.id] = {
                    "user_id": after.id,
                    "username": str(after),
                }

    @commands.Cog.listener()
    async def on_message(self, message):
        if self.bot.bot_ready is False:
            return
        if message.author.bot or not message.guild:
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

    @commands.Cog.listener()
    async def on_typing(self, channel, user, when):
        if self.bot.bot_ready is False:
            return
        if user.bot:
            return
        async with self.batch_lock:
            self.tracker_batch[user.id] = {"unix": time.time(), "user_id": user.id}

    @commands.Cog.listener()
    async def on_raw_message_edit(self, payload):
        if self.bot.bot_ready is False:
            return
        channel_obj = self.bot.get_channel(payload.channel_id)
        try:
            message = await channel_obj.fetch_message(payload.message_id)
        except (RuntimeError, RuntimeWarning):
            pass
        except (discord.NotFound, discord.Forbidden):
            return
        if message.author.bot:
            return
        author_id = message.author.id
        async with self.batch_lock:
            self.tracker_batch[author_id] = {"unix": time.time(), "user_id": author_id}

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if self.bot.bot_ready is False:
            return
        user = self.bot.get_user(payload.user_id)
        if user.bot:
            return
        async with self.batch_lock:
            self.tracker_batch[user.id] = {
                "unix": time.time(),
                "user_id": payload.user_id,
            }

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if self.bot.bot_ready is False:
            return
        if member.bot:
            return
        async with self.batch_lock:
            self.tracker_batch[member.id] = {"unix": time.time(), "user_id": member.id}

    @commands.Cog.listener()
    async def on_invite_create(self, invite):
        if self.bot.bot_ready is False:
            return
        if invite.inviter.bot:
            return
        async with self.batch_lock:
            self.tracker_batch[invite.inviter.id] = {
                "unix": time.time(),
                "user_id": invite.inviter.id,
            }

    @commands.Cog.listener()
    async def on_member_join(self, member):
        if self.bot.bot_ready is False:
            return
        if member.bot:
            return
        async with self.batch_lock:
            self.tracker_batch[member.id] = {"unix": time.time(), "user_id": member.id}

    @commands.Cog.listener()
    async def on_member_leave(self, member):
        if self.bot.bot_ready is False:
            return
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
        # if avatars:
        #     avatars = str(avatars).replace(",",", ")
        if hasattr(member, "guild"):
            if nicknames:
                nicknames = str(nicknames).replace(",", ", ")

        observed_data = {
            "usernames": usernames or None,
            "nicknames": nicknames or None
            # "avatars": avatars or None
        }
        return observed_data
