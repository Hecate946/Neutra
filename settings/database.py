import os
import asyncio
import asyncpg
import logging

from colr import color
from colr.colr import disabled

from settings import constants
from utilities import utils

info_logger = logging.getLogger("INFO_LOGGER")
scripts = [x[:-4] for x in sorted(os.listdir("./data/scripts")) if x.endswith(".sql")]
postgres = asyncio.get_event_loop().run_until_complete(
    asyncpg.create_pool(constants.postgres)
)
settings = dict()
bot_settings = dict()


async def initialize(guilds, members):
    await scriptexec()
    await update_db(guilds, members)
    await load_settings()
#     await load_prefixes(guilds)


# async def load_prefixes(guilds):
#     query = """
#             SELECT prefix
#             FROM prefixes
#             WHERE server_id = $1;
#             """
#     for guild in guilds:
#         all_prefixes = await postgres.fetch(query, guild.id)
#         prefixes = settings[guild.id]["prefixes"] = []
#         for x in all_prefixes:
#             prefixes.append(x[0])

async def scriptexec():
    # We execute the SQL script to make sure we have all our tables.
    SEPARATOR = "================================"
    for script in scripts:
        with open(f"data/scripts/{script}.sql", "r", encoding="utf-8") as script:
            try:
                await postgres.execute(script.read())
            except Exception as e:
                print(e)
    print(color(fore="#830083", text=SEPARATOR))
    print(color(fore="#830083", text=f"Established Database Connection."))
    print(color(fore="#830083", text=SEPARATOR))


async def update_server(server, member_list):
    # Main database updater. This is mostly just for updating new servers and members that the bot joined when offline.
    await postgres.execute(
        """
    INSERT INTO servers(server_id, server_name, owner_id) VALUES ($1, $2, $3)
    ON CONFLICT DO NOTHING""",
        server.id,
        server.name,
        server.owner.id,
    )

    # await postgres.execute(
    #     """
    # INSERT INTO prefixes(server_id, prefix) VALUES ($1, $2)
    # ON CONFLICT DO NOTHING""",
    #     server.id,
    #     f"<@!{constants.client}>"
    # )

    await postgres.execute(
        """INSERT INTO logging (server_id, logchannel) VALUES ($1, $2)
    ON CONFLICT (server_id) DO NOTHING""",
        server.id,
        None,
    )

    await postgres.executemany(
        """INSERT INTO usernames VALUES ($1, $2) 
    ON CONFLICT (user_id) DO NOTHING""",
        ((member.id, str(member)) for member in member_list),
    )

    await postgres.executemany(
        """INSERT INTO nicknames VALUES ($1, $2, $3, $4) 
    ON CONFLICT (serveruser) DO NOTHING""",
        (
            (
                f"{member.guild.id}:{member.id}",
                member.id,
                member.guild.id,
                member.display_name,
            )
            for member in member_list
        ),
    )

    await postgres.executemany(
        """INSERT INTO userroles VALUES ($1, $2, $3, $4)
    ON CONFLICT (serveruser) DO NOTHING""",
        (
            (
                f"{member.guild.id}:{member.id}",
                member.id,
                member.guild.id,
                ",".join(str(x.id) for x in member.roles),
            )
            for member in member_list
        ),
    )


async def update_db(guilds, member_list):
    # Main database updater. This is mostly just for updating new servers and members that the bot joined when offline.
    await postgres.executemany(
        """
    INSERT INTO servers(server_id, server_name, owner_id) VALUES ($1, $2, $3)
    ON CONFLICT DO NOTHING""",
        ((server.id, server.name, server.owner.id) for server in guilds),
    )

    # await postgres.executemany(
    #     """
    # INSERT INTO prefixes(server_id, prefix) VALUES ($1, $2)
    # ON CONFLICT DO NOTHING""",
    #     ((server.id, f"<@!{constants.client}>") for server in guilds),
    # )

    await postgres.executemany(
        """INSERT INTO logging (server_id, logchannel) VALUES ($1, $2)
    ON CONFLICT (server_id) DO NOTHING""",
        ((server.id, None) for server in guilds),
    )

    # await postgres.executemany("""INSERT INTO useravatars VALUES ($1, $2)
    # ON CONFLICT (user_id) DO NOTHING""",
    # ((member.id, str(member.avatar_url)) for member in member_list))

    await postgres.executemany(
        """INSERT INTO usernames VALUES ($1, $2) 
    ON CONFLICT (user_id) DO NOTHING""",
        ((member.id, str(member)) for member in member_list),
    )

    await postgres.executemany(
        """INSERT INTO nicknames VALUES ($1, $2, $3, $4) 
    ON CONFLICT (serveruser) DO NOTHING""",
        (
            (
                f"{member.guild.id}:{member.id}",
                member.id,
                member.guild.id,
                member.display_name,
            )
            for member in member_list
        ),
    )

    await postgres.executemany(
        """INSERT INTO userroles VALUES ($1, $2, $3, $4) 
    ON CONFLICT (serveruser) DO NOTHING""",
        (
            (
                f"{member.guild.id}:{member.id}",
                member.id,
                member.guild.id,
                ",".join(str(x.id) for x in member.roles),
            )
            for member in member_list
        ),
    )


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
            "prefix": prefix,
            "prefixes": [],
            "profanities": profanities,
            "disabled_commands": disabled_commands,
            "admin_allow": admin_allow,
            "react": react,
            "autoroles": autoroles,
            "antiinvite": antiinvite,
            "reassign": reassign,
            "ignored_users": {},
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


    # Load the ignored users
    query = """SELECT (server_id, user_id, react) FROM ignored;"""
    results = await postgres.fetch(query)

    if results == []:
        pass
    for x in results:
        server_id = x[0][0]
        user_id = x[0][1]
        react = x[0][2]

        settings[server_id]["ignored_users"][user_id] = react

    # Load the logging configuration

    query = """SELECT * FROM logging;"""
    results = await postgres.fetch(query)

    if results == []:
        pass
    for x in results:
        server_id = x[0]
        message_edits = x[1]
        message_deletions = x[2]
        role_changes = x[3]
        channel_updates = x[4]
        name_updates = x[5]
        voice_state_updates = x[6]
        avatar_changes = x[7]
        bans = x[8]
        leaves = x[9]
        joins = x[10]
        ignored_channels = x[11]
        logchannel = x[12]
        webhook_id = x[13]

        if ignored_channels is None:
            ignored_channels = []
        else:
            ignored_channels = [x for x in ignored_channels.split(",")]

        settings[server_id]["logging"]["message_edits"] = message_edits
        settings[server_id]["logging"]["message_deletions"] = message_deletions
        settings[server_id]["logging"]["role_changes"] = role_changes
        settings[server_id]["logging"]["channel_updates"] = channel_updates
        settings[server_id]["logging"]["name_updates"] = name_updates
        settings[server_id]["logging"]["voice_state_updates"] = voice_state_updates
        settings[server_id]["logging"]["avatar_changes"] = avatar_changes
        settings[server_id]["logging"]["bans"] = bans
        settings[server_id]["logging"]["leaves"] = leaves
        settings[server_id]["logging"]["joins"] = joins
        settings[server_id]["logging"]["ignored_channels"] = ignored_channels
        settings[server_id]["logging"]["logchannel"] = logchannel
        settings[server_id]["logging"]["webhook_id"] = webhook_id


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
            "prefix": prefix,
            "prefixes": [],
            "profanities": profanities,
            "disabled_commands": disabled_commands,
            "admin_allow": admin_allow,
            "react": react,
            "autoroles": autoroles,
            "antiinvite": antiinvite,
            "reassign": reassign,
            "ignored_users": {},
            "logging": {},
        }

    # load the prefixes
    query = """
            SELECT server_id, array_agg(prefix) as prefix_list
            FROM prefixes WHERE server_id = $1 GROUP BY server_id;
            """
    all_prefixes = await postgres.fetchrow(query, server)
    if all_prefixes is None:
        pass

    server_id = all_prefixes[0]
    prefixes = all_prefixes[1]

    settings[server_id]["prefixes"] = prefixes

    # Load the ignored users
    query = """SELECT (server_id, user_id, react) FROM ignored WHERE server_id = $1;"""
    results = await postgres.fetch(query, server)

    if results == []:
        pass
    for x in results:
        server_id = x[0][0]
        user_id = x[0][1]
        react = x[0][2]

        settings[server_id]["ignored_users"][user_id] = react

    # Load the logging configuration
    query = """SELECT * FROM logging WHERE server_id = $1;"""
    results = await postgres.fetch(query, server)

    if results == []:
        pass
    for x in results:
        server_id = x[0]
        message_edits = x[1]
        message_deletions = x[2]
        role_changes = x[3]
        channel_updates = x[4]
        name_updates = x[5]
        voice_state_updates = x[6]
        avatar_changes = x[7]
        bans = x[8]
        leaves = x[9]
        joins = x[10]
        ignored_channels = x[11]
        logchannel = x[12]
        webhook_id = x[13]

        if ignored_channels is None:
            ignored_channels = []
        else:
            ignored_channels = [x for x in ignored_channels.split(",")]

        settings[server_id]["logging"]["message_edits"] = message_edits
        settings[server_id]["logging"]["message_deletions"] = message_deletions
        settings[server_id]["logging"]["role_changes"] = role_changes
        settings[server_id]["logging"]["channel_updates"] = channel_updates
        settings[server_id]["logging"]["name_updates"] = name_updates
        settings[server_id]["logging"]["voice_state_updates"] = voice_state_updates
        settings[server_id]["logging"]["avatar_changes"] = avatar_changes
        settings[server_id]["logging"]["bans"] = bans
        settings[server_id]["logging"]["leaves"] = leaves
        settings[server_id]["logging"]["joins"] = joins
        settings[server_id]["logging"]["ignored_channels"] = ignored_channels
        settings[server_id]["logging"]["logchannel"] = logchannel
        settings[server_id]["logging"]["webhook_id"] = webhook_id


async def fetch_prefix(server):
    try:
        prefixes = settings[server]["prefixes"]
    except KeyError:
        return []
    return prefixes
