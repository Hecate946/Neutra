import discord
import time
import io
import traceback
import asyncio
from discord.ext import commands, tasks
from dislash.interactions import *
from dislash.slash_commands import *
import json
from utilities import decorators
from utilities import utils
from datetime import datetime


def setup(bot):
    bot.add_cog(Testing(bot))
    slash = SlashClient(bot)


class Testing(commands.Cog):
    """
    A cog for testing features
    """

    def __init__(self, bot):
        self.bot = bot
        self.avatar_batch = []

        self.batch_lock = asyncio.Lock(loop=bot.loop)
        self.queue = asyncio.Queue(loop=bot.loop)

        self.inserter.start()
        self.dispatch_avatars.start()

    @decorators.command()
    async def archive(self, ctx):
        # await self.insertion()
        query = """
                SELECT user_id, avatar
                FROM testavs LIMIT 1;
                """
        record = await self.bot.cxn.fetchrow(query)
        print(record)
        await ctx.send_or_reply(
            f"https://img.discord.wf/avatars/{record['user_id']}/{record['avatar']}.png?size=1024"
        )

    async def insertion(self):
        query = """
                INSERT INTO testavs (user_id, avatar)
                SELECT x.user_id, x.avatar
                FROM JSONB_TO_RECORDSET($1::JSONB)
                AS x(user_id BIGINT, avatar TEXT);
                """
        for user in self.bot.users:
            async with self.bot.session.get(
                f"https://img.discord.wf/avatars/{user.id}/{user.avatar}.png"
            ) as resp:
                print(resp.content)
            self.avs.append(
                {
                    "user_id": user.id,
                    "avatar": user.avatar,
                }
            )

        data = json.dumps(self.avs)
        await self.bot.cxn.execute(query, data)

        print("completed")

    @commands.command()
    async def wut(self, ctx):

        # Send a message with buttons
        await ctx.buttons("This message has buttons!")

    @commands.command()
    async def a(self, ctx, role: discord.Role):
        st = time.time()
        users = sum(1 for m in role.guild.members if m._roles.has(role.id))
        await ctx.send(str(time.time() - st))
        st = time.time()
        users = sum(1 for m in role.guild.members if role in m.roles)
        await ctx.send(str(time.time() - st))

    @commands.Cog.listener()
    @decorators.wait_until_ready()
    @decorators.event_check(lambda s, b, a: not a.bot)
    async def on_user_update(self, before, after):
        """
        Here's where we get notified of avatar changes
        """
        if before.avatar != after.avatar:
            if self.bot.testing_webhook:  # Check if we have the webhook set up.
                async with self.batch_lock:
                    try:
                        avatar_url = str(before.avatar_url_as(format="png", size=1024))
                        resp = await self.bot.get((avatar_url), res_method="read")
                        data = io.BytesIO(resp)
                        dfile = discord.File(data, filename=f"{after.id}.png")
                        self.queue.put_nowait(dfile)
                    except Exception as e:
                        await self.bot.logging_webhook.send(
                            f"Error in avatar_batcher: {e}"
                        )
                        await self.bot.logging_webhook.send(
                            "```prolog\n" + str(traceback.format_exc()) + "```"
                        )

    @tasks.loop(seconds=1.0)
    async def inserter(self):
        if self.avatar_batch:  # Save user avatars
            query = """
                    INSERT INTO testavs (user_id, avatar)
                    SELECT x.user_id, x.avatar_id
                    FROM JSONB_TO_RECORDSET($1::JSONB)
                    AS x(user_id BIGINT, avatar_id BIGINT)
                    """
            async with self.batch_lock:
                data = json.dumps(self.avatar_batch)
                await self.bot.cxn.execute(query, data)
                self.avatar_batch.clear()

    @tasks.loop(seconds=0.0)
    async def dispatch_avatars(self):
        while True:
            files = [await self.queue.get() for _ in range(10)]
            try:
                upload_batch = await self.bot.testing_webhook.send(
                    files=files, wait=True
                )
                for x in upload_batch.attachments:
                    self.avatar_batch.append(
                        {
                            "user_id": int(x.filename.split(".")[0]),
                            "avatar_id": x.id,
                        }
                    )
            except discord.HTTPException as e:
                # Here the combined files likely went over the 8mb file limit
                # Lets divide them up into 2 parts and send them separately.
                upload_batch_1 = await self.bot.testing_webhook.send(
                    files=files[:5], wait=True
                )
                upload_batch_2 = await self.bot.testing_webhook.send(
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
                        }
                    )
                try:
                    await self.bot.logging_webhook.send(
                        f"{self.emote_dict['success']} **Information** `{datetime.utcnow()}`\n"
                        f"```prolog\nQueue: Payload data limit resolved.```",
                        username=f"{self.user.name} Logger",
                        avatar_url=self.bot.constants.avatars["green"],
                    )
                except Exception:
                    pass
            except Exception as e:
                self.bot.dispatch("error", "queue_error", tb=utils.traceback_maker(e))
