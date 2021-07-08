import discord
import time
import io
from discord.ext import commands
from utilities import checks

from PIL import Image


def setup(bot):
    bot.add_cog(Testing(bot))


class Testing(commands.Cog):
    """
    A cog for testing features
    """

    def __init__(self, bot):
        self.bot = bot

    # Owner only cog.
    async def cog_check(self, ctx):
        return checks.is_owner(ctx)

    @commands.command()
    async def a(self, ctx, role: discord.Role):
        st = time.time()
        users = sum(1 for m in role.guild.members if m._roles.has(role.id))
        await ctx.send(str(time.time() - st))
        st = time.time()
        users = sum(1 for m in role.guild.members if role in m.roles)
        await ctx.send(str(time.time() - st))

    @commands.command()
    async def blah(self, ctx):
        from utilities import images

        query = """
                SELECT author_id, COUNT(*) FROM messages
                WHERE server_id = $1
                GROUP BY author_id
                ORDER BY count DESC
                LIMIT 5;
                """
        await ctx.trigger_typing()
        records = await self.bot.cxn.fetch(query, ctx.guild.id)
        data = {
            str(await self.bot.fetch_user(record["author_id"])): record["count"]
            for record in records
        }
        image = Image.new("RGBA", (len(data) * 200, 1000), (216, 183, 255))
        while max(data.values()) > 1000:
            data = {user: count // 2 for user, count in data.items()}
        for user, count in data.items():
            bar = images.get_bar(user, count)
            image.paste(im=bar, box=(list(data.values()).index(count) * 200, 0))

        buffer = io.BytesIO()
        image.save(buffer, "png")  # 'save' function for PIL
        buffer.seek(0)
        dfile = discord.File(fp=buffer, filename="mstats.png")
        em = discord.Embed(title="Message Stats", color=self.bot.constants.embed)
        em.set_image(url="attachment://mstats.png")
        await ctx.send_or_reply(embed=em, file=dfile)
