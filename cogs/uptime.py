import discord
from discord.ext import commands
import io
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
from utilities import decorators
from settings import constants

    
def setup(bot):
    bot.add_cog(Specific(bot))

class Specific(commands.Cog):
    def __init__(self, bot):
        self.bot = bot


    @commands.Cog.listener()
    @decorators.wait_until_ready()
    @decorators.event_check(lambda s, m: m.guild and m.guild.id == constants.home)
    async def on_message(self, message):
        pass