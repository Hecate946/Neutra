from io import BytesIO
import json
import discord
from discord.ext import commands
from discord import app_commands

from utilities import cleaner, pagination


async def setup(bot):
    await bot.add_cog(Interactions(bot))
    bot.tree.add_command(avatar, guild=discord.Object(805638877762420786))
    bot.tree.add_command(_ascii, guild=discord.Object(805638877762420786))


class Interactions(commands.Cog):
    """
    Hub for slash and context menu commands.
    """

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="prefix", description="Show my current prefixes.")
    async def prefix(self, interaction):

        prefixes = self.bot.get_guild_prefixes(interaction.guild)
        mention_fmt = interaction.guild.me.display_name
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
async def avatar(interaction, user: discord.Member):
    await interaction.response.send_message(user.display_avatar.url)


@app_commands.context_menu(name="Ascii")
@app_commands.guilds(discord.Object(id=805638877762420786))
async def _ascii(interaction, user: discord.Member):
    if user != interaction.client:
        image_bytes = await interaction.client.http_utils.get(
            user.display_avatar.url, res_method="read"
        )
        path = BytesIO(image_bytes)
        image = interaction.client.get_cog("Misc").ascii_image(path)
        await interaction.response.send_message(
            file=discord.File(image, filename="matrix.png")
        )
    else:
        image_bytes = await interaction.client.http_utils.get(
            interaction.client.display_avatar.url, res_method="read"
        )
        path = BytesIO(image_bytes)
        image = interaction.client.get_cog("Misc").ascii_image(path)
        await interaction.response.send_message(
            file=discord.File(image, filename="matrix.png")
        )
