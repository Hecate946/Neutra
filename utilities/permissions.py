import discord
 
from discord.ext import commands

from settings import constants

owners = constants.owners

def is_owner(ctx):
    """ Checks if the author is one of the owners """
    return ctx.author.id in owners


async def check_permissions(ctx, perms, *, check=all):
    """ Checks if author has permissions to a permission """
    if ctx.author.id in owners:
        return True

    #resolved = ctx.channel.permissions_for(ctx.author)
    resolved = ctx.author.guild_permissions
    guild_perm_checker = check(getattr(resolved, name, None) == value for name, value in perms.items())
    if guild_perm_checker is False:
        # Try to see if the user has channel permissions that override
        resolved = ctx.channel.permissions_for(ctx.author)
    return check(getattr(resolved, name, None) == value for name, value in perms.items())


def has_permissions(*, check=all, **perms):
    """ discord.Commands method to check if author has permissions """
    async def pred(ctx):
        return await check_permissions(ctx, perms, check=check)
    return commands.check(pred)


async def check_priv(ctx, member):
    """ Custom (weird) way to check permissions when handling moderation commands """
    failed = []
    try:
        # Self checks
        if member == ctx.author:
            return await ctx.send(f"<:failed:816521503554273320> You cannot {ctx.command.name} yourself.")
        if member.id == ctx.bot.user.id:
            return await ctx.send(f"Fuck off or I'll {ctx.command.name} you. Little piece of shit...")

        # Check if user bypasses
        if ctx.author.id == ctx.guild.owner.id:
            return None
        if ctx.author.id in owners:
            return None

        # Now permission check
        if member.id in owners:
            if ctx.author.id not in owners:
                return await ctx.send(f"<:failed:816521503554273320> I cannot {ctx.command.name} my creator.")
            else:
                pass
        if member.id == ctx.guild.owner.id:
            return await ctx.send(f"<:failed:816521503554273320> You cannot {ctx.command.name} the server owner.")
        if ctx.author.top_role == member.top_role:
            return await ctx.send(f"<:failed:816521503554273320> You cannot {ctx.command.name} someone who has the same permissions as you.")
        if ctx.author.top_role < member.top_role:
            return await ctx.send(f"<:failed:816521503554273320> You cannot {ctx.command.name} someone with a higher role than you.")
    except Exception:
        pass


async def checker(ctx, value):
    if type(value) is list:
        for x in value:
            result = await check_priv(ctx, member=x)
    if type(value) is not list:
        result = await check_priv(ctx, member=value)
    return result


async def voice_priv(ctx, member):
    try:
        if member == ctx.author:
            return None
        if member.id == ctx.bot.user.id:
            return None

        if ctx.author.id == ctx.guild.owner.id:
            return None
        if ctx.author.id in owners:
            return None
        
        if member.id == ctx.guild.owner.id:
            return await ctx.send(f"<:failed:816521503554273320> You cannot {ctx.command.name} the server owner.")
        if ctx.author.top_role == member.top_role:
            return await ctx.send(f"<:failed:816521503554273320> You cannot {ctx.command.name} someone who has the same permissions as you.")
        if ctx.author.top_role < member.top_role:
            return await ctx.send(f"<:failed:816521503554273320> You cannot {ctx.command.name} someone who has a higher role than you.")
    except Exception as e:
        print(e)

def can_handle(ctx, permission: str):
    """ Checks if bot has permissions or is in DMs right now """
    return isinstance(ctx.channel, discord.DMChannel) or getattr(ctx.channel.permissions_for(ctx.guild.me), permission)