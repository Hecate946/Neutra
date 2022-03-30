import io
import discord
import PIL as pillow

from discord.ext import commands

from utilities import utils
from utilities import checks
from utilities import converters
from utilities import decorators

HOME = 805638877762420786  # Support Server
WELCOME = 847612677013766164  # Welcome channel
GENERAL = 805638877762420789  # Chatting channel
TESTING = 871900448955727902  # Testing channel
ANNOUNCE = 852361774871216150  # Announcement channel


async def setup(bot):
    await bot.add_cog(Home(bot))


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

    @property
    def booster(self):
        return self.bot.get_channel(TESTING)

    #####################
    ## Event Listeners ##
    #####################

    @commands.Cog.listener()
    @decorators.wait_until_ready()
    @decorators.event_check(lambda s, m: m.guild.id == HOME)
    async def on_member_join(self, member):
        if self.bot.tester is False:
            await self.welcome(member)

    async def welcome(self, member):
        byteav = await member.display_avatar.with_size(128).read()
        buffer = await self.bot.loop.run_in_executor(
            None, self.create_welcome_image, byteav, member
        )
        dfile = discord.File(fp=buffer, filename="welcome.png")

        embed = discord.Embed(
            title=f"WELCOME TO {member.guild.name.upper()}!",
            description=f"> Click [here]({self.bot.oauth}) to invite {self.bot.user.mention}\n"
            f"> Click [here](https://discord.com/channels/{HOME}/{ANNOUNCE}) for announcements.\n"
            f"> Click [here](https://discord.com/channels/{HOME}/{GENERAL}) to start chatting.\n"
            f"> Click [here](https://discord.com/channels/{HOME}/{TESTING}) to run commands.\n",
            timestamp=discord.utils.utcnow(),
            color=self.bot.config.EMBED_COLOR,
            url=self.bot.oauth,
        )
        embed.set_thumbnail(url=utils.get_icon(member.guild))
        embed.set_image(url="attachment://welcome.png")
        embed.set_footer(text=f"Server Population: {member.guild.member_count} ")
        await self.welcomer.send(f"{member.mention}", file=dfile, embed=embed)

    def create_welcome_image(self, bytes_avatar, member):
        banner = pillow.Image.open("./data/assets/banner.png").resize((725, 225))
        blue = pillow.Image.open("./data/assets/blue.png")
        mask = pillow.Image.open("./data/assets/avatar_mask.png")

        avatar = pillow.Image.open(io.BytesIO(bytes_avatar))

        try:
            composite = pillow.Image.composite(avatar, mask, mask)
        except ValueError:  # Sometimes the avatar isn't resized properly
            avatar = avatar.resize((128, 128))
            composite = pillow.Image.composite(avatar, mask, mask)
        blue.paste(im=composite, box=(0, 0), mask=composite)
        banner.paste(im=blue, box=(40, 45), mask=blue.split()[3])

        text = "{}\nWelcome to {}".format(str(member), member.guild.name)
        draw = pillow.ImageDraw.Draw(banner)
        font = pillow.ImageFont.truetype(
            "./data/assets/FreeSansBold.ttf", 40, encoding="utf-8"
        )
        draw.text((190, 60), text, (211, 211, 211), font=font)
        buffer = io.BytesIO()
        banner.save(buffer, "png")  # 'save' function for PIL
        buffer.seek(0)
        return buffer

    async def thank_booster(self, member):
        byteav = await member.display_avatar.with_size(128).read()
        buffer = await self.bot.loop.run_in_executor(
            None, self.create_booster_image, byteav, member
        )
        dfile = discord.File(fp=buffer, filename="booster.png")

        embed = discord.Embed(
            title=f"Thank you for boosting!",
            # description=f"> Click [here]({self.bot.oauth}) to invite {self.bot.user.mention}\n"
            # f"> Click [here](https://discord.com/channels/{HOME}/{ANNOUNCE}) for announcements.\n"
            # f"> Click [here](https://discord.com/channels/{HOME}/{GENERAL}) to start chatting.\n"
            # f"> Click [here](https://discord.com/channels/{HOME}/{TESTING}) to run commands.\n",
            timestamp=discord.utils.utcnow(),
            color=self.bot.config.EMBED_COLOR,
            url=self.bot.oauth,
        )
        embed.set_thumbnail(url=utils.get_icon(member.guild))
        embed.set_image(url="attachment://booster.png")
        embed.set_footer(
            text=f"Server Boosts: {member.guild.premium_subscription_count} "
        )
        await self.booster.send(f"{member.mention}", file=dfile, embed=embed)

    def create_booster_image(self, bytes_avatar, member):
        banner = pillow.Image.open("./data/assets/roo.png")  # .resize((725, 225))
        blue = pillow.Image.open("./data/assets/blue.png")
        mask = pillow.Image.open("./data/assets/avatar_mask.png")

        avatar = pillow.Image.open(io.BytesIO(bytes_avatar))

        try:
            composite = pillow.Image.composite(avatar, mask, mask)
        except ValueError:  # Sometimes the avatar isn't resized properly
            avatar = avatar.resize((128, 128))
            composite = pillow.Image.composite(avatar, mask, mask)
        blue.paste(im=composite, box=(0, 0), mask=composite)
        banner.paste(im=blue, box=(40, 45), mask=blue.split()[3])

        # text = "{}\nWelcome to {}".format(str(member), member.guild.name)
        # draw = pillow.ImageDraw.Draw(banner)
        # font = pillow.ImageFont.truetype(
        #     "./data/assets/FreeSansBold.ttf", 40, encoding="utf-8"
        # )
        # draw.text((190, 60), text, (211, 211, 211), font=font)
        buffer = io.BytesIO()
        banner.save(buffer, "png")  # 'save' function for PIL
        buffer.seek(0)
        return buffer

    @decorators.command(hidden=True, brief="Test the welcome", name="welcome")
    @decorators.is_home(HOME)
    @checks.has_perms(manage_guild=True)
    @checks.bot_has_perms(embed_links=True, attach_files=True)
    async def _welcome(self, ctx, user: converters.DiscordMember = None):
        user = user or ctx.author
        await self.welcome(user)

    @decorators.command(hidden=True, brief="Test the boost", name="booster")
    @decorators.is_home(HOME)
    @checks.has_perms(manage_guild=True)
    @checks.bot_has_perms(embed_links=True, attach_files=True)
    async def _booster(self, ctx, user: converters.DiscordMember = None):
        user = user or ctx.author
        await self.thank_booster(user)
