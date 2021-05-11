import asyncio
import calendar
import difflib
import json
import re
import time
import traceback
from datetime import datetime, timedelta, timezone
import gc

import aiohttp
import discord
from discord.ext import menus
import humanize
import pytz
import timeago as timesince

from discord.iterators import HistoryIterator


# Some funcs and ideas from corpbot.py and discord_bot.py

URL_REGEX = (
    r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*(),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+"
)


def config(filename: str = "config"):
    """ Fetch default config file """
    try:
        with open(f"{filename}.json", encoding="utf8") as data:
            return json.load(data)
    except FileNotFoundError:
        raise FileNotFoundError("JSON file wasn't found")


def traceback_maker(err, advance: bool = True):
    """ A way to debug your code anywhere """
    _traceback = "".join(traceback.format_tb(err.__traceback__))
    error = ("\n{1}{0}: {2}\n").format(type(err).__name__, _traceback, err)
    return error if advance else f"{type(err).__name__}: {err}"


def timetext(name):
    """ Timestamp, but in text form """
    return f"{name}_{int(time.time())}.txt"


def timeago(target):
    """ Timeago in easier way """
    return str(timesince.format(target))


def date(target, clock=True):
    """ Clock format using datetime.strftime() """
    if not clock:
        return target.strftime("%d %B %Y")
    return target.strftime("%d %B %Y, %H:%M")


def get_years(timeBetween, year, reverse):
    years = 0

    while True:
        if reverse:
            year -= 1
        else:
            year += 1

        year_days = 366 if calendar.isleap(year) else 365
        year_seconds = year_days * 86400

        if timeBetween < year_seconds:
            break

        years += 1
        timeBetween -= year_seconds

    return timeBetween, years, year


def get_months(timeBetween, year, month, reverse):
    months = 0

    while True:
        month_days = calendar.monthrange(year, month)[1]
        month_seconds = month_days * 86400

        if timeBetween < month_seconds:
            break

        months += 1
        timeBetween -= month_seconds

        if reverse:
            if month > 1:
                month -= 1
            else:
                month = 12
                year -= 1
        else:
            if month < 12:
                month += 1
            else:
                month = 1
                year += 1

    return timeBetween, months


def time_between(first, last, reverse=False):
    # A helper function to make a readable string between two times
    timeBetween = int(last - first)
    now = datetime.now()
    year = now.year
    month = now.month

    timeBetween, years, year = get_years(timeBetween, year, reverse)
    timeBetween, months = get_months(timeBetween, year, month, reverse)

    weeks = int(timeBetween / 604800)
    days = int((timeBetween - (weeks * 604800)) / 86400)
    hours = int((timeBetween - (days * 86400 + weeks * 604800)) / 3600)
    minutes = int((timeBetween - (hours * 3600 + days * 86400 + weeks * 604800)) / 60)
    seconds = int(
        timeBetween - (minutes * 60 + hours * 3600 + days * 86400 + weeks * 604800)
    )
    msg = ""

    if years > 0:
        msg += "1 year, " if years == 1 else "{:,} years, ".format(years)
    if months > 0:
        msg += "1 month, " if months == 1 else "{:,} months, ".format(months)
    if weeks > 0:
        msg += "1 week, " if weeks == 1 else "{:,} weeks, ".format(weeks)
    if days > 0:
        msg += "1 day, " if days == 1 else "{:,} days, ".format(days)
    if hours > 0:
        msg += "1 hour, " if hours == 1 else "{:,} hours, ".format(hours)
    if minutes > 0:
        msg += "1 minute, " if minutes == 1 else "{:,} minutes, ".format(minutes)
    if seconds > 0:
        msg += "1 second, " if seconds == 1 else "{:,} seconds, ".format(seconds)

    if msg == "":
        return "0 seconds"
    else:
        try:
            msg_args = msg[:-2].split(" ")
            msg_args[-3] = msg_args[-3][:-1]
            msg_args[-2] = "and " + msg_args[-2]
            msg = " ".join(msg_args)
            return msg
        except IndexError:
            return msg[:-2]


def responsible(target, reason):
    """ Default responsible maker targeted to find user in AuditLogs """
    responsible = f"[ {target} ]"
    if not reason:
        return f"{responsible} no reason given..."
    return f"{responsible} {reason}"


def makeBar(progress):
    return "[{0}{1}] {2}%".format(
        "#" * (int(round(progress / 3))),
        " " * (33 - (int(round(progress / 3)))),
        progress,
    )


def center(string, header=None):
    leftPad = " " * (int(round((40 - len(string)) / 3)))
    leftPad += string
    if header:
        output = header + leftPad[len(header) :]
    else:
        output = leftPad
    return output


def edit_config(value: str, changeto: str):
    """ Change a value from the configs """
    config_name = "config.json"
    with open(config_name, "r") as jsonFile:
        data = json.load(jsonFile)
    data[value] = changeto
    with open(config_name, "w") as jsonFile:
        json.dump(data, jsonFile, indent=2)


def write_json(file_path, data):
    with open(file_path, "w", encoding="utf-8") as fp:
        json.dump(data, fp, indent=2)


def disambiguate(term, list_to_search, key: str = None, limit: int = 3):
    """Searches the provided list for the searchTerm - using a keyName if provided for dicts."""
    if len(list_to_search) < 1:
        return None
    # Iterate through the list and create a list of items
    findings = []
    for item in list_to_search:
        if key:
            name = item[key]
        else:
            name = item
        match_ratio = difflib.SequenceMatcher(None, term.lower(), name.lower()).ratio()
        findings.append({"result": item, "ratio": match_ratio})
    # sort the servers by population
    findings = sorted(findings, key=lambda x: x["ratio"], reverse=True)
    if limit > len(findings):
        limit = len(findings)
    return findings[:limit]


def getClockForTime(time_string):
    # Assumes a HH:MM PP format
    try:
        t = time_string.split(" ")
        if len(t) == 2:
            t = t[0].split(":")
        elif len(t) == 3:
            t = t[1].split(":")
        else:
            return time_string
        hour = int(t[0])
        minute = int(t[1])
    except Exception:
        return time_string
    clock_string = ""
    if minute > 44:
        clock_string = str(hour + 1) if hour < 12 else "1"
    elif minute > 14:
        clock_string = str(hour) + "30"
    else:
        clock_string = str(hour)

    clock_dict = {
        ":clock1:": "\U0001f550",
        ":clock130:": "\U0001f55c",
        ":clock2:": "\U0001f551",
        ":clock230:": "\U0001f55d",
        ":clock3:": "\U0001f552",
        ":clock330:": "\U0001f55e",
        ":clock4:": "\U0001f553",
        ":clock430:": "\U0001f55f",
        ":clock5:": "\U0001f554",
        ":clock530:": "\U0001f560",
        ":clock6:": "\U0001f555",
        ":clock630:": "\U0001f561",
        ":clock7:": "\U0001f556",
        ":clock730:": "\U0001f562",
        ":clock8:": "\U0001f557",
        ":clock830:": "\U0001f563",
        ":clock9:": "\U0001f558",
        ":clock930:": "\U0001f564",
        ":clock10:": "\U0001f559",
        ":clock1030:": "\U0001f565",
        ":clock11:": "\U0001f55a",
        ":clock1130:": "\U0001f566",
        ":clock12:": "\U0001f55b",
        ":clock1230:": "\U0001f567",
    }
    return time_string + " " + clock_dict[":clock" + clock_string + ":"]


def getUserTime(
    member, settings, time=None, strft="%Y-%m-%d %I:%M %p", clock=True, force=None
):
    # Returns a dict representing the time from the passed member's perspective
    offset = (
        force
        if force
        else settings.getGlobalUserStat(
            member, "TimeZone", settings.getGlobalUserStat(member, "UTCOffset", None)
        )
    )
    if offset is None:
        # No offset or tz - return UTC
        t = getClockForTime(time.strftime(strft)) if clock else time.strftime(strft)
        return {"zone": "UTC", "time": t, "vanity": "{} {}".format(t, "UTC")}
    # At this point - we need to determine if we have an offset - or possibly a timezone passed
    t = getTimeFromTZ(offset, time, strft, clock)
    if t is None:
        # We did not get a zone
        t = getTimeFromOffset(offset, time, strft, clock)
    t["vanity"] = "{} {}".format(t["time"], t["zone"])
    return t


def getTimeFromOffset(offset, t=None, strft="%Y-%m-%d %I:%M %p", clock=True):
    offset = offset.replace("+", "")
    # Split time string by : and get hour/minute values
    try:
        hours, minutes = map(int, offset.split(":"))
    except Exception:
        try:
            hours = int(offset)
            minutes = 0
        except Exception:
            return None
    msg = "UTC"
    # Get the time
    if t is None:
        t = datetime.utcnow()
    # Apply offset
    if hours > 0:
        # Apply positive offset
        msg += "+{}".format(offset)
        td = timedelta(hours=hours, minutes=minutes)
        newTime = t + td
    elif hours < 0:
        # Apply negative offset
        msg += "{}".format(offset)
        td = timedelta(hours=(-1 * hours), minutes=(-1 * minutes))
        newTime = t - td
    else:
        # No offset
        newTime = t
    if clock:
        ti = getClockForTime(newTime.strftime(strft))
    else:
        ti = newTime.strftime(strft)
    return {"zone": msg, "time": ti}


def getTimeFromTZ(tz, t=None, strft="%Y-%m-%d %I:%M %p", clock=True):
    # Assume sanitized zones - as they're pulled from pytz
    # Let's get the timezone list
    zone = next(
        (pytz.timezone(x) for x in pytz.all_timezones if x.lower() == tz.lower()), None
    )
    if zone is None:
        return None
    zone_now = (
        datetime.now(zone)
        if t is None
        else pytz.utc.localize(t, is_dst=None).astimezone(zone)
    )
    ti = (
        getClockForTime(zone_now.strftime(strft)) if clock else zone_now.strftime(strft)
    )
    return {"zone": str(zone), "time": ti}


def modify_config(key, value):
    with open("./config.json", "r", encoding="utf-8") as fp:
        data = json.load(fp)
        data[key] = value
    with open("./config.json", "w") as fp:
        json.dump(data, fp, indent=2)


def load_json(file):
    with open(file, "r", encoding="utf-8") as fp:
        data = json.load(fp)
        return data


def get_urls(message):
    # Returns a list of valid urls from a passed message/context/string
    message = (
        message.content
        if isinstance(message, discord.Message)
        else message.message.content
        if isinstance(message, discord.ext.commands.Context)
        else str(message)
    )
    return [x.group(0) for x in re.finditer(URL_REGEX, message)]


async def async_post_json(url, data=None, headers=None):
    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.post(url, data=data) as response:
            return await response.json()


async def async_post_text(url, data=None, headers=None):
    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.post(url, data=data) as response:
            res = await response.read()
            return res.decode("utf-8", "replace")


async def async_post_bytes(url, data=None, headers=None):
    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.post(url, data=data) as response:
            return await response.read()


async def async_head_json(url, headers=None):
    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.head(url) as response:
            return await response.json()


async def async_dl(url, headers=None):
    # print("Attempting to download {}".format(url))
    total_size = 0
    data = b""
    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.get(url) as response:
            assert response.status == 200
            while True:
                chunk = await response.content.read(4 * 1024)  # 4k
                data += chunk
                total_size += len(chunk)
                if not chunk:
                    break
                if total_size > 8000000:
                    # Too big...
                    # print("{}\n - Aborted - file too large.".format(url))
                    return None
    return data


async def async_text(url, headers=None):
    data = await async_dl(url, headers)
    if data != None:
        return data.decode("utf-8", "replace")
    else:
        return data


async def async_json(url, headers=None):
    data = await async_dl(url, headers)
    if data != None:
        return json.loads(data.decode("utf-8", "replace"))
    else:
        return data


UNKNOWN_CUTOFF = datetime.utcfromtimestamp(1420070400.000)
UNKNOWN_CUTOFF_TZ = UNKNOWN_CUTOFF.replace(tzinfo=timezone.utc)


def format_time(time):
    if time is None or time < UNKNOWN_CUTOFF:
        return "Unknown"
    return "{} - [{}+00:00 UTC]".format(
        humanize.naturaltime(time + (datetime.now() - datetime.utcnow())), time
    )


def short_time(time):
    if time is None or time < UNKNOWN_CUTOFF:
        return "Unknown"
    return "{}".format(
        humanize.naturaltime(time + (datetime.now() - datetime.utcnow())), time
    )


def format_time_tz(time):
    if time is None or time < UNKNOWN_CUTOFF_TZ:
        return "Unknown"
    return "{} ({})".format(
        humanize.naturaltime(time.astimezone(tz=None).replace(tzinfo=None)), time
    )


def format_timedelta(td):
    ts = td.total_seconds()
    return "{:02d}:{:06.3f}".format(int(ts // 60), ts % 60)


def hex_value(arg):
    return int(arg, base=16)


def object_at(addr):
    for o in gc.get_objects():
        if id(o) == addr:
            return o
    return None


def cleanup_code(content):
    """Automatically removes code blocks from the code."""
    # remove ```py\n```
    if content.startswith("```") and content.endswith("```"):
        return "\n".join(content.split("\n")[1:-1])

    # remove `foo`
    return content.strip("` \n")


class CachedHistoryIterator(HistoryIterator):
    """HistoryIterator, but we hit the cache first."""

    def __init__(
        self,
        messageable,
        limit,
        before=None,
        after=None,
        around=None,
        oldest_first=None,
    ):
        super().__init__(messageable, limit, before, after, around, oldest_first)
        self.prefill = self.reverse is False and around is None

    async def next(self):
        if self.prefill:
            await self.prefill_from_cache()
            self.prefill = False
        return await super().next()

    async def prefill_from_cache(self):
        if not hasattr(self, "channel"):
            # do the required set up
            channel = await self.messageable._get_channel()
            self.channel = channel

        for msg in reversed(self.channel._state._messages):
            if (
                msg.channel.id == self.channel.id
                and self.limit > 0
                and (not self.before or msg.id < self.before.id)
            ):
                self.limit -= 1
                self.before = discord.Object(id=msg.id)
                await self.messages.put(msg)
