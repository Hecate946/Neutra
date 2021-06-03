import discord
import time
from discord.ext import commands, tasks
from dislash.interactions import *
from dislash.slash_commands import *
import json
from utilities import decorators
from utilities import utils


def setup(bot):
    bot.add_cog(Testing(bot))
    slash = SlashClient(bot)

class Testing(commands.Cog):
    """
    A cog for testing features
    """
    def __init__(self, bot):
        self.bot = bot
        self.avs = []

    @decorators.command()
    async def test(self, ctx):
        try:
            utils.blahblah
        except Exception as e:
            self.bot.dispatch("error", "my shit", tb=utils.traceback_maker(e))

    @decorators.command()
    async def archive(self, ctx):
        #await self.insertion()
        query = """
                SELECT user_id, avatar
                FROM testavs LIMIT 1;
                """
        record = await self.bot.cxn.fetchrow(query)
        print(record)
        await ctx.send_or_reply(f"https://img.discord.wf/avatars/{record['user_id']}/{record['avatar']}.png?size=1024")


    async def insertion(self):
        query = """
                INSERT INTO testavs (user_id, avatar)
                SELECT x.user_id, x.avatar
                FROM JSONB_TO_RECORDSET($1::JSONB)
                AS x(user_id BIGINT, avatar TEXT);
                """
        for user in self.bot.users:
            async with self.bot.session.get(f"https://img.discord.wf/avatars/{user.id}/{user.avatar}.png") as resp:
                print(resp.content)
            self.avs.append({
                "user_id": user.id,
                "avatar": user.avatar,
            })

        data = json.dumps(self.avs)
        await self.bot.cxn.execute(query, data)

        print("completed")

    @commands.command()
    async def w(self, ctx):

        # Send a message with buttons
        await ctx.buttons("This message has buttons!")

    @commands.command()
    async def a(self, ctx, role:discord.Role):
        st = time.time()
        users = sum(1 for m in role.guild.members if m._roles.has(role.id))
        await ctx.send(str(time.time() - st))
        st = time.time()
        users = sum(1 for m in role.guild.members if role in m.roles)
        await ctx.send(str(time.time() - st))