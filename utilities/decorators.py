import discord
import functools
import asyncio
from discord.ext import commands, menus
from core import bot


def is_home():
    """Server specific"""

    async def predicate(ctx):
        if ctx.guild and ctx.guild.id == 805638877762420786:
            return True

    return commands.check(predicate)


# def bot_check(func, bot=None):
#     """Event decorator check."""
#     @functools.wraps(func)
#     async def wrapper(*args, **kwargs):
#         nonlocal bot
#         self = args[0] if args else None
#         print(self)
#         if isinstance(self, commands.Cog):
#             bot = bot or self.bot
#             val = await bot.add_check(func(*args, **kwargs))
#             return val
#     return wrapper


def event_check(func):
    """Event decorator check."""
    def check(method):
        method.callback = method

        @functools.wraps(method)
        async def wrapper(*args, **kwargs):
            if await discord.utils.maybe_coroutine(func, *args, **kwargs):
                await method(*args, **kwargs)
        return wrapper
    return check


def wait_until_ready(bot=None):
    async def predicate(*args, **_):
        nonlocal bot
        self = args[0] if args else None
        if isinstance(self, commands.Cog):
            bot = bot or self.bot
        if bot.bot_ready:
            return True

    return event_check(predicate)

