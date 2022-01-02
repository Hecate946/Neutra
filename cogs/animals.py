import csv
import discord
import random

from discord.ext import commands

from utilities import checks
from utilities import decorators


async def read_shuffle_and_send(animal, ctx):
    """Rewrote wuacks shitty code but yeah thanks anyways wuack"""
    with open(f"./data/csvs/{animal}_url.csv", "r") as f:
        urls = list(csv.reader(f))

    embed = discord.Embed(
        title=f"{animal.capitalize()}!", color=ctx.bot.constants.embed
    )
    embed.set_image(url=random.choice(urls)[0])
    await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Animals(bot))


class Animals(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @decorators.command(
        brief="Random picture of a cat",
        aliases=[
            "cats",
            "meow",
        ],
    )
    @checks.cooldown()
    async def cat(self, ctx):
        robot = ctx.guild.me
        async with ctx.channel.typing():
            async with self.bot.session as cs:
                async with cs.get("http://aws.random.cat/meow") as r:
                    data = await r.json()

                    embed = discord.Embed(title="Meow", color=robot.color)
                    embed.set_image(url=data["file"])
                    embed.set_footer(text="http://random.cat/")

                    await ctx.send(embed=embed)

    @decorators.command(brief="Random picture of a fox")
    @checks.cooldown()
    async def fox(self, ctx):
        """Random picture of a fox"""
        robot = ctx.guild.me
        async with ctx.channel.typing():
            async with self.bot.session as cs:
                async with cs.get("https://randomfox.ca/floof/") as r:
                    data = await r.json()

                    embed = discord.Embed(title="Floof", color=robot.color)
                    embed.set_image(url=data["image"])
                    embed.set_footer(text="https://randomfox.ca/")

                    await ctx.send(embed=embed)

    @decorators.command(
        brief="Random picture of a duck", aliases=["quack", "ducc", "ducks"]
    )
    @checks.cooldown()
    async def duck(self, ctx):
        """Random picture of a duck"""
        robot = ctx.guild.me
        async with ctx.channel.typing():
            async with self.bot.session as cs:
                async with cs.get("https://random-d.uk/api/random") as response:
                    data = await response.json()

                    embed = discord.Embed(title="Quack", color=robot.color)
                    embed.set_image(url=data["url"])
                    embed.set_footer(text="https://random-d.uk/")

                    await ctx.send(embed=embed)

    @decorators.command(
        brief="Random picture of a raccoon", aliases=["racc", "raccoons"]
    )
    @checks.cooldown()
    async def raccoon(self, ctx):
        """Random picture of a raccoon"""
        await read_shuffle_and_send("raccoon", ctx)

    @decorators.command(
        brief="Random picture of a dog",
        aliases=[
            "dogs",
            "bark",
        ],
    )
    @checks.cooldown()
    async def dog(self, ctx):
        """Random picture of a dog"""
        await read_shuffle_and_send("dog", ctx)

    @decorators.command(
        brief="Random picture of a squirrel",
        aliases=[
            "squ",
            "squirrels",
        ],
    )
    @checks.cooldown()
    async def squirrel(self, ctx):
        """Random picture of a squirrel"""
        await read_shuffle_and_send("squirrel", ctx)

    @decorators.command(
        brief="Random picture of a bear",
        aliases=[
            "bears",
        ],
    )
    @checks.cooldown()
    async def bear(self, ctx):
        """Random picture of a bear"""
        await read_shuffle_and_send("bear", ctx)

    @decorators.command(
        brief="Random picture of a possum",
        aliases=[
            "possums",
        ],
    )
    @checks.cooldown()
    async def possum(self, ctx):
        """Random picture of a possum"""
        await read_shuffle_and_send("possum", ctx)

    @decorators.command(
        brief="Random picture of an axolotl",
        aliases=[
            "axolotls",
        ],
    )
    @checks.cooldown()
    async def axolotl(self, ctx):
        """Random picture of an axolotl"""
        await read_shuffle_and_send("axolotl", ctx)

    @decorators.command(brief="Random picture of a pig", aliases=["pigs"])
    @checks.cooldown()
    async def pig(self, ctx):
        """Random picture of a pig"""
        await read_shuffle_and_send("pig", ctx)

    @decorators.command(brief="Random picture of a penguin", aliases=["penguins"])
    @checks.cooldown()
    async def penguin(self, ctx):
        """Random picture of a penguin"""
        await read_shuffle_and_send("penguin", ctx)

    @decorators.command(
        brief="Random picture of a bunny", aliases=["bunnies", "rabbit"]
    )
    @checks.cooldown()
    async def bunny(self, ctx):
        """Random picture of a bunny"""
        await read_shuffle_and_send("bunny", ctx)

    @decorators.command(brief="Random picture of a snake", aliases=["snek", "snakes"])
    @checks.cooldown()
    async def snake(self, ctx):
        """Random picture of a snake"""
        await read_shuffle_and_send("snake", ctx)

    @decorators.command(brief="Random picture of a sheep", aliases=["shep"])
    @checks.cooldown()
    async def sheep(self, ctx):
        """Random picture of a sheep"""
        await read_shuffle_and_send("sheep", ctx)

    @decorators.command(
        brief="Random picture of a panda (may be a redpanda)", aliases=["pandas"]
    )
    @checks.cooldown()
    async def panda(self, ctx):
        """Random picture of a panda (may be a redpanda)"""
        await read_shuffle_and_send("panda", ctx)

    @decorators.command(brief="Random picture of a redpanda", aliases=["redpandas"])
    @checks.cooldown()
    async def redpanda(self, ctx):
        """"Random picture of a redpanda"""
        await read_shuffle_and_send("redpanda", ctx)

    @decorators.command(brief="Random picture of a birb", aliases=["birb"])
    @checks.cooldown()
    async def bird(self, ctx):
        """Random picture of a birb"""
        await read_shuffle_and_send("bird", ctx)
