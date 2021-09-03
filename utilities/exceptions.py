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


class InactivePlayer(commands.BadArgument):
    """
    Custom exception to raise when
    the music player is not active.
    """

    def __init__(self, *args):
        msg = "No track is currently being played."
        super().__init__(message=msg, *args)


class FeatureNotSupported(commands.BadArgument):
    """
    Custom exception to raise when the user
    uses on a not yet implemented music feature.
    """

    def __init__(self, message=None, *args):
        msg = "Feature is currently not supported."
        super().__init__(message=message or msg, *args)

class InvalidMediaType(commands.BadArgument):
    """
    Custom exception to raise when the
    file media type cannot be played.
    """

    def __init__(self, message=None, *args):
        msg = "Invalid media type. Media type must be either audio or video."
        super().__init__(message=message or msg, *args)


class SpotifyError(Exception):
    pass


class VoiceError(Exception):
    pass


class YTDLError(Exception):
    pass
