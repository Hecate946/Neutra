import discord
from discord.ext import commands
from discord.ext.commands.errors import BadArgument

from settings import constants

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


async def check_permissions(ctx, perms, *, check=all):
    """ Checks if author has permissions to a permission """
    if ctx.author.id in owners:
        return True

    # resolved = ctx.channel.permissions_for(ctx.author)
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

    # resolved = ctx.channel.permissions_for(ctx.author)
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


def has_permissions(*, check=all, **perms):
    """ discord.Commands method to check if author has permissions """

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


def bot_has_permissions(*, check=all, **perms):
    """ discord.Commands method to check if bot has permissions """

    async def pred(ctx):
        result = await check_bot_permissions(ctx, perms, check=check)
        perm_list = [x.title().replace("_", " ").replace("Tts", "TTS") for x in perms]
        if result is False:
            raise commands.BadArgument(
                message=f"I require the following permission{'' if len(perm_list) == 1 else 's'}: `{', '.join(perm_list)}`"
            )
        return result

    return commands.check(pred)


# async def check_priv(ctx, member):
#     """ Custom way to check permissions when handling moderation commands """
#     try:
#         # Self checks
#         if member == ctx.author:
#             raise commands.BadArgument(f"You cannot {ctx.command.name} yourself.")
#         if member.id == ctx.bot.user.id:
#             raise commands.BadArgument(f"I cannot {ctx.command.name} myself.")

#         # Check if user bypasses
#         if ctx.author.id == ctx.guild.owner.id:
#             return
#         if ctx.author.id in owners:
#             return

#         # Now permission check
#         if member.id in owners:
#             if ctx.author.id not in owners:
#                 raise commands.BadArgument(f"I cannot {ctx.command.name} my creator.")
#         if member.id == ctx.guild.owner.id:
#             raise commands.BadArgument(f"You cannot {ctx.command.name} the server owner.",
#             )
#         if ctx.author.top_role.position == member.top_role.position:
#             raise commands.BadArgument(f"You cannot {ctx.command.name} someone who has the same permissions as you.",
#             )
#         if ctx.author.top_role.position < member.top_role.position:
#             raise commands.BadArgument(f"You cannot {ctx.command.name} someone with a higher role than you.")
#     except Exception as e:
#         print(e)
#         pass

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

        # Check if user bypasses
        if ctx.author.id == ctx.guild.owner.id:
            return
        if ctx.author.id in owners:
            return

        # Now permission check
        if member.id in owners:
            if ctx.author.id not in owners:
                return f"You cannot {ctx.command.name} my creator."
        if member.id == ctx.guild.owner.id:
            return f"You cannot {ctx.command.name} the server owner."
        if ctx.author.top_role.position == member.top_role.position:
            return f"You cannot {ctx.command.name} a user with equal permissions."
        if ctx.author.top_role.position < member.top_role.position:
            return f"You cannot {ctx.command.name} a user with superior permissions."
    except Exception as e:
        print(e)
        pass

def sync_priv(ctx, member):
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

        # Check if user bypasses
        if ctx.author.id == ctx.guild.owner.id:
            return
        if ctx.author.id in owners:
            return

        # Now permission check
        if member.id in owners:
            if ctx.author.id not in owners:
                return f"You cannot {ctx.command.name} my creator."
        if member.id == ctx.guild.owner.id:
            return f"You cannot {ctx.command.name} the server owner."
        if ctx.author.top_role.position == member.top_role.position:
            return f"You cannot {ctx.command.name} a user with equal permissions."
        if ctx.author.top_role.position < member.top_role.position:
            return f"You cannot {ctx.command.name} a user with superior permissions."
    except Exception as e:
        print(e)
        pass

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
