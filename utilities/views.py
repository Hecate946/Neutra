import discord

class MuteRoleView(discord.ui.View):
    def __init__(self, ctx):
        super().__init__(timeout=60)
        self.ctx = ctx
        self.overwrites = None
        self.message = None


    def create_msg(self, option):
        msg = f"{self.ctx.bot.emote_dict['loading']} **Creating mute system. "
        msg += f"Muted users will not be able to {option} messages. "
        msg += "This process may take several minutes...**"
        return msg

    async def interaction_check(self, interaction):
        if self.ctx.author.id == interaction.user.id:
            return True
        else:
            await interaction.response.send_message(
                "Only the command invoker can use this button.", ephemeral=True
            )

    async def on_timeout(self):
        self.stop()

    @discord.ui.button(label="Block (Cannot send messages)", style=discord.ButtonStyle.blurple)
    async def block(self, button: discord.ui.Button, interaction: discord.Interaction):
        await interaction.message.edit(content=self.create_msg("send"), embed=None, view=None)
        self.overwrites = {"send_messages": False}
        self.stop()

    @discord.ui.button(label="Blind (Cannot read messages)", style=discord.ButtonStyle.gray)
    async def blind(self, button: discord.ui.Button, interaction: discord.Interaction):
        await interaction.message.edit(content=self.create_msg("read"), embed=None, view=None)
        self.overwrites = {"send_messages": False, "read_messages": False}
        self.stop()

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red)
    async def cancel(self, button: discord.ui.Button, interaction: discord.Interaction):
        self.stop()