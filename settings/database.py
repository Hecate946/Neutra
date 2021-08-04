import os
import json
import time
import asyncio
import asyncpg
import logging

from collections import defaultdict

from settings import constants
from utilities import utils

log = logging.getLogger("INFO_LOGGER")

scripts = [x[:-4] for x in sorted(os.listdir("./data/scripts")) if x.endswith(".sql")]
cxn = asyncio.get_event_loop().run_until_complete(
    asyncpg.create_pool(constants.postgres)
)

prefixes = dict()
settings = defaultdict(dict)


async def initialize(bot, members):
    await scriptexec()
    await set_config_id(bot)
    await load_prefixes()
    await update_db(bot.guilds, members)
    await load_settings()


async def set_config_id(bot):
    # Initialize the config table
    # with the bot's client ID.
    query = """
            INSERT INTO config
            VALUES ($1)
            ON CONFLICT (client_id)
            DO NOTHING;
            """
    await cxn.execute(query, bot.user.id)


async def scriptexec():
    # We execute the SQL script to make sure we have all our tables.
    for script in scripts:
        with open(f"./data/scripts/{script}.sql", "r", encoding="utf-8") as script:
            try:
                await cxn.execute(script.read())
            except Exception as e:
                print(utils.traceback_maker(e))


async def update_server(server, member_list):
    # Update a server when the bot joins.
    query = """
            INSERT INTO servers (server_id) VALUES ($1)
            ON CONFLICT DO NOTHING;
            """
    st = time.time()
    await cxn.execute(query, server.id)

    query = """
            INSERT INTO userstatus (user_id)
            VALUES ($1) ON CONFLICT DO NOTHING;
            """
    await cxn.executemany(
        query,
        ((m.id,) for m in member_list),
    )

    log.info(f"Server {server.name} Updated [{server.id}] Time: {time.time() - st}")


async def update_db(guilds, member_list):
    # Main database updater. This is mostly just for updating new servers and members that the bot joined when offline.
    query = """
            INSERT INTO servers (server_id) VALUES ($1)
            ON CONFLICT DO NOTHING;
            """
    st = time.time()
    await cxn.executemany(
        query,
        ((s.id,) for s in guilds),
    )

    query = """
            INSERT INTO userstatus (user_id)
            VALUES ($1) ON CONFLICT DO NOTHING;
            """
    await cxn.executemany(
        query,
        ((m.id,) for m in member_list),
    )
    log.info(f"Database Update: {time.time() - st}")


async def load_settings():
    query = """
            SELECT 
            servers.server_id,
            (SELECT ROW_TO_JSON(_) FROM (SELECT
                servers.muterole,
                servers.antiinvite,
                servers.reassign,
                servers.autoroles,
                servers.profanities
            ) AS _) AS settings
            FROM servers;
            """
    records = await cxn.fetch(query)
    if records:
        for record in records:
            settings[record["server_id"]].update(json.loads(record["settings"]))


async def fix_server(server):
    query = """
            SELECT 
            servers.server_id,
            (SELECT ROW_TO_JSON(_) FROM (SELECT
                servers.muterole,
                servers.antiinvite,
                servers.reassign,
                servers.autoroles,
                servers.profanities
            ) AS _) AS settings
            FROM servers
            WHERE server_id = $1;
            """
    record = await cxn.fetchrow(query, server)
    if record:
        settings[record["server_id"]].update(json.loads(record["settings"]))


async def load_prefixes():
    query = """
            SELECT server_id, ARRAY_REMOVE(ARRAY_AGG(prefix), NULL) as prefix_list
            FROM prefixes GROUP BY server_id;
            """
    records = await cxn.fetch(query)
    for server_id, prefix_list in records:
        prefixes[server_id] = prefix_list
