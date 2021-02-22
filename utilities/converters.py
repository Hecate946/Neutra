import discord
from discord.ext import commands

# Converter from Not-a-Bot
class PossibleUser(commands.converter.IDConverter):
    """
    Possibly returns a user object
    If no user is found returns user id if it could be parsed from argument
    """
    async def convert(self, ctx, argument):
        match = self._get_id_match(argument) or re.match(r'<@!?([0-9]+)>$', argument)
        state = ctx._state

        if match is not None:
            user_id = int(match.group(1))
            result = ctx.bot.get_user(user_id)
            if not result:
                try:
                    result = await ctx.bot.fetch_user(user_id)
                except discord.HTTPException:
                    result = user_id
        else:
            arg = argument
            # check for discriminator if it exists
            if len(arg) > 5 and arg[-5] == '#':
                discrim = arg[-4:]
                name = arg[:-5]
                user = discord.utils.find(lambda u: u.name == name and u.discriminator == discrim,
                                          state._users.values())
                if user is not None:
                    return user

            result = discord.utils.find(lambda u: u.name == arg,
                                        state._users.values())
            if result is None:
                raise commands.BadArgument(f'No user id or user found with "{argument}"')

        if result is None:
            raise commands.BadArgument('User "{}" not found'.format(argument))

        return result


class AnyUser(PossibleUser):
    """
    Like possible user but fall back to given value when nothing is found
    """
    async def convert(self, ctx, argument):
        try:
            user = await PossibleUser.convert(self, ctx, argument)
            return user or argument
        except commands.BadArgument:
            return argument

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

class TextChannel(commands.Converter):
    async def convert(self, ctx, argument):
        if argument.isdigit():
            textchannel_id = int(argument, base=10)
            try:
                return await ctx.guild.get_channel(textchannel_id)
            except discord.NotFound:
                raise commands.BadArgument('No such channel.') from None
    
        channel_list = await ctx.guild.TextChannels()
        entity = discord.utils.find(lambda u: str(u.name) == argument, channel_list)
        if entity is None:
            raise commands.BadArgument('No such channel.')
        return entity
