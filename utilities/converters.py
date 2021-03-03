import re
import discord

from discord.ext import commands

from core import bot



#converter from R.Danny
class BannedMember(commands.Converter):
    async def convert(self, ctx, argument):
        if argument.isdigit():
            member_id = int(argument, base=10)
            try:
                return await ctx.guild.fetch_ban(discord.Object(id=member_id))
            except discord.NotFound:
                raise commands.BadArgument('This member has not been banned before.') from None

        ban_list = await ctx.guild.bans()
        entity = discord.utils.find(lambda u: str(u.user) == argument, ban_list)

        if entity is None:
            raise commands.BadArgument('This member has not been banned before.')
        return entity

class DiscordUser(commands.Converter):
    """
    Returns user object from ID, mention, nickname, username, or username+discriminator (If user exists)
    """
    async def convert(self, ctx, argument):
        #Check to see whether the ID was passed
        if argument.isdigit():
            user_id = int(argument, base=10)
            result = await ctx.bot.fetch_user(user_id)
            #Got our user, return result
            return result

        #Check to see if the user was mentioned
        match = re.match(r'<@!?([0-9]+)>$', argument)

        if match is not None:
            #Parse the mention and fetch user from ID
            user_id = int(match.group(1))
            result = ctx.bot.get_user(user_id)
            if not result:
                try:
                    result = await ctx.bot.fetch_user(user_id)
                    return result
                except discord.HTTPException:
                    result = user_id
        else:
            member_list = ctx.bot.get_all_members()
            arg = argument
            # check for discriminator if it exists
            if len(arg) > 5 and arg[-5] == '#':
                discrim = arg[-4:]
                name = arg[:-5]
                user = discord.utils.find(lambda u: u.name == name and u.discriminator == discrim, member_list)
                if user is not None:
                    #Got the user from username+discrim
                    return user

            result = discord.utils.find(lambda u: u.name == arg, member_list)
            if result is None:
                #Lastly try for nickname match
                if not ctx.guild:
                    return None
                server_members = ctx.guild.members
                result = discord.utils.find(lambda u: u.display_name == arg, server_members)
                if result is None:
                    raise commands.BadArgument(f'No user id or user found with "{argument}"')
                
        if result is None:
            raise commands.BadArgument('User "{}" not found'.format(argument))
        #Was just username
        return result
