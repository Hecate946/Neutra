import io
import discord
import traceback

from datetime import datetime
from discord.ext import commands

from utilities import utils


class Monitor(commands.Cog):
    """
    Log bot errors and monitor health
    """

    def __init__(self, bot):
        self.bot = bot

    @discord.utils.cached_property
    def webhook(self):
        try:
            wh_id, wh_token = utils.config()["errors"]
            hook = discord.Webhook.partial(
                id=wh_id,
                token=wh_token,
                adapter=discord.AsyncWebhookAdapter(self.bot.session),
            )
        except KeyError:
            hook = None
        return hook


async def on_error(self, event, *args, **kwargs):
    title = f"**{self.emote_dict['failed']} Error `{datetime.utcnow()}`**"
    description = f"```prolog\n{event.upper()}:\n{kwargs.get('tb') or traceback.format_exc()}\n```"
    args_str = []
    dfile = None
    if args:
        for index, arg in enumerate(args):
            args_str.append(f"[{index}]: {arg!r}")

        fp = io.BytesIO("\n".join(args_str).encode("utf-8"))
        dfile = discord.File(fp, "arguments.unrendered")
    hook = self.get_cog("Monitor").webhook
    av = "https://cdn.discordapp.com/attachments/846597178918436885/846597481231679508/error.png"
    try:
        await hook.send(
            title + description,
            file=dfile,
            username=f"{self.user.name} Monitor",
            avatar_url=av,
        )
    except Exception:
        pass


def setup(bot):
    cog = Monitor(bot)
    bot.add_cog(cog)
    commands.AutoShardedBot.on_error = on_error
