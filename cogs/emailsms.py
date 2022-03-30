import discord
from discord.ext import commands
import asyncio
import re
from email.message import EmailMessage
from typing import Collection, List, Tuple, Union

import aiosmtplib


async def setup(bot):
    await bot.add_cog(Email(bot))


class Email(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        self.HOST = "smtp.gmail.com"

        self.CARRIER_MAP = {
            "verizon": "vtext.com",
            "tmobile": "tmomail.net",
            "sprint": "messaging.sprintpcs.com",
            "at&t": "txt.att.net",
            "boost": "smsmyboostmobile.com",
            "cricket": "sms.cricketwireless.net",
            "uscellular": "email.uscc.net",
        }

        self.email = "botneutra@gmail.com"
        self.password = "Neutra#946"

    async def cog_check(self, ctx):
        if ctx.author.id in [
            708584008065351681,
            782479134436753428,
            664245010383896620,
        ]:
            return True
        return await ctx.send("Yeah you don't have perms lmfao.")

    async def send_email(self, address, email: str, pword: str, msg: str, subj: str):
        message = EmailMessage()
        message["From"] = email
        message["To"] = address
        message["Subject"] = subj
        message.set_content(msg)
        # send
        send_kws = dict(
            username=email, password=pword, hostname=self.HOST, port=587, start_tls=True
        )
        res = await aiosmtplib.send(message, **send_kws)  # type: ignore
        msg = "failed" if not re.search(r"\sOK\s", res[1]) else "succeeded"
        return res

    async def send_txt(
        self, num: Union[str, int], carrier: str, email: str, pword: str, msg: str
    ) -> Tuple[dict, str]:
        to_email = self.CARRIER_MAP[carrier]

        message = EmailMessage()
        message["From"] = email
        message["To"] = f"{num}@{to_email}"
        message.set_content(msg)

        # send
        send_kws = dict(
            username=email, password=pword, hostname=self.HOST, port=587, start_tls=True
        )
        res = await aiosmtplib.send(message, **send_kws)  # type: ignore
        msg = "failed" if not re.search(r"\sOK\s", res[1]) else "succeeded"
        return res

    async def send_txts(
        self,
        nums: Collection[Union[str, int]],
        carrier: str,
        email: str,
        pword: str,
        msg: str,
        subj: str,
    ) -> List[Tuple[dict, str]]:
        tasks = [self.send_txt(n, carrier, email, pword, msg, subj) for n in set(nums)]
        return await asyncio.gather(*tasks)

    @commands.command()
    async def text(self, ctx, number: int, carrier, *, message):
        if carrier in self.CARRIER_MAP:
            msg = await ctx.send("I'm sending it don't spam.")
            await self.send_txt(
                number, carrier, email=self.email, pword=self.password, msg=message
            )
            await msg.edit(content="sent")

        else:
            await ctx.send(
                f"Carrier must be one of these: `{', '.join(self.CARRIER_MAP)}`"
            )

    @commands.command()
    async def email(self, ctx, address, *, message):

        msg = await ctx.send("I'm sending it don't spam.")
        await self.send_email(
            address, email=self.email, pword=self.password, msg=message, subj=None
        )
        await msg.edit(content="sent")
