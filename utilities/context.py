import discord

from discord.ext import commands

from utilities import pagination


class BotContext(commands.Context):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    async def fail(self, content=None, **kwargs):
        return await self.send_or_reply(
            self.bot.emote_dict["failed"] + " " + (content if content else ""), **kwargs
        )

    async def success(self, content=None, **kwargs):
        return await self.send_or_reply(
            self.bot.emote_dict["success"] + " " + (content if content else ""),
            **kwargs,
        )

    async def bot_channel(self, content=None, **kwargs):
        return await self.bot.bot_channel.send(content, **kwargs)

    async def send_or_reply(self, content=None, **kwargs):
        ref = self.message.reference
        if ref and isinstance(ref.resolved, discord.Message):
            return await self.send(
                content, **kwargs, reference=ref.resolved.to_reference()
            )
        return await self.send(content, **kwargs)

    async def react(self, reaction=None, content=None, **kwargs):
        return await self.message.add_reaction(reaction)

    async def usage(self, content=None, **kwargs):
        return await self.send(
            f"Usage: `{self.prefix}{self.command.qualified_name} " + content + "`"
        )

    async def load(self, content=None, **kwargs):
        content = f"{self.bot.emote_dict['loading']} **{content}**"
        return await self.send_or_reply(content, **kwargs)

    async def confirm(self, content=None, **kwargs):
        content = f"**{self.bot.emote_dict['exclamation']} {content}. Do you wish to continue?**"
        c = await pagination.Confirmation(msg=content).prompt(ctx=self)
        if c:
            return True
        return

    # async def log(self, _type=None, content=None, **kwargs):
    #     if _type in ["info", "i", "information"]:
    #         logger = info_logger
    #         loglev = info_logger.info
    #         level = "INFO"
    #         location = info_logger_handler.baseFilename
    #     elif _type in ["command", "commands", "cmd", "cmds"]:
    #         logger = command_logger
    #         loglev = command_logger.info
    #         level = "INFO"
    #         location = command_logger_handler.baseFilename
    #     elif _type in ["err", "e", "error", "errors"]:
    #         logger = error_logger
    #         loglev = error_logger.warning
    #         level = "WARNING"
    #         location = error_logger_handler.baseFilename
    #     elif _type in ["trace", "t", "traceback"]:
    #         logger = traceback_logger
    #         loglev = traceback_logger.warning
    #         level = "WARNING"
    #         location = traceback_logger_handler.baseFilename
    #     log_format = "{0}: [{1}] {2} ||".format(
    #         datetime.now().strftime("%Y-%m-%d %H:%M:%S"), level, logger.name
    #     )
    #     filename = "./" + "/".join(location.split("/")[-4:])
    #     loglev(msg=content)
    #     return await self.bot_channel(
    #         self.bot.emote_dict["log"]
    #         + f" **Logged to `{filename}`**```prolog\n{log_format}{content}```"
    #     )
