import typing
import discord
from discord.ext import commands

from utilities import pagination


class BotContext(commands.Context):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.handled = False
        

    async def fail(self, content=None, **kwargs):
        return await self.send_or_reply(
            self.bot.emote_dict["failed"] + " " + (content if content else ""), **kwargs
        )

    async def success(self, content=None, **kwargs):
        return await self.send_or_reply(
            self.bot.emote_dict["success"] + " " + (content if content else ""),
            **kwargs,
        )

    async def send_or_reply(self, content=None, **kwargs):
        if not self.channel.permissions_for(self.me).send_messages:
            return
        ref = self.message.reference
        if ref and isinstance(ref.resolved, discord.Message):
            return await self.send(
                content, **kwargs, reference=ref.resolved.to_reference()
            )
        return await self.send(content, **kwargs)

    async def rep_or_ref(self, content=None, **kwargs):
        ref = self.message.reference
        if ref and isinstance(ref.resolved, discord.Message):
            return await self.send(
                content, **kwargs, reference=ref.resolved.to_reference()
            )
        return await self.reply(content, **kwargs)

    async def react(self, reaction=None, content=None, **kwargs):
        return await self.message.add_reaction(reaction)

    async def bold(self, content=None, **kwargs):
        return await self.send_or_reply(
            "**" + (content if content else "") + "**", **kwargs
        )

    async def usage(self, usage=None, command=None, **kwargs):
        if command:
            name = command.qualified_name
        else:
            name = self.command.qualified_name
        content = (
            f"Usage: `{self.prefix}{name} "
            + (usage if usage else self.command.signature)
            + "`"
        )
        return await self.send_or_reply(content, **kwargs)

    async def load(self, content=None, **kwargs):
        content = f"{self.bot.emote_dict['loading']} **{content}**"
        return await self.send_or_reply(content, **kwargs)

    async def confirm(self, content="", **kwargs):
        content = f"**{content} Do you wish to continue?**"
        c = await pagination.Confirmation(msg=content).prompt(ctx=self)
        if c:
            return True
        await self.send_or_reply(f"{self.bot.emote_dict['exclamation']} **Cancelled.**")
        return

    async def dm(self, content=None, **kwargs):
        try:
            await self.author.send(content, **kwargs)
        except Exception:
            await self.send_or_reply(content, **kwargs)

    async def trigger_typing(self):
        if self.channel.permissions_for(self.me).send_messages:
            return await super().trigger_typing()
        else:
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
    #     return await self.logging_webhook(
    #         self.bot.emote_dict["log"]
    #         + f" **Logged to `{filename}`**```prolog\n{log_format}{content}```"
    #     )


class BotCommand(commands.Command):
    def __init__(self, func, **kwargs):
        super().__init__(func, **kwargs)
        self.cooldown_after_parsing = kwargs.pop("cooldown_after_parsing", True)
        self.examples = kwargs.pop("examples", None)
        self.implemented = kwargs.pop("implemented", None)
        self.updated = kwargs.pop("updated", None)
        self.writer = kwargs.pop("writer", 708584008065351681)
        # Maybe someday more will contribute... :((


class BotGroup(commands.Group):
    def __init__(self, func, **kwargs):
        super().__init__(func, **kwargs)
        self.case_insensitive = kwargs.pop("case_insensitive", True)
        self.cooldown_after_parsing = kwargs.pop("cooldown_after_parsing", True)
        self.invoke_without_command = kwargs.pop("invoke_without_command", False)
        self.examples = kwargs.pop("examples", None)
        self.implemented = kwargs.pop("implemented", None)
        self.updated = kwargs.pop("updated", None)
        self.writer = kwargs.pop("writer", 708584008065351681)


class CustomCooldown:
    def __init__(
        self,
        rate: int = 3,
        per: float = 10.0,
        *,
        alter_rate: int = 0.0,
        alter_per: float = 0,
        bucket: commands.BucketType = commands.BucketType.user,
        bypass: list = [],
    ):
        self.bypass = bypass
        self.default_mapping = commands.CooldownMapping.from_cooldown(rate, per, bucket)
        self.altered_mapping = commands.CooldownMapping.from_cooldown(
            alter_rate, alter_per, bucket
        )
        self.owner_mapping = commands.CooldownMapping.from_cooldown(0, 0, bucket)
        self.owner = 708584008065351681

    def __call__(self, ctx):
        key = self.altered_mapping._bucket_key(ctx.message)
        if key == self.owner:
            bucket = self.owner_mapping.get_bucket(ctx.message)
        elif key in self.bypass:
            bucket = self.altered_mapping.get_bucket(ctx.message)
        else:
            bucket = self.default_mapping.get_bucket(ctx.message)
        retry_after = bucket.update_rate_limit()
        if retry_after:
            raise commands.CommandOnCooldown(bucket, retry_after)
        return True


T = typing.TypeVar("T")


class Greedy(typing.List[T]):
    r"""A special converter that greedily consumes arguments until it can't.
    As a consequence of this behaviour, most input errors are silently discarded,
    since it is used as an indicator of when to stop parsing.
    When a parser error is met the greedy converter stops converting, undoes the
    internal string parsing routine, and continues parsing regularly.
    For example, in the following code:
    .. code-block:: python3
        @commands.command()
        async def test(ctx, numbers: Greedy[int], reason: str):
            await ctx.send("numbers: {}, reason: {}".format(numbers, reason))
    An invocation of ``[p]test 1 2 3 4 5 6 hello`` would pass ``numbers`` with
    ``[1, 2, 3, 4, 5, 6]`` and ``reason`` with ``hello``\.
    For more information, check :ref:`ext_commands_special_converters`.
    """

    def __init__(self, *, converter: T):
        self.converter = converter

    def __repr__(self):
        converter = getattr(self.converter, "__name__", repr(self.converter))
        return f"Greedy[{converter}]"

    def __class_getitem__(cls, params: typing.Union[typing.Tuple[T], T]):
        if not isinstance(params, tuple):
            params = (params,)
        if len(params) != 1:
            raise TypeError("Greedy[...] only takes a single argument")
        converter = params[0]

        origin = getattr(converter, "__origin__", None)
        args = getattr(converter, "__args__", ())

        if not (
            callable(converter)
            or isinstance(converter, discord.Converter)
            or origin is not None
        ):
            raise TypeError("Greedy[...] expects a type or a Converter instance.")

        if converter in (str, type(None)) or origin is Greedy:
            raise TypeError(f"Greedy[{converter.__name__}] is invalid.")

        if origin is typing.Union and type(None) in args:
            raise TypeError(f"Greedy[{converter!r}] is invalid.")

        return cls(converter=converter)
