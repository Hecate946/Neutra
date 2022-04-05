import discord
from discord.ext import commands
from discord import app_commands


async def setup(bot):
    await bot.add_cog(Interactions(bot))


class Interactions(commands.Cog):
    """
    Hub for slash and context menu commands.
    """

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="prefix")
    async def slash_prefix(self, interaction: discord.Interaction) -> None:
        """/prefix"""

        if not interaction.message.guild:
            prefixes = list(
                set(self.bot.common_prefixes + [self.bot.config.DEFAULT_PREFIX])
            )
            prefixes = prefixes.copy()
            mention_fmt = self.bot.user.name
        else:
            prefixes = self.bot.get_guild_prefixes(interaction.message.guild)
            mention_fmt = interaction.message.guild.guild.me.display_name
            # Lets remove the mentions and replace with @name
            del prefixes[0]
            del prefixes[0]

        prefixes.insert(0, f"@{mention_fmt}")

        await interaction.response.send_message(
            f"My current prefix{' is' if len(prefixes) == 1 else 'es are'} `{', '.join(prefixes)}`",
            ephemeral=True,
        )

    # @app_commands.context_menu()
    # async def avatar(interaction, user: discord.User):
    #     await interaction.response.send_message(user.display_avatar.url)

    @app_commands.context_menu()
    @app_commands.guilds(discord.Object(id=805638877762420786))
    async def userinfo(interaction, user: discord.User):
        cog = interaction.client.get_cog("Stats")
        embed = await cog.get_userinfo(user)
        await interaction.response.send_message(embed=embed)
