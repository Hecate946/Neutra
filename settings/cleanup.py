# Module for deleting useless entries in postgres
import logging

from . import database

log = logging.getLogger("INFO_LOGGER")

conn = database.cxn


async def basic_cleanup(guilds):
    query = "SELECT server_id FROM servers"
    await find_discrepancy(query, guilds)


async def find_discrepancy(query, guilds):
    server_list = [x.id for x in guilds]
    records = await conn.fetch(query)
    for record in records:
        server_id = record["server_id"]
        if server_id not in server_list:
            await destroy_server(server_id)


async def purge_discrepancies(guilds):
    print("Running purge_discrepancies(guilds)")
    query = "SELECT server_id FROM servers"
    await find_discrepancy(query, guilds)
    print(f"{query.split()[-1]}_query")

    query = "SELECT server_id FROM prefixes"
    await find_discrepancy(query, guilds)
    print(f"{query.split()[-1]}_query")

    query = "SELECT server_id FROM logs"
    await find_discrepancy(query, guilds)
    print(f"{query.split()[-1]}_query")

    query = "SELECT server_id FROM log_data"
    await find_discrepancy(query, guilds)
    print(f"{query.split()[-1]}_query")

    query = "SELECT server_id FROM warns"
    await find_discrepancy(query, guilds)
    print(f"{query.split()[-1]}_query")

    query = "SELECT server_id FROM invites"
    await find_discrepancy(query, guilds)
    print(f"{query.split()[-1]}_query")

    query = "SELECT server_id FROM emojistats"
    await find_discrepancy(query, guilds)
    print(f"{query.split()[-1]}_query")

    query = "SELECT server_id FROM messages"
    await find_discrepancy(query, guilds)
    print(f"{query.split()[-1]}_query")

    query = "SELECT server_id FROM usernicks"
    await find_discrepancy(query, guilds)
    print(f"{query.split()[-1]}_query")

    query = "SELECT server_id FROM userroles"
    await find_discrepancy(query, guilds)
    print(f"{query.split()[-1]}_query")


async def destroy_server(guild_id):
    """Delete all records of a server from the db"""

    query = "DELETE FROM servers WHERE server_id = $1"
    await conn.execute(query, guild_id)

    query = "DELETE FROM prefixes WHERE server_id = $1"
    await conn.execute(query, guild_id)

    query = "DELETE FROM warns WHERE server_id = $1"
    await conn.execute(query, guild_id)

    query = "DELETE FROM invites WHERE server_id = $1"
    await conn.execute(query, guild_id)

    query = "DELETE FROM emojistats WHERE server_id = $1"
    await conn.execute(query, guild_id)

    query = "DELETE FROM messages WHERE server_id = $1"
    await conn.execute(query, guild_id)

    query = "DELETE FROM usernicks WHERE server_id = $1"
    await conn.execute(query, guild_id)

    query = "DELETE FROM userroles WHERE server_id = $1"
    await conn.execute(query, guild_id)

    log.info(f"Destroyed server [{guild_id}]")
