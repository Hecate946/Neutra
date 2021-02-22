from utilities import default
from lib.bot import bot

VERSION = default.config()["version"]

bot.run(VERSION)
