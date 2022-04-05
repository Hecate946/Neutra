import discord
import asyncio
import random
import numpy as np

from PIL import Image, ImageDraw, ImageFont
from discord.ext import commands
from discord import app_commands
from io import BytesIO

from utilities import checks
from utilities import converters
from utilities import decorators


async def setup(bot):
    await bot.add_cog(Misc(bot))


class Misc(commands.Cog):
    """
    Miscellaneous stuff.
    """

    def __init__(self, bot):
        self.bot = bot

    @decorators.command(
        brief="Finds the 'best' definition of a word", aliases=["urban"]
    )
    @checks.cooldown()
    async def define(self, ctx, *, search: commands.clean_content):
        """
        Usage: {0}define <search>
        Alias: {0}urban
        Output:
            Attempts to fetch an urban dictionary
            definition based off of your search query.
        """
        async with ctx.channel.typing():
            try:
                url = await self.bot.http_utils.get(
                    f"https://api.urbandictionary.com/v0/define?term={search}",
                    res_method="json",
                )
            except Exception:
                return await ctx.send("Urban API returned invalid data... fuck them.")

            if not url:
                return await ctx.send("I think the API broke...")

            if not len(url["list"]):
                return await ctx.send("Couldn't find your search in the dictionary...")

            result = sorted(
                url["list"], reverse=True, key=lambda g: int(g["thumbs_up"])
            )[0]

            definition = result["definition"]
            if len(definition) >= 2000:
                definition = definition[:2000]
                definition = definition.rsplit(" ", 1)[0]
                definition += "..."

            await ctx.send_or_reply(
                f"📚 Definitions for **{result['word']}**```yaml\n{definition}```"
            )

    def ascii_image(self, path):
        image = Image.open(path)
        sc = 0.2
        gcf = 0.2
        bgcolor = "#060e16"
        re_list = list(" .,:;irsXA253hMHGS#9B&@")
        chars = np.asarray(re_list)
        font = ImageFont.load_default()
        font = ImageFont.truetype("./data/assets/Monospace.ttf", 10)
        letter_width = font.getsize("x")[0]
        letter_height = font.getsize("x")[1]
        wcf = letter_height / letter_width
        img = image.convert("RGBA")

        width_by_letter = round(img.size[0] * sc * wcf)
        height_by_letter = round(img.size[1] * sc)
        s = (width_by_letter, height_by_letter)
        img = img.resize(s)
        img = np.sum(np.asarray(img), axis=2)
        img -= img.min()
        img = (1.0 - img / img.max()) ** gcf * (chars.size - 1)
        lines = ("".join(r) for r in chars[len(chars) - img.astype(int) - 1])
        new_img_width = letter_width * width_by_letter
        new_img_height = letter_height * height_by_letter
        new_img = Image.new("RGBA", (new_img_width, new_img_height), bgcolor)
        draw = ImageDraw.Draw(new_img)
        y = 0
        for line in lines:
            draw.text((0, y), line, "#FFFFFF", font=font)
            y += letter_height

        buffer = BytesIO()
        new_img.save(buffer, "png")  # 'save' function for PIL
        buffer.seek(0)
        return buffer

    @decorators.command(
        name="matrix",
        aliases=["ascii", "print"],
        brief="Generate a dot matrix of an image.",
    )
    @checks.cooldown()
    async def matrix(self, ctx, *, url=None):
        """
        Usage: {0}print [user, image url, or image attachment]
        Aliases: {0}matrix, {0}ascii
        Output: Creates a dot matrix of the passed image.
        Notes: Accepts a url or picks the first attachment.
        """

        if url == None and len(ctx.message.attachments) == 0:
            await ctx.send_or_reply(
                "Usage: `{}matrix [user, url, or attachment]`".format(ctx.prefix)
            )
            return

        if url == None:
            url = ctx.message.attachments[0].url

        # Let's check if the "url" is actually a user
        try:
            test_user = await converters.DiscordUser().convert(ctx, url)
            url = test_user.display_avatar.url
        except Exception:
            pass

        message = await ctx.load("Generating dot matrix...")

        try:
            image_bytes = await self.bot.http_utils.get(url, res_method="read")
        except Exception:
            await message.edit(content="Invalid url or attachment.")
            return

        path = BytesIO(image_bytes)
        if not path:
            await message.edit(content="Invalid url or attachment.")
            return

        image = self.ascii_image(path)
        await ctx.rep_or_ref(file=discord.File(image, filename="matrix.png"))
        await message.delete()

    @decorators.command(brief="Just try it and see.")
    @checks.cooldown()
    async def size(self, ctx, *, user: converters.DiscordUser = None):
        user = user or ctx.author

        def find_size(snowflake):
            s = 0
            while snowflake:
                snowflake //= 10
                s += snowflake % 10
                return (s % 10) * 2

        size = find_size(user.id)
        if user.id == self.bot.developer_id:
            size *= 5

        await ctx.send_or_reply(f"**{user.display_name}'s** size: 8{'=' * size}D")
