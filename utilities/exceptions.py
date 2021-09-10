import discord
from discord.ext import commands


class AmbiguityError(commands.BadArgument):
    """
    Custom exception to raise when
    multiple objects match a search.
    """

    def __init__(self, argument, name: str = "User", *args):
        msg = f"Multiple {name}s found from search: `{argument}`. Please retry using the ID or mention to prevent ambiguity."
        super().__init__(message=msg, *args)


class IntractabilityError(commands.BadArgument):
    """
    Custom exception to raise when
    an object cannot be manipulated.
    """

    def __init__(self, reason, *args):
        super().__init__(message=reason, *args)


class WebhookLimit(commands.BadArgument):
    """
    Custom exception to raise when the max
    webhook limit for a channel is reached.
    """

    def __init__(self, channel, *args):
        msg = f"Channel {channel.mention} has reached the maximum number of webhooks (10). Please delete a webhook and retry."
        super().__init__(message=msg, *args)
