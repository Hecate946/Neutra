import os
import uuid
from os.path import splitext
from PIL import Image
from discord.ext import commands
from utilities import utils, pagination
from urllib.parse import urlparse


# A helper module for images


async def download(
    url, ext: str = "jpg", sizeLimit: int = 8000000, ua: str = "NGC0000"
):
    """Download the passed URL and return the file path."""
    url = str(url).strip("<>")
    folder = "./data/wastebin/"
    filename = f"{uuid.uuid4()}:image.png"
    dirpath = folder + filename
    r_image = None

    try:
        r_image = await utils.async_dl(url, headers={"user-agent": ua})
    except Exception:
        pass
    if r_image is None:
        raise commands.BadArgument(f"Invalid emoji.")

    with open(dirpath, "wb") as f:
        f.write(r_image)

    try:
        # Try to get the extension
        img = Image.open(dirpath)
        ext = img.format
        img.close()
    except Exception:
        os.remove(dirpath)

    if ext and not dirpath.lower().endswith("." + ext.lower()):
        os.rename(dirpath, "{}.{}".format(dirpath, ext))
        return "{}.{}".format(dirpath, ext)
    else:
        return dirpath
