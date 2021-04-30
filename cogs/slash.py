from discord.ext import commands
from discord_slash import SlashContext, cog_ext

from core import bot


def setup(bot):
    bot.add_cog(Slash(bot))


class Slash(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @cog_ext.cog_slash(
        description="Show my server prefix.", guild_ids=[x.id for x in bot.guilds]
    )
    async def prefix(self, ctx: SlashContext):
        current_prefixes = self.bot.server_settings[ctx.guild.id]["prefixes"].copy()
        try:
            current_prefixes.remove(f"<@!{self.bot.user.id}>")
        except ValueError:
            pass
        if len(current_prefixes) == 0:
            return await ctx.send(
                content=f"My current prefix is {self.bot.constants.prefix}",
                hidden=True,
            )
        await ctx.send(
            f"My current prefix{' is' if len(current_prefixes) == 1 else 'es are '} `{', '.join(current_prefixes)}`",
            hidden=True,
        )

    # @cog_ext.cog_slash(description="Show my uptime.", guild_ids=[740734113086177433, 782493910161031185])
    # async def uptime(self, ctx: SlashContext):
    #     uptime = utils.time_between(self.bot.starttime, int(time.time()))
    #     await ctx.send_or_reply(
    #         f"{self.bot.emote_dict['stopwatch']} I've been running for `{uptime}`",
    #         hidden=True)
