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
            return await ctx.send_or_reply(
                content=f"My current prefix is {self.bot.constants.prefix}",
                hidden=True,
            )
        await ctx.send_or_reply(
            f"My current prefix{' is' if len(current_prefixes) == 1 else 'es are '} `{', '.join(current_prefixes)}`",
            hidden=True,
        )
