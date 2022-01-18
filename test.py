# import smtplib, ssl

# port = 587  # For starttls
# smtp_server = "smtp.gmail.com"
# sender_email = "botneutra@gmail.com"
# receiver_email = "hecate946@gmail.com"
# password = input("Type your password and press enter:")
# message = """\
# Subject: Hi there

# This message is sent from Python."""

# context = ssl.create_default_context()
# with smtplib.SMTP(smtp_server, port) as server:
#     server.ehlo()  # Can be omitted
#     server.starttls(context=context)
#     server.ehlo()  # Can be omitted
#     server.login(sender_email, password)
#     server.sendmail(sender_email, receiver_email, message)


import asyncio
import re
from email.message import EmailMessage
from typing import Collection, List, Tuple, Union

import aiosmtplib

HOST = "smtp.gmail.com"

CARRIER_MAP = {
    "verizon": "vtext.com",
    "tmobile": "tmomail.net",
    "sprint": "messaging.sprintpcs.com",
    "at&t": "txt.att.net",
    "boost": "smsmyboostmobile.com",
    "cricket": "sms.cricketwireless.net",
    "uscellular": "email.uscc.net",
}


# pylint: disable=too-many-arguments
async def send_txt(
    num: Union[str, int], carrier: str, email: str, pword: str, msg: str, subj: str
) -> Tuple[dict, str]:
    to_email = CARRIER_MAP[carrier]

    # build message
    message = EmailMessage()
    message["From"] = email
    message["To"] = f"{num}@{to_email}"
    message["Subject"] = subj
    message.set_content(msg)

    # send
    send_kws = dict(username=email, password=pword, hostname=HOST, port=587, start_tls=True)
    res = await aiosmtplib.send(message, **send_kws)  # type: ignore
    msg = "failed" if not re.search(r"\sOK\s", res[1]) else "succeeded"
    print(msg)
    return res


async def send_txts(
    nums: Collection[Union[str, int]], carrier: str, email: str, pword: str, msg: str, subj: str
) -> List[Tuple[dict, str]]:
    tasks = [send_txt(n, carrier, email, pword, msg, subj) for n in set(nums)]
    return await asyncio.gather(*tasks)


if __name__ == "__main__":
    _num = "7607039509"
    _carrier = "tmobile"
    _email = "botneutra@gmail.com"
    _pword = "Neutra#946"
    _msg = "Dummy msg"
    _subj = "Dummy subj"
    coro = send_txt(_num, _carrier, _email, _pword, _msg, _subj)
    # _nums = {"999999999", "000000000"}
    # coro = send_txts(_nums, _carrier, _email, _pword, _msg, _subj)
    asyncio.run(coro)