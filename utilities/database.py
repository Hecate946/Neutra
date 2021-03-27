import asyncio
import asyncpg
import aioredis
import sys
import os
import json
from colr import color

from secret import constants

from discord.ext import tasks

SCRIPTS   = [x[:-4] for x in sorted(os.listdir('./data/scripts')) if x.endswith('.sql')]

postgres  = asyncio.get_event_loop().run_until_complete(asyncpg.create_pool(constants.postgres))
# redis_cxn = asyncio.get_event_loop().run_until_complete(aioredis.create_pool(constants.redis))
# redis     = aioredis.Redis(redis_cxn)

settings = dict()

async def initialize(guilds, members):
    await scriptexec()
    await update_db(guilds, members)
    await set_settings()


async def scriptexec():
    # We execute the SQL script to make sure we have all our tables.
    SEPARATOR = '================================'
    for script in SCRIPTS:
        with open(f"data/scripts/{script}.sql", "r", encoding="utf-8") as script:
            try:
                await postgres.execute(script.read())
            except Exception as e:
                print(e)
    print(color(fore="#830083", text=SEPARATOR))
    print(color(fore="#830083", text=f"Established Database Connection."))
    print(color(fore="#830083", text=SEPARATOR))


async def update_db(guilds, member_list):
    # Main database updater. This is mostly just for updating new servers and members that the bot joined when offline.
    await postgres.executemany("""
    INSERT INTO servers VALUES ($1, $2, $3)
    ON CONFLICT DO NOTHING""", 
    ((server.id, server.name, server.owner.id)
    for server in guilds))


    await postgres.executemany("""INSERT INTO roleconfig (server_id, autoroles, reassign) VALUES ($1, $2, $3)
    ON CONFLICT (server_id) DO NOTHING""",
    ((server.id, None, True)
    for server in guilds))


    await postgres.executemany("""INSERT INTO logging VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
    ON CONFLICT (server_id) DO NOTHING""",
    ((server.id, True, True, True, True, True, True, True, True, True, True, None, None)
    for server in guilds))


    await postgres.executemany("""INSERT INTO moderation VALUES ($1, $2, $3)
    ON CONFLICT (server_id) DO NOTHING""", 
    ((server.id, False, None)
    for server in guilds))

    await postgres.executemany("""INSERT INTO useravatars VALUES ($1, $2)
    ON CONFLICT (user_id) DO NOTHING""",
    ((member.id, str(member.avatar_url)) for member in member_list))


    await postgres.executemany("""INSERT INTO usernames VALUES ($1, $2) 
    ON CONFLICT (user_id) DO NOTHING""",
    ((member.id, str(member)) for member in member_list))


    await postgres.executemany("""INSERT INTO nicknames VALUES ($1, $2, $3, $4) 
    ON CONFLICT (serveruser) DO NOTHING""",
    ((f"{member.guild.id}:{member.id}", member.id, member.guild.id, member.display_name) for member in member_list))


    await postgres.executemany("""INSERT INTO userroles VALUES ($1, $2, $3, $4) 
    ON CONFLICT (serveruser) DO NOTHING""",
    ((
        f"{member.guild.id}:{member.id}",
        member.id,
        member.guild.id,
        ",".join(str(x.id) for x in member.roles)
        ) for member in member_list
    ))

    
async def set_settings():
    query = '''SELECT (server_id, prefix, antiinvite, logchannel, filter_bool) FROM servers'''
    result = await postgres.fetch(query)

    for x in result:
        server_id = x[0][0]
        prefix = x[0][1]
        antiinvite = x[0][2]
        logchannel = x[0][3]
        filter_bool = x[0][4]
        settings[server_id] = {
            "prefix": prefix,
            "antiinvite": antiinvite,
            "logchannel": logchannel,
            "filter_bool": filter_bool,
        }
    
    # with open('./json/settings.json', 'w') as prefix_json:
    #     json.dump(settings, prefix_json, indent=2)
    

async def fetch_prefix(server):
    try:
        prefix = settings[server]['prefix']
    except KeyError:
        query = '''SELECT prefix FROM servers WHERE server_id = $1'''
        record = await postgres.fetchrow(query, server)
        prefix = record[0]
        settings[server]['prefix'] = prefix
    return settings[server]['prefix']








""" class Redis:
    def __init__(self):
        self.postgres = postgres
        self.redis = redis

    async def set_prefixes(self):
        all_prefixes = await Postgres.prefixes()
        for server_id in all_prefixes:
            await self.redis.hset('prefixes', server_id, all_prefixes[server_id]['prefix'])

    async def get_prefixes(self, server_id):
        byte_prefix = await self.redis.hget('prefixes', server_id)
        prefix = byte_prefix.decode('utf-8')
        return prefix """
