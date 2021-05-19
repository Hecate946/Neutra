import discord
from discord.ext import commands
from utilities import decorators

def setup(bot):
    bot.add_cog(Testing(bot))


class Testing(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    
    @decorators.command()
    async def prompt(self, ctx):
        boolean = await ctx.confirm("\:thinking:")
        if boolean:
            await ctx.send("PEPELAUGH")
            return
        await ctx.send("pepesad")