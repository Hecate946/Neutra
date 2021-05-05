import discord
import functools
from discord.ext import commands

from utilities import override

command = functools.partial(commands.command, cls=override.BotCommand)
group = functools.partial(commands.group, cls=override.BotGroup)


def is_home():
    """
    Server specific
    """

    async def predicate(ctx):
        if ctx.guild and ctx.guild.id == ctx.bot.home.id:
            return True

    return commands.check(predicate)


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
