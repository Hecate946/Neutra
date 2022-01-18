import os
import aiohttp
import asyncio
import asyncpg

from config import POSTGRES


class Client:
    def __init__(self):
        self.loop = asyncio.get_event_loop()
        asyncio.set_event_loop(self.loop)

        self.scripts = [
            x[:-4] for x in os.listdir("./data/scripts") if x.endswith(".sql")
        ]
        self.session = aiohttp.ClientSession(loop=self.loop)
        self.cxn = self.loop.run_until_complete(asyncpg.create_pool(POSTGRES.uri))

        self.loop.run_until_complete(self.scriptexec())

    async def scriptexec(self):
        # We execute the SQL scripts to make sure we have all our tables.
        for script in self.scripts:
            with open(f"./data/scripts/{script}.sql", "r", encoding="utf-8") as script:
                await self.cxn.execute(script.read())

    ##############################
    ## Aiohttp Helper Functions ##
    ##############################

    async def query(self, url, method="get", res_method="json", *args, **kwargs):
        async with getattr(self.session, method.lower())(url, *args, **kwargs) as res:
            if res_method:
                return await getattr(res, res_method)()

    async def get(self, url, *args, **kwargs):
        return await self.query(url, "get", *args, **kwargs)

    async def post(self, url, *args, **kwargs):
        return await self.query(url, "post", *args, **kwargs)

    async def put(self, url, *args, **kwargs):
        return await self.query(url, "put", *args, **kwargs)

    async def patch(self, url, *args, **kwargs):
        return await self.query(url, "patch", *args, **kwargs)


client = Client()
