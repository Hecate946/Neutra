import asyncio
from . import asyncdb as db


async def run_build():
    await db.build()

build_loop = asyncio.get_event_loop()
build_loop.run_until_complete(db.build())