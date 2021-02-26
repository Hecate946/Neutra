import asyncio
from os.path import isfile
from aiosqlite import connect


DB_PATH = "./data/db/database.db"
BUILD_PATH = "./data/db/build.sql"


async def connection():
    return await connect(DB_PATH)


connection_loop = asyncio.get_event_loop()
cxn = connection_loop.run_until_complete(connection())


separator = '=' * len(str(cxn))
print(separator)
print(cxn)
print(separator)

def with_commit(func):
    async def inner(*args, **kwargs):
        await func(*args, **kwargs)
        await commit()

    return  inner


@with_commit
async def build():
    if isfile(BUILD_PATH):
        await scriptexec(BUILD_PATH)


async def commit():
    await cxn.commit()


async def close():
    await cxn.close()


async def field(command, *values):
    cur = await cxn.cursor()
    await cur.execute(command, tuple(values))


    if (fetch := await cur.fetchone()) is not None:
        return fetch[0]


async def record(command, *values):
    cur = await cxn.cursor()
    await cur.execute(command, tuple(values))

    return await cur.fetchone()

async def records(command, *values):
    cur = await cxn.cursor()
    await cur.execute(command, tuple(values))

    return await cur.fetchall()

async def column(command, *values):
    cur = await cxn.cursor()
    await cur.execute(command, tuple(values))

    return [item[0] for item in  await cur.fetchall()]
    
async def execute(command, *values):
    cur = await cxn.cursor()
    await cur.execute(command, tuple(values))

async def multiexec(command, valueset):
    cur = await cxn.cursor()
    await cur.executemany(command, valueset)

async def scriptexec(path):
    with open(path, "r", encoding="utf-8") as script:
        cur = await cxn.cursor()
        await cur.executescript(script.read())
