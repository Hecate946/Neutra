import io
import discord
import PIL as pillow

from datetime import datetime
from discord.ext import commands

from utilities import decorators

HOME = 805638877762420786  # Support Server
WELCOME = 847612677013766164  # Welcome channel
GENERAL = 805638877762420789  # Chatting channel
SUPPORT = 848648976349921350  # Support channel


def setup(bot):
    bot.add_cog(Home(bot))


class Home(commands.Cog):
    """
    Server specific cog.
    """

    def __init__(self, bot):
        self.bot = bot

    @property
    def home(self):
        return self.bot.get_guild(HOME)

    @property
    def welcomer(self):
        return self.bot.get_channel(WELCOME)

    #####################
    ## Event Listeners ##
    #####################

    @commands.Cog.listener()
    @decorators.wait_until_ready()
    @decorators.event_check(lambda s, m: m.guild.id == HOME)
    async def on_member_join(self, member):
        await self.welcome(member)

    async def welcome(self, member):
        banner = pillow.Image.open("./data/assets/banner.png")
        blue = pillow.Image.open("./data/assets/blue.png")
        mask = pillow.Image.open("./data/assets/avatar_mask.png")

        bytes_avatar = await self.bot.get(
            str(member.avatar_url_as(format="png", size=128)), res_method="read"
        )
        avatar = pillow.Image.open(io.BytesIO(bytes_avatar))

        composite = pillow.Image.composite(avatar, mask, mask)
        blue.paste(im=composite, box=(0, 0), mask=composite)
        banner.paste(im=blue, box=(30, 30), mask=blue.split()[3])

        text = f"{str(member)}\nWelcome to {member.guild.name}"
        draw = pillow.ImageDraw.Draw(banner)
        font = pillow.ImageFont.truetype("./data/assets/Roboto-Black.ttf", 30)
        draw.text((170, 60), text, (211, 211, 211), font=font)

        buffer = io.BytesIO()
        banner.save(buffer, "png")  # 'save' function for PIL
        buffer.seek(0)
        dfile = discord.File(fp=buffer, filename="welcome.png")

        embed = discord.Embed(
            title=f"WELCOME TO {member.guild.name.upper()}!",
            description=f"> Click [here]({self.bot.oauth}) to invite {self.bot.user.mention}\n"
            f"> Click [here](https://discord.com/channels/{HOME}/{GENERAL}) to start chatting\n"
            f"> Click [here](https://discord.com/channels/{HOME}/{SUPPORT}) for bot support\n",
            timestamp=datetime.utcnow(),
            color=self.bot.constants.embed,
            url=self.bot.oauth,
        )
        embed.set_thumbnail(url=member.guild.icon_url)
        embed.set_image(url="attachment://welcome.png")
        embed.set_footer(text=f"Server Population: {member.guild.member_count} ")
        await self.welcomer.send(f"{member.mention}", file=dfile, embed=embed)
