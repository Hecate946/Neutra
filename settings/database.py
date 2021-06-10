import os
import time
import asyncio
import asyncpg
import logging

from colr import color

from settings import constants

info_logger = logging.getLogger("INFO_LOGGER")
scripts = [x[:-4] for x in sorted(os.listdir("./data/scripts")) if x.endswith(".sql")]
postgres = asyncio.get_event_loop().run_until_complete(
    asyncpg.create_pool(constants.postgres)
)

prefixes = dict()
settings = dict()
bot_settings = dict()
config = dict()


async def initialize(bot, members):
    await scriptexec()
    await set_config_id(bot)
    await load_prefixes()
    await update_db(bot.guilds, members)
    await load_settings()


SEPARATOR = "=" * 33


async def set_config_id(bot):
    # Initialize the config table
    # with the bot's client ID.
    query = """
            INSERT INTO config
            VALUES ($1)
            ON CONFLICT (client_id)
            DO NOTHING;
            """
    await postgres.execute(query, bot.user.id)


async def scriptexec():
    # We execute the SQL script to make sure we have all our tables.
    st = time.time()
    for script in scripts:
        with open(f"./data/scripts/{script}.sql", "r", encoding="utf-8") as script:
            try:
                await postgres.execute(script.read())
            except Exception as e:
                print(e)
    print(
        color(
            fore="#46648F", text=f"Script   execution : {str(time.time() - st)[:10]} s"
        )
    )


async def update_server(server, member_list):
    # Update a server when the bot joins.
    st = time.time()
    await postgres.execute(
        """
    INSERT INTO servers(server_id, server_name, owner_id) VALUES ($1, $2, $3)
    ON CONFLICT DO NOTHING""",
        server.id,
        server.name,
        server.owner.id,
    )
    print(
        color(fore="#46648F", text=f"Server insertion : {str(time.time() - st)[:10]} s")
    )

    st = time.time()
    query = """
            INSERT INTO userstatus (user_id)
            VALUES ($1) ON CONFLICT DO NOTHING;
            """
    await postgres.executemany(
        query,
        ((member.id,) for member in member_list),
    )
    print(
        color(
            fore="#46648F", text=f"Status   insertion : {str(time.time() - st)[:10]} s"
        )
    )


async def update_db(guilds, member_list):
    # Main database updater. This is mostly just for updating new servers and members that the bot joined when offline.
    st = time.time()
    await postgres.executemany(
        """
    INSERT INTO servers(server_id, server_name, owner_id) VALUES ($1, $2, $3)
    ON CONFLICT DO NOTHING""",
        ((server.id, server.name, server.owner.id) for server in guilds),
    )
    print(
        color(
            fore="#46648F", text=f"Servers  insertion : {str(time.time() - st)[:10]} s"
        )
    )

    st = time.time()
    query = """
            INSERT INTO userstatus (user_id)
            VALUES ($1) ON CONFLICT DO NOTHING;
            """
    await postgres.executemany(
        query,
        ((member.id,) for member in member_list),
    )
    print(
        color(
            fore="#46648F", text=f"Status   insertion : {str(time.time() - st)[:10]} s"
        )
    )
    print(color(fore="#46648F", text=SEPARATOR))


async def load_settings():
    query = """SELECT (server_id, prefix, profanities, autoroles, antiinvite, reassign, disabled_commands, admin_allow, react) FROM servers"""
    results = await postgres.fetch(query)

    # load everything from the servers table
    for x in results:
        server_id = x[0][0]
        prefix = x[0][1]
        profanities = x[0][2]
        autoroles = x[0][3]
        antiinvite = x[0][4]
        reassign = x[0][5]
        disabled_commands = x[0][6]
        admin_allow = x[0][7]
        react = x[0][8]

        if disabled_commands is None:
            disabled_commands = []
        else:
            disabled_commands = [x for x in disabled_commands.split(",")]

        if profanities is None:
            profanities = []
        else:
            profanities = [x for x in profanities.split(",")]

        if autoroles is None:
            autoroles = []
        else:
            autoroles = [x for x in autoroles.split(",")]

        settings[server_id] = {
            "prefixes": [],
            "profanities": profanities,
            "disabled_commands": disabled_commands,
            "admin_allow": admin_allow,
            "react": react,
            "autoroles": autoroles,
            "antiinvite": antiinvite,
            "reassign": reassign,
            "logging": {},
        }

    # load the prefixes
    query = """
            SELECT server_id, array_agg(prefix) as prefix_list
            FROM prefixes GROUP BY server_id;
            """
    all_prefixes = await postgres.fetch(query)
    for x in all_prefixes:
        server_id = x[0]
        prefixes = x[1]

        settings[server_id]["prefixes"] = prefixes


async def fix_server(server):
    query = """ SELECT (
                  server_id,
                  prefix,
                  profanities,
                  autoroles,
                  antiinvite,
                  reassign,
                  disabled_commands,
                  admin_allow,
                  react
                )
                FROM servers
                WHERE server_id = $1;
            """
    results = await postgres.fetch(query, server)

    # load everything from the servers table
    for x in results:
        server_id = x[0][0]
        prefix = x[0][1]
        profanities = x[0][2]
        autoroles = x[0][3]
        antiinvite = x[0][4]
        reassign = x[0][5]
        disabled_commands = x[0][6]
        admin_allow = x[0][7]
        react = x[0][8]

        if disabled_commands is None:
            disabled_commands = []
        else:
            disabled_commands = [x for x in disabled_commands.split(",")]

        if profanities is None:
            profanities = []
        else:
            profanities = [x for x in profanities.split(",")]

        if autoroles is None:
            autoroles = []
        else:
            autoroles = [x for x in autoroles.split(",")]

        settings[server_id] = {
            "prefixes": [],
            "profanities": profanities,
            "disabled_commands": disabled_commands,
            "admin_allow": admin_allow,
            "react": react,
            "autoroles": autoroles,
            "antiinvite": antiinvite,
            "reassign": reassign,
        }

    # load the prefixes
    query = """
            SELECT server_id, array_agg(prefix) as prefix_list
            FROM prefixes WHERE server_id = $1 GROUP BY server_id;
            """
    all_prefixes = await postgres.fetchrow(query, server)
    try:
        server_id = all_prefixes[0]
        prefixes = all_prefixes[1]

        settings[server_id]["prefixes"] = prefixes
    except TypeError:  # No custom prefixes, must be new server
        pass


async def load_prefixes():
    query = """
            SELECT server_id, ARRAY_REMOVE(ARRAY_AGG(prefix), NULL) as prefix_list
            FROM prefixes GROUP BY server_id;
            """
    records = await postgres.fetch(query)
    for server_id, prefix_list in records:
        prefixes[server_id] = prefix_list
