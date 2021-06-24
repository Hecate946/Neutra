import asyncio
import discord
import functools
from discord.ext import commands

from utilities import override

command = functools.partial(commands.command, cls=override.BotCommand)
group = functools.partial(commands.group, cls=override.BotGroup)


def cooldown(*args, **kwargs):
    return commands.check(override.CustomCooldown(*args, **kwargs))


def event_check(func):
    """
    Event decorator check.
    """

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
        if bot.ready:
            return True

    return event_check(predicate)


def defer_ratelimit(bot=None):
    async def predicate(*args, **_):
        nonlocal bot
        self = args[0] if args else None
        if isinstance(self, commands.Cog):
            bot = bot or self.bot
        await asyncio.sleep(1)
        return True

    return event_check(predicate)


def is_home(home):
    """Support server only commands"""

    async def predicate(ctx):
        if type(home) != list:
            home_guild_list = [home]
        if ctx.guild and ctx.guild.id in home_guild_list:
            return True

    return commands.check(predicate)
