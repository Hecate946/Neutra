import discord
import asyncio
import random
import numpy as np

from PIL import Image
from discord.ext import commands
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
        description="Finds the 'best' definition of a word", aliases=["urban"]
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

    def _ascii(self, image):
        try:
            chars = np.asarray(list(" .,:;irsXA253hMHGS#9B&@"))
            f, WCF, GCF = image, 7 / 4, 0.6
            img = Image.open(image)
            # Make sure we have frame 1
            img = img.convert("RGBA")

            # Let's scale down
            w, h = 0, 0
            adjust = 2
            w = img.size[0] * adjust
            h = img.size[1]

            # Make sure we're under max params of 50h, 50w
            ratio = 1
            max_wide = 500
            if h * 2 > w:
                if h > max_wide / adjust:
                    ratio = max_wide / adjust / h
            else:
                if w > max_wide:
                    ratio = max_wide / w
            h = ratio * h
            w = ratio * w

            # Shrink to an area of 1900 or so (allows for extra chars)
            target = 1900
            if w * h > target:
                r = h / w
                w1 = np.sqrt(target / r)
                h1 = target / w1
                w = w1
                h = h1

            S = (round(w), round(h))
            img = np.sum(np.asarray(img.resize(S)), axis=2)
            img -= img.min()
            img = (1.0 - img / img.max()) ** GCF * (chars.size - 1)
            a = "\n".join(("".join(r) for r in chars[len(chars) - img.astype(int) - 1]))
            a = "```\n" + a + "```"
            return a
        except Exception:
            pass
        return False

    @decorators.command(name="print", aliases=["matrix", "ascii"])
    @checks.cooldown()
    async def print(self, ctx, *, url=None):
        """
        Usage: {0}print [user, image url, or image attachment]
        Aliases: {0}matrix, {0}ascii
        Output: Creates a dot matrix of the passed image.
        Notes: Accepts a url or picks the first attachment.
        """

        if url == None and len(ctx.message.attachments) == 0:
            await ctx.send_or_reply(
                "Usage: `{}print [user, url, or attachment]`".format(ctx.prefix)
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

        message = await ctx.load("Printing...")

        image_bytes = await self.bot.http_utils.get(url, res_method="read")
        path = BytesIO(image_bytes)
        if not path:
            await message.edit(
                content="I guess I couldn't print that one...  Make sure you're passing a valid url or attachment."
            )
            return

        final = self._ascii(path)

        if not final:
            await message.edit(
                content="I couldn't print that image...  Make sure you're pointing me to a valid image file."
            )
            return

        await message.edit(content=final)

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

        await ctx.send_or_reply(
            f"**{user.display_name}'s** size: 8{'=' * find_size(user.id)}D"
        )
