import os
import json
import time
import logging

from collections import defaultdict
from utilities import utils

log = logging.getLogger("INFO_LOGGER")


class Database:
    def __init__(self, cxn):
        self.cxn = cxn

        self.prefixes = {}
        self.settings = defaultdict(dict)
        self.scripts = [
            x[:-4] for x in sorted(os.listdir("./data/scripts")) if x.endswith(".sql")
        ]

    async def initialize(self, bot, members):
        await self.scriptexec()
        await self.set_config_id(bot)
        await self.load_prefixes()
        await self.update_db(bot.guilds, members)
        await self.load_settings()

    async def set_config_id(self, bot):
        # Initialize the config table
        # with the bot's client ID.
        query = """
                INSERT INTO config
                VALUES ($1)
                ON CONFLICT (client_id)
                DO NOTHING;
                """
        await self.cxn.execute(query, bot.user.id)

    async def scriptexec(self):
        # We execute the SQL script to make sure we have all our tables.
        for script in self.scripts:
            with open(f"./data/scripts/{script}.sql", "r", encoding="utf-8") as script:
                try:
                    await self.cxn.execute(script.read())
                except Exception as e:
                    print(utils.traceback_maker(e))

    async def update_server(self, server, member_list):
        # Update a server when the bot joins.
        query = """
                INSERT INTO servers (server_id) VALUES ($1)
                ON CONFLICT DO NOTHING;
                """
        st = time.time()
        await self.cxn.execute(query, server.id)

        query = """
                INSERT INTO userstatus (user_id)
                VALUES ($1) ON CONFLICT DO NOTHING;
                """
        await self.cxn.executemany(
            query,
            ((m.id,) for m in member_list),
        )

        log.info(f"Server {server.name} Updated [{server.id}] Time: {time.time() - st}")

    async def update_db(self, guilds, member_list):
        # Main database updater. This is mostly just for updating new servers and members that the bot joined when offline.
        query = """
                INSERT INTO servers (server_id) VALUES ($1)
                ON CONFLICT DO NOTHING;
                """
        st = time.time()
        await self.cxn.executemany(
            query,
            ((s.id,) for s in guilds),
        )

        query = """
                INSERT INTO userstatus (user_id)
                VALUES ($1) ON CONFLICT DO NOTHING;
                """
        await self.cxn.executemany(
            query,
            ((m.id,) for m in member_list),
        )
        log.info(f"Database Update: {time.time() - st}")

    async def load_settings(self):
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
        records = await self.cxn.fetch(query)
        if records:
            for record in records:
                self.settings[record["server_id"]].update(
                    json.loads(record["settings"])
                )

    async def fix_server(self, server):
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
        record = await self.cxn.fetchrow(query, server)
        if record:
            self.settings[record["server_id"]].update(json.loads(record["settings"]))

    async def load_prefixes(self):
        query = """
                SELECT server_id, ARRAY_REMOVE(ARRAY_AGG(prefix), NULL) as prefix_list
                FROM prefixes GROUP BY server_id;
                """
        records = await self.cxn.fetch(query)
        for server_id, prefix_list in records:
            self.prefixes[server_id] = prefix_list

    async def basic_cleanup(self, guilds):
        query = "SELECT server_id FROM servers"
        await self.find_discrepancy(query, guilds)

    async def find_discrepancy(self, query, guilds):
        server_list = [x.id for x in guilds]
        records = await self.cxn.fetch(query)
        for record in records:
            server_id = record["server_id"]
            if server_id not in server_list:
                await self.destroy_server(server_id)

    async def purge_discrepancies(self, guilds):
        print("Running purge_discrepancies(guilds)")
        query = "SELECT server_id FROM servers"
        await self.find_discrepancy(query, guilds)
        print(f"{query.split()[-1]}_query")

        query = "SELECT server_id FROM prefixes"
        await self.find_discrepancy(query, guilds)
        print(f"{query.split()[-1]}_query")

        query = "SELECT server_id FROM logs"
        await self.find_discrepancy(query, guilds)
        print(f"{query.split()[-1]}_query")

        query = "SELECT server_id FROM log_data"
        await self.find_discrepancy(query, guilds)
        print(f"{query.split()[-1]}_query")

        query = "SELECT server_id FROM warns"
        await self.find_discrepancy(query, guilds)
        print(f"{query.split()[-1]}_query")

        query = "SELECT server_id FROM invites"
        await self.find_discrepancy(query, guilds)
        print(f"{query.split()[-1]}_query")

        query = "SELECT server_id FROM emojidata"
        await self.find_discrepancy(query, guilds)
        print(f"{query.split()[-1]}_query")

        query = "SELECT server_id FROM messages"
        await self.find_discrepancy(query, guilds)
        print(f"{query.split()[-1]}_query")

        query = "SELECT server_id FROM usernicks"
        await self.find_discrepancy(query, guilds)
        print(f"{query.split()[-1]}_query")

        query = "SELECT server_id FROM userroles"
        await self.find_discrepancy(query, guilds)
        print(f"{query.split()[-1]}_query")

    async def destroy_server(self, guild_id):
        """Delete all records of a server from the db"""

        query = "DELETE FROM servers WHERE server_id = $1"
        await self.cxn.execute(query, guild_id)

        query = "DELETE FROM prefixes WHERE server_id = $1"
        await self.cxn.execute(query, guild_id)

        query = "DELETE FROM warns WHERE server_id = $1"
        await self.cxn.execute(query, guild_id)

        query = "DELETE FROM invites WHERE server_id = $1"
        await self.cxn.execute(query, guild_id)

        query = "DELETE FROM emojidata WHERE server_id = $1"
        await self.cxn.execute(query, guild_id)

        query = "DELETE FROM messages WHERE server_id = $1"
        await self.cxn.execute(query, guild_id)

        query = "DELETE FROM usernicks WHERE server_id = $1"
        await self.cxn.execute(query, guild_id)

        query = "DELETE FROM userroles WHERE server_id = $1"
        await self.cxn.execute(query, guild_id)

        log.info(f"Destroyed server [{guild_id}]")
