import discord
from discord.ext import commands

from settings import constants

from utilities import override

owners = constants.owners
admins = constants.admins


def is_owner(ctx):
    """ Checks if the author is one of the owners """
    return ctx.author.id in owners


def is_admin(ctx):
    if (
        ctx.author.id in ctx.bot.constants.admins
        or ctx.author.id in ctx.bot.constants.owners
    ):
        return True
    return


def is_mod():
    async def pred(ctx):
        return await check_permissions(ctx, {"manage_guild": True})

    return commands.check(pred)


async def check_permissions(ctx, perms, *, check=all):
    """ Checks if author has permissions to a permission """
    if ctx.author.id in owners:
        return True

    resolved = ctx.author.guild_permissions
    guild_perm_checker = check(
        getattr(resolved, name, None) == value for name, value in perms.items()
    )
    if guild_perm_checker is False:
        # Try to see if the user has channel permissions that override
        resolved = ctx.channel.permissions_for(ctx.author)
    return check(
        getattr(resolved, name, None) == value for name, value in perms.items()
    )


async def check_bot_permissions(ctx, perms, *, check=all):
    """ Checks if author has permissions to a permission """
    if ctx.guild:
        resolved = ctx.guild.me.guild_permissions
        guild_perm_checker = check(
            getattr(resolved, name, None) == value for name, value in perms.items()
        )
        if guild_perm_checker is False:
            # Try to see if the user has channel permissions that override
            resolved = ctx.channel.permissions_for(ctx.guild.me)
        return check(
            getattr(resolved, name, None) == value for name, value in perms.items()
        )
    else:
        return True


def has_perms(*, check=all, **perms):  # Decorator to check if a user has perms

    invalid = set(perms) - set(discord.Permissions.VALID_FLAGS)
    if invalid:
        raise TypeError(f"Invalid permission(s): {', '.join(invalid)}")

    async def pred(ctx):
        result = await check_permissions(ctx, perms, check=check)
        perm_list = [
            x.title().replace("_", " ").replace("Tts", "TTS").replace("Guild", "Server")
            for x in perms
        ]
        if result is False:
            raise commands.BadArgument(
                message=f"You are missing the following permission{'' if len(perm_list) == 1 else 's'}: `{', '.join(perm_list)}`"
            )
        return result

    return commands.check(pred)


def bot_has_perms(*, check=all, **perms):  # Decorator to check if the bot has perms

    invalid = set(perms) - set(discord.Permissions.VALID_FLAGS)
    if invalid:
        raise TypeError(f"Invalid permission(s): {', '.join(invalid)}")

    async def pred(ctx):
        result = await check_bot_permissions(ctx, perms, check=check)
        if (
            result is False
        ):  # We know its a guild because permissions failed in check_bot_permissions()
            guild_perms = [x[0] for x in ctx.guild.me.guild_permissions if x[1] is True]
            channel_perms = [
                x[0] for x in ctx.channel.permissions_for(ctx.guild.me) if x[1] is True
            ]
            botperms = guild_perms + channel_perms
            perms_needed = []
            for x in perms:
                if not x in botperms:  # Only complain about the perms we don't have
                    perms_needed.append(x)

            perm_list = [
                x.title().replace("_", " ").replace("Tts", "TTS") for x in perms_needed
            ]
            raise commands.BadArgument(
                message=f"I require the following permission{'' if len(perm_list) == 1 else 's'}: `{', '.join(perm_list)}`"
            )
        return result

    return commands.check(pred)


def is_bot_admin():  # Decorator for bot admin commands
    async def pred(ctx):
        return is_admin(ctx)

    return commands.check(pred)


async def check_priv(ctx, member):
    """
    Handle permission hierarchy for commands
    Return the reason for failure.
    """
    try:
        # Self checks
        if member == ctx.author:
            return f"You cannot {ctx.command.name} yourself."
        if member.id == ctx.bot.user.id:
            return f"I cannot {ctx.command.name} myself."

        # Bot lacks permissions
        if member.id == ctx.guild.owner.id:
            return f"I cannot {ctx.command.name} the server owner."
        if ctx.guild.me.top_role.position == member.top_role.position:
            return f"I cannot {ctx.command.name} a user with equal permissions."
        if ctx.guild.me.top_role.position < member.top_role.position:
            return f"I cannot {ctx.command.name} a user with superior permissions."
        if member.id in owners:
            return f"I cannot {ctx.command.name} my creator."

        # Check if user bypasses
        if ctx.author.id == ctx.guild.owner.id:
            return
        if ctx.author.id in owners:
            return
        # Now permission check
        if ctx.author.top_role.position == member.top_role.position:
            return f"You cannot {ctx.command.name} a user with equal permissions."
        if ctx.author.top_role.position < member.top_role.position:
            return f"You cannot {ctx.command.name} a user with superior permissions."
    except Exception as e:
        print(e)
        pass


async def role_priv(ctx, role):
    """
    Handle permission hierarchy for commands
    Return the reason for failure.
    """
    # First role validity check
    if role.is_bot_managed():
        return f"Role `{role.name}` is managed by a bot."
    if role.is_premium_subscriber():
        return f"Role `{role.name}` is this server's booster role."
    if role.is_integration():
        return f"Role `{role.name}` is managed by an integration."

    # Bot lacks permissions
    if ctx.guild.me.top_role.position == role.position:
        return f"Role `{role.name}` is my highest role."
    if ctx.guild.me.top_role.position < role.position:
        return f"Role `{role.name}` is above my highest role."

    # Check if user bypasses
    if ctx.author.id == ctx.guild.owner.id:
        return

    # Now permission check
    if ctx.author.top_role.position == role.position:
        return f"Role `{role.name}` is your highest role."
    if ctx.author.top_role.position < role.position:
        return f"Role `{role.name}` is above highest role."


async def nick_priv(ctx, member):
    # Bot lacks permissions
    if member.id == ctx.guild.owner.id:
        return f"User `{member}` is the server owner. I cannot edit the nickname of the server owner."
    if ctx.me.top_role.position < member.top_role.position:
        return "I cannot rename users with superior permissions."
    if ctx.me.top_role.position == member.top_role.position and member.id != ctx.me.id:
        return "I cannot rename users with equal permissions."
    
    # Check if user bypasses
    if ctx.author.id == ctx.guild.owner.id:
        return  # Owner bypasses
    if ctx.author.id == member.id:
        return  # They can edit their own nicknames

    # Now permission check
    if ctx.author.top_role.position < member.top_role.position:
        return f"You cannot nickname a user with superior permissions."
    if ctx.author.top_role.position == member.top_role.position:
        return f"You cannot nickname a user with equal permissions."


async def checker(ctx, value):
    if type(value) is list:
        for x in value:
            result = await check_priv(ctx, member=x)
    if type(value) is not list:
        result = await check_priv(ctx, member=value)
    return result


def can_handle(ctx, permission: str):
    """ Checks if bot has permissions or is in DMs right now """
    return isinstance(ctx.channel, discord.DMChannel) or getattr(
        ctx.channel.permissions_for(ctx.guild.me), permission
    )


def has_guild_permissions(**perms):

    invalid = set(perms) - set(discord.Permissions.VALID_FLAGS)
    if invalid:
        raise TypeError(f"Invalid permission(s): {', '.join(invalid)}")

    def predicate(ctx):
        if not ctx.guild:
            raise commands.NoPrivateMessage

        permissions = ctx.author.guild_permissions
        missing = [
            perm for perm, value in perms.items() if getattr(permissions, perm) != value
        ]

        if not missing:
            return True

        perm_list = [x.title().replace("_", " ").replace("Tts", "TTS") for x in missing]
        raise commands.BadArgument(
            f"You require the following permission{'' if len(perm_list) == 1 else 's'}: `{', '.join(perm_list)}`"
        )

    return commands.check(predicate)


def bot_has_guild_perms(**perms):

    invalid = set(perms) - set(discord.Permissions.VALID_FLAGS)
    if invalid:
        raise TypeError(f"Invalid permission(s): {', '.join(invalid)}")

    def predicate(ctx):
        if not ctx.guild:
            raise commands.NoPrivateMessage

        permissions = ctx.me.guild_permissions
        missing = [
            perm for perm, value in perms.items() if getattr(permissions, perm) != value
        ]
        if not missing:
            return True

        perm_list = [x.title().replace("_", " ").replace("Tts", "TTS") for x in missing]
        raise commands.BadArgument(
            f"I require the following permission{'' if len(perm_list) == 1 else 's'}: `{', '.join(perm_list)}`"
        )

    return commands.check(predicate)


def dm_only():
    def predicate(ctx):
        if ctx.guild is not None:
            raise commands.PrivateMessageOnly()
        return True

    return commands.check(predicate)


def guild_only():
    def predicate(ctx):
        if ctx.guild is None:
            raise commands.NoPrivateMessage()
        return True

    return commands.check(predicate)


def cooldown(*args, **kwargs):
    return commands.check(override.CustomCooldown(*args, **kwargs))
