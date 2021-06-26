import PIL
import discord
import time
import io
import math
import traceback
import asyncio
import typing
from discord.ext import commands, tasks
from dislash.interactions import *
from dislash.slash_commands import *
import json

from matplotlib.pyplot import show
from utilities import decorators
from utilities import images
from utilities import avatars
from utilities import converters
from datetime import datetime
import numpy as np
from PIL import Image


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

        self.avatar_saver = avatars.AvatarSaver(bot, "hi")

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
            await self.avatar_saver.do_avatar(after)
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


    @commands.command()
    async def blah(self, ctx):
        from utilities import images

        query = """
                SELECT author_id, COUNT(*) FROM messages
                WHERE server_id = $1
                GROUP BY author_id
                ORDER BY count DESC
                LIMIT 5;
                """
        await ctx.trigger_typing()
        records = await self.bot.cxn.fetch(query, ctx.guild.id)
        data = {
            str(await self.bot.fetch_user(record["author_id"])): record["count"]
            for record in records
        }
        image = Image.new("RGBA", (len(data) * 200, 1000), (216, 183, 255))
        while max(data.values()) > 1000:
            data = {user: count // 2 for user, count in data.items()}
        for user, count in data.items():
            bar = images.get_bar(user, count)
            image.paste(im=bar, box=(list(data.values()).index(count) * 200, 0))

        buffer = io.BytesIO()
        image.save(buffer, "png")  # 'save' function for PIL
        buffer.seek(0)
        dfile = discord.File(fp=buffer, filename="mstats.png")
        em = discord.Embed(title="Message Stats", color=self.bot.constants.embed)
        em.set_image(url="attachment://mstats.png")
        await ctx.send_or_reply(embed=em, file=dfile)

    @commands.command()
    async def avyquilt(self, ctx, user: converters.DiscordMember = None):
        user = user or ctx.author

        query = """
                SELECT avs.url
                FROM (SELECT avatar, first_seen
                FROM (SELECT avatar, LAG(avatar)
                OVER (order by first_seen desc) AS old_avatar, first_seen
                FROM avatars WHERE avatars.user_id = $1) a
                WHERE avatar != old_avatar OR old_avatar IS NULL) avys
                LEFT JOIN avs ON avs.hash = avys.avatar
                ORDER BY avys.first_seen DESC LIMIT 100
                """

        urls = await self.bot.cxn.fetch(query, user.id)

        async def url_to_bytes(url):
            if not url:
                return None
            bytes_av = await self.bot.get(url, res_method="read")
            return bytes_av

        avys = await asyncio.gather(*[url_to_bytes(url['url']) for url in urls])
        file = await self.bot.loop.run_in_executor(None, images.quilt, avys)

        await ctx.send(file=discord.File(file, f'{user.id}_avatars.png'))