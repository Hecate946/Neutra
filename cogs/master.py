import discord
import os
from discord.ext import commands, menus

from utilities import pagination, permissions
from core import bot
def setup(bot):
    bot.add_cog(Master(bot))
def checker():
    return True
class Master(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        if not os.path.exists('./data/txts'):
            os.mkdir('./data/txts')

        self.todo = './data/txts/todo.txt'

    async def cog_check(self, ctx):
        print(super().cog_check(ctx))
        return super().cog_check(ctx)

    @commands.group(case_insensitive=True, aliases=['to-do'], invoke_without_subcommand=True)
    async def todo(self, ctx):
        if ctx.invoked_subcommand is None:
            with open(self.todo) as fp:
                data = fp.read()
            p = pagination.MainMenu(pagination.TextPageSource(data, prefix="```prolog\n"))
            try:
                await p.start(ctx)
            except menus.MenuError as e:
                await ctx.send(e)

    @todo.command()
    async def add(self, ctx, *, todo = None):
        if todo is None:
            return await ctx.send(f"Usage: `{ctx.prefix}todo add <todo>`")
        with open(self.todo, "a", encoding="utf=8") as fp:
            fp.write(todo + "\n")
        await ctx.send(f"Done")



    
