# Module for deleting useless entries in both postgres and possibly redis in the future
import logging
from . import database

log = logging.getLogger("INFO_LOGGER")

conn = database.postgres


async def cleanup_servers(guilds):
    server_list = []
    for server in guilds:
        server_list.append(server.id)

    query = '''SELECT (server_id, server_name) FROM servers;'''
    servers = await conn.fetch(query)
    for x in servers:
        if x[0][0] not in server_list:
            await destroy_server(x[0][0], x[0][1])


async def destroy_server(guild_id, guild_name):
    await conn.execute("""
    DELETE FROM servers WHERE server_id = $1
    """, guild_id)

    await conn.execute("""
    DELETE FROM userroles WHERE server_id = $1
    """, guild_id)

    await conn.execute("""
    DELETE FROM nicknames WHERE server_id = $1
    """, guild_id)

    await conn.execute("""
    DELETE FROM roleconfig WHERE server_id = $1
    """, guild_id)

    await conn.execute("""
    DELETE FROM mutes WHERE server_id = $1
    """, guild_id)

    await conn.execute("""
    DELETE FROM logging WHERE server_id = $1
    """, guild_id)

    await conn.execute("""
    DELETE FROM lockedchannels WHERE server_id = $1
    """, guild_id)

    await conn.execute("""
    DELETE FROM warn WHERE server_id = $1
    """, guild_id)

    await conn.execute("""
    DELETE FROM messages WHERE server_id = $1
    """, guild_id)

    await conn.execute("""
    DELETE FROM ignored WHERE server_id = $1
    """, guild_id)

    await conn.execute("""
    DELETE FROM snipe WHERE server_id = $1
    """, guild_id)

    await conn.execute("""
    DELETE FROM profanity WHERE server_id = $1
    """, guild_id)

    await conn.execute("""
    DELETE FROM moderation WHERE server_id = $1
    """, guild_id)

    log.info("Successfully destroyed server [{0}] Name: ({1})".format(guild_id, guild_name))
    

