import PIL
import discord
import time
import io
import re
import traceback
import asyncio
import typing
from discord.ext import commands, tasks
from dislash.interactions import *
from dislash.slash_commands import *
import json

from matplotlib.pyplot import show
from utilities import decorators
from utilities import utils
from utilities import spotify
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

        self.inserter.start()
        self.dispatch_avatars.start()

        self.spotify_client_id = utils.config()["spotify_client_id"]
        self.spotify_client_secret = utils.config()["spotify_client_secret"]
        self.spotify = None

        if self.spotify_client_id and self.spotify_client_secret:
            self.spotify = spotify.Spotify(self.spotify_client_id, self.spotify_client_secret, aiosession=self.bot.session, loop=self.bot.loop)

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
    @decorators.cooldown(3, 10, bucket=commands.BucketType.user, bypass=[770690986908581948])
    async def meh(self, ctx):
        await ctx.reply("blah")


    @decorators.command(name="spotify")
    async def _spotify(self, ctx, *, url):
        linksRegex = '((http(s)*:[/][/]|www.)([a-z]|[A-Z]|[0-9]|[/.]|[~])*)'
        pattern = re.compile(linksRegex)
        matchUrl = pattern.match(url)
        song_url = url.replace('/', '%2F') if matchUrl is None else url

        # Rewrite YouTube playlist URLs if the wrong URL type is given
        playlistRegex = r'watch\?v=.+&(list=[^&]+)'
        matches = re.search(playlistRegex, song_url)
        groups = matches.groups() if matches is not None else []
        song_url = "https://www.youtube.com/playlist?" + groups[0] if len(groups) > 0 else song_url

        if self.spotify:
            if 'open.spotify.com' in song_url:
                song_url = 'spotify:' + re.sub('(http[s]?:\/\/)?(open.spotify.com)\/', '', song_url).replace('/', ':')
                # remove session id (and other query stuff)
                song_url = re.sub('\?.*', '', song_url)
            if song_url.startswith('spotify:'):
                parts = song_url.split(":")
                try:
                    if 'track' in parts:
                        res = await self.spotify.get_track(parts[-1])
                        song_url = res['artists'][0]['name'] + ' ' + res['name']
                        await ctx.send(song_url)

                    elif 'album' in parts:
                        res = await self.spotify.get_album(parts[-1])
                        for i in res['tracks']['items']:
                            song_url = i['name'] + ' ' + i['artists'][0]['name']
                            await ctx.send(song_url)
                            
                    elif 'playlist' in parts:
                        res = []
                        r = await self.spotify.get_playlist_tracks(parts[-1])
                        print(r)
                        while True:
                            res.extend(r['items'])
                            if r['next'] is not None:
                                r = await self.spotify.make_spotify_req(r['next'])
                                continue
                            else:
                                break
                        for i in res:
                            song_url = i['track']['name'] + ' ' + i['track']['artists'][0]['name']
                            #await ctx.send(song_url)
                    
                    else:
                        return await ctx.fail("Invalid Spotify URI.")
                except spotify.SpotifyError:
                    return await ctx.fail("Invalid Spotify URI.")