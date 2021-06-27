# https://github.com/CuteFwan/Koishi

import io
import os
import json
import aiohttp
import asyncio
import discord
import logging

from collections import defaultdict
from datetime import datetime
from yarl import URL

from utilities import images

log = logging.getLogger("INFO_LOGGER")


class AvatarSaver:
    def __init__(self, webhook, pool, aiosession=None, loop=None):

        self.wh = webhook
        self.pool = pool
        self.aiosession = aiosession if aiosession else aiohttp.ClientSession()
        self.loop = loop if loop else asyncio.get_event_loop()

        self.avatars = defaultdict(list)
        self.pending = []
        self.queue = asyncio.Queue(loop=loop)

        self.is_saving = False

        if not self.wh:
            print("Avatar saving unavailable. Invalid Webhook.")
        elif not self.pool:
            print("Avatar saving unavailable. Invalid Connection Pool.")
        else:
            self.loop.create_task(self.batch_post_avatars())
            self.loop.create_task(self.inserter())
            self.loop.create_task(self.downloader())
            self.is_saving = True


    def save(self, user):
        if self.is_saving:
            avatar_name = user.avatar if user.avatar else user.default_avatar.name
            self.pending.append({
                "user_id": user.id,
                "avatar": avatar_name,
                "first_seen": str(datetime.utcnow())
            })
            self.avatars[avatar_name] = str(user.avatar_url_as(static_format='png'))


    async def inserter(self):
        while True:
            if not self.pending:
                await asyncio.sleep(2)
                continue
            query = """
                    INSERT INTO useravatars (user_id, avatar, first_seen)
                    SELECT x.user_id, x.avatar, x.first_seen
                    FROM JSONB_TO_RECORDSET($1::JSONB) as x(user_id BIGINT, avatar TEXT, first_seen TIMESTAMP)
                    """
            data = json.dumps(self.pending)
            await self.pool.execute(query, data)
            self.pending.clear()

    async def downloader(self):
        async def url_to_bytes(hash, url):
            if isinstance(url, tuple):
                retries = url[1] - 1
                url = url[0]
            else:
                retries = 5

            try:
                async with self.aiosession.get(str(url)) as r:
                    if r.status == 200:
                        await self.queue.put((hash, io.BytesIO(await r.read())))
                        return
                    if r.status in {403, 404}:
                        # Invalid url.
                        pass
                    elif r.status == 415:
                        # Avatar is too large. Retry with lower size.
                        url = URL(str(url))
                        new_size = int(url.query.get('size', 1024))//2
                        if new_size > 128:
                            # give up resizing it. Its too small to be worthwhile.
                            new_url = url.with_query(size=str(new_size))
                        else:
                            # could not find a gif size that did not throw 415, changing format to png.
                            new_url = url.with_path(url.path.replace('gif','png')).with_query(size=1024)
                        self.avatars[hash] = new_url
                    else:
                        # Put it back in for next round if there are retries left.
                        if retries:
                            self.avatars[hash] = (url, retries)
                    log.warning(f"downloading {url} failed with {r.status}")
            except (asyncio.TimeoutError, aiohttp.ClientError):
                log.warning(f"downloading {url} failed.")
                self.avatars[hash] = url
        try:
            while True:
                while len(self.avatars) == 0:
                    await asyncio.sleep(2)
                query = """
                    SELECT hash
                    FROM avatars
                    WHERE hash = ANY($1::TEXT[])
                    """
                to_check = list(self.avatars.keys())
                batch_size = 50000
                for i in range(0, len(to_check)):
                    results = await self.pool.fetch(query, to_check[i:i+batch_size])
                    for r in results:
                        # remove items in the avatar url dict that are already in the db
                        self.avatars.pop(r['hash'], None)

                chunk = dict()
                while len(self.avatars) > 0 and len(chunk) < (50 - self.queue.qsize()):
                    # grabs enough avatars to fill the posting queue with 50 avatars if possible
                    avy, url = self.avatars.popitem()
                    chunk[avy] = url
                if chunk:
                    await asyncio.gather(*[url_to_bytes(avy, url) for avy, url in chunk.items()])
                await asyncio.sleep(2)
        except asyncio.CancelledError:
            log.warning("avatar downloading task cancelled")


    async def batch_post_avatars(self):
        log.info('started avatar posting task')
        try:
            while True:
                if self.queue.qsize() == 0:
                    await asyncio.sleep(2)

                to_post = {}
                post_size = 0
                while len(to_post) < 10 and self.queue.qsize() > 0:
                    avy, file = await self.queue.get()
                    s = file.getbuffer().nbytes
                    if post_size + s < 8000000:
                        post_size += s
                        to_post[avy] = discord.File(file, filename=f'{avy}.{"png" if not avy.startswith("a_") else "gif"}')
                    elif s > 8000000:
                        new_bytes = None
                        if avy.startswith('a_'):
                            new_bytes = await self.loop.run_in_executor(None, images.extract_first_frame, file)
                        else:
                            new_bytes = await self.loop.run_in_executor(None, images.resize_to_limit, file, 8000000)
                        await self.queue.put((avy, new_bytes))
                        continue
                    else:
                        await self.queue.put((avy, file))
                        break
                if len(to_post) == 0:
                    continue

                backup = {k: io.BytesIO(v.fp.getbuffer()) for k, v in to_post.items()}

                for tries in range(5):
                    if tries > 0:
                        to_post = {k: discord.File(io.BytesIO(v.getbuffer()), filename=f'{k}.{"png" if not k.startswith("a_") else "gif"}') for k, v in backup.items()}
                    try:
                        message = await self.wh.send(content='\n'.join(to_post.keys()), wait=True, files=list(to_post.values()))
                        transformed = []
                        for a in message.attachments:
                            if a.height:
                                file_hash = os.path.splitext(a.filename)[0]
                                transformed.append(
                                    {
                                        "hash": file_hash,
                                        "url": a.url,
                                        "msgid": message.id,
                                        "id": a.id,
                                        "size": a.size,
                                        "height": a.height,
                                        "width": a.width
                                    }
                                )
                                backup.pop(file_hash)
                        query = '''
                            insert into avatars
                            (hash, url, msgid, id, size, height, width)
                            select x.hash, x.url, x.msgid, x.id, x.size, x.height, x.width
                            from jsonb_to_recordset($1::jsonb) as x(hash text, url text, msgid bigint, id bigint, size bigint, height bigint, width bigint)
                            on conflict (hash) do nothing
                        '''
                        await self.pool.execute(query, json.dumps(transformed))
                        if len(backup) == 0:
                            break
                        log.warning(f"{len(backup)} failed to upload. retrying")
                    except discord.HTTPException:
                        log.warning("HTTPException in on downloader")
                    except aiohttp.ClientError:
                        log.warning("Aiohttp client error in downloader")
                    except ValueError:
                        log.warning('Avatar file closed.')
                    except TypeError:
                        log.warning("Discord api returned nothing.")
                    except asyncio.TimeoutError:
                        log.warning("Webhook timed out.")
                    await asyncio.sleep(2 + 2 * tries)

        except asyncio.CancelledError:
            log.info("Avatar posting cancelled.")