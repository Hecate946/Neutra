from utilities import default
from lib.bot import bot
from lib.db import asyncdb as db

VERSION = default.config()["version"]

owners = default.config()["owners"]

@bot.command()
async def droptable(ctx):
    if ctx.author.id not in owners: return
    await ctx.send(f"Dropping table")
    await db.execute("""
    DELETE FROM messages
    """)
    await ctx.send("Table has been dropped")

bot.run(VERSION)
