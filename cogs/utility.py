import re
import json
import pytz
import math
import time
import codecs
import pprint
import discord
import operator

from datetime import datetime, timedelta
from collections import Counter
from functools import cmp_to_key
from pyparsing import (
    Literal,
    CaselessLiteral,
    Word,
    Combine,
    Group,
    Optional,
    ZeroOrMore,
    Forward,
    nums,
    alphas,
    oneOf,
)
from geopy import geocoders
from discord.ext import commands, menus

from utilities import utils, permissions, pagination, converters


def setup(bot):
    bot.add_cog(Utility(bot))


class Utility(commands.Cog):
    """
    Module for general utilities
    """

    def __init__(self, bot):
        self.bot = bot
        self.emote_dict = bot.emote_dict
        self.stopwatches = {}
        self.geo = geocoders.Nominatim(user_agent="Hypernova")

    ####################
    ## VOICE COMMANDS ##
    ####################

    @commands.command(brief="Move a user from a voice channel.")
    @commands.guild_only()
    @permissions.bot_has_permissions(move_members=True)
    @permissions.has_permissions(move_members=True)
    async def vcmove(
        self, ctx, targets: commands.Greedy[discord.Member] = None, channel: str = None
    ):
        """
        Usage:      -vcmove <target> <target>... <channel>
        Output:     Moves members into a new voice channel
        Permission: Move Members
        """
        if not targets:
            return await ctx.send(
                f"Usage: `{ctx.prefix}vc move <to channel> <target> [target]...`"
            )
        if not channel:
            return await ctx.send(
                f"Usage: `{ctx.prefix}vc move <to channel> <target> [target]...`"
            )
        voice = []
        try:
            voicechannel = ctx.guild.get_channel(int(channel))
        except Exception as e:
            try:
                voicechannel = discord.utils.get(ctx.guild.voice_channels, name=channel)
            except Exception as e:
                await ctx.send(e)
        for target in targets:
            if target.id in self.bot.constants.owners:
                return await ctx.send(
                    reference=self.bot.rep_ref(ctx),
                    content="You cannot move my master.",
                )
            if (
                ctx.author.top_role.position < target.top_role.position
                and ctx.author.id not in self.bot.constants.owners
            ):
                return await ctx.send(
                    reference=self.bot.rep_ref(ctx),
                    content="You cannot move other staff members",
                )
            try:
                await target.edit(voice_channel=voicechannel)
            except discord.HTTPException:
                await ctx.send(
                    f"{self.emote_dict['error']} Target is not connected to a voice channel"
                )
            voice.append(target)
        if voice:
            vckicked = []
            for member in voice:
                users = []
                people = await self.bot.fetch_user(int(member.id))
                users.append(people)
                for user in users:
                    username = f"{user.name}#{user.discriminator}"
                    vckicked += [username]
            await ctx.send(
                "<:checkmark:816534984676081705> VC Moved `{0}`".format(
                    ", ".join(vckicked)
                )
            )

    @commands.command(brief="Kick all users from a voice channel.")
    @commands.guild_only()
    @permissions.has_permissions(move_members=True)
    @permissions.bot_has_permissions(move_members=True)
    async def vcpurge(self, ctx, channel: discord.VoiceChannel = None):
        """
        Usage: -vcpurge <voice channel>
        Output: Kicks all members from the channel
        Permission: Move Members
        """
        if channel is None:
            return await ctx.send(
                f"Usage: `{ctx.prefix}vcpurge <voice channel name/id>`"
            )
        if channel.members is None:
            return await ctx.send(
                f"{self.emote_dict['error']} No members in voice channel."
            )
        for member in channel.members:
            try:
                if await permissions.voice_priv(ctx, member):
                    continue
                await member.edit(voice_channel=None)
            except Exception:
                continue
        await ctx.send(
            reference=self.bot.rep_ref(ctx),
            content=f"{self.emote_dict['success']} Purged {channel.mention}.",
        )

    @commands.command(brief="Kick users from a voice channel.")
    @commands.guild_only()
    @permissions.has_permissions(move_members=True)
    @permissions.bot_has_permissions(move_members=True)
    async def vckick(self, ctx, targets: commands.Greedy[discord.Member]):
        """
        Usage:      -vckick <target> <target>
        Output:     Kicks passed members from their channel
        Permission: Move Members
        """
        if not len(targets):
            return await ctx.send(
                reference=self.bot.rep_ref(ctx),
                content=f"Usage: `{ctx.prefix}vckick <target> [target]...`",
            )
        voice = []
        for target in targets:
            if (
                ctx.author.top_role.position <= target.top_role.position
                and ctx.author.id not in self.bot.constants.owners
                or ctx.author.id != ctx.guild.owner.id
                and target.id != ctx.author.id
            ):
                return await ctx.send(
                    "<:fail:816521503554273320> You cannot move other staff members"
                )
            try:
                await target.edit(voice_channel=None)
            except discord.HTTPException:
                await ctx.send(
                    f"{self.emote_dict['error']} Target is not connected to a voice channel"
                )
            voice.append(target)
        if voice:
            vckicked = []
            for member in voice:
                users = []
                people = await self.bot.fetch_user(int(member.id))
                users.append(people)
                for user in users:
                    username = f"{user.name}#{user.discriminator}"
                    vckicked += [username]
            await ctx.send(
                "<:checkmark:816534984676081705> VC Kicked `{0}`".format(
                    ", ".join(vckicked)
                )
            )

    async def do_avatar(self, ctx, user, url):
        embed = discord.Embed(
            title=f"**{user.display_name}'s avatar.**",
            description=f"Links to `{user}'s` avatar:  "
            f"[webp]({(str(url))}) | "
            f'[png]({(str(url).replace("webp", "png"))}) | '
            f'[jpeg]({(str(url).replace("webp", "jpg"))})  ',
            color=self.bot.constants.embed,
        )
        embed.set_image(url=url)
        await ctx.send(reference=self.bot.rep_ref(ctx), embed=embed)

    @commands.command(brief="Show a user's avatar.", aliases=["av", "pfp"])
    async def avatar(self, ctx, *, user: converters.DiscordUser = None):
        """
        Usage:    -avatar [user]
        Aliases:  -av, -pfp
        Examples: -avatar 810377376269205546, -avatar Hypernova
        Output:   Shows an enlarged embed of a user's avatar.
        Notes:    Will default to yourself if no user is passed.
        """
        if user is None:
            user = ctx.author
        try:
            await self.bot.fetch_user(user.id)
        except AttributeError:
            return await ctx.send(
                f"{self.bot.emote_dict['failed']} User `{user}` does not exist."
            )
        await self.do_avatar(ctx, user, url=user.avatar_url)

    @commands.command(
        brief="Show a user's default avatar.", aliases=["dav", "dpfp", "davatar"]
    )
    async def defaultavatar(self, ctx, *, user: converters.DiscordUser = None):
        """
        Usage:    -defaultavatar [user]
        Aliases:  -dav, -dpfp, davatar
        Examples: -defaultavatar 810377376269205546, -davatar Hypernova
        Output:   Shows an enlarged embed of a user's default avatar.
        Notes:    Will default to yourself if no user is passed.
        """
        if user is None:
            user = ctx.author
        try:
            await self.bot.fetch_user(user.id)
        except AttributeError:
            return await ctx.send(
                f"{self.bot.emote_dict['failed']} User `{user}` does not exist."
            )
        await self.do_avatar(ctx, user, user.default_avatar_url)

    @commands.command(
        aliases=["nick", "setnick"], brief="Edit or reset a user's nickname"
    )
    @commands.guild_only()
    @permissions.has_permissions(manage_nicknames=True)
    async def nickname(self, ctx, user: discord.Member, *, nickname: str = None):
        """
        Usage:      -nickname <member> [nickname]
        Aliases:    -nick, -setnick
        Examples:   -nickname Hypernova NGC, -nickname Hypernova
        Permission: Manage Nicknames
        Output:     Edits a member's nickname on the server.
        Notes:      Nickname will reset if no member is passed.
        """
        if user is None:
            return await ctx.send(
                reference=self.bot.rep_ref(ctx),
                content=f"Usage: `{ctx.prefix}nickname <user> <nickname>`",
            )
        if user.id == ctx.guild.owner.id:
            return await ctx.send(
                f"{self.emote_dict['failed']} User `{user}` is the server owner. I cannot edit the nickname of the server owner."
            )
        try:
            await user.edit(
                nick=nickname,
                reason=utils.responsible(
                    ctx.author, "Nickname edited by command execution"
                ),
            )
            message = f"{self.emote_dict['success']} Nicknamed `{user}: {nickname}`"
            if nickname is None:
                message = f"{self.emote_dict['success']} Reset nickname for `{user}`"
            await ctx.send(message)
        except discord.Forbidden:
            await ctx.send(
                f"{self.emote_dict['failed']} I do not have permission to edit `{user}'s` nickname."
            )

    # command mostly from Alex Flipnote's discord_bot.py bot
    # I'll rewrite his "prettyresults" method to use a paginator later.
    # https://github.com/AlexFlipnote/discord_bot.py

    @commands.group(brief="Find any user using a search.", aliases=["search"])
    @commands.guild_only()
    @permissions.has_permissions(manage_messages=True)
    async def find(self, ctx):
        """
        Usage:      -find <method> <search>
        Alias:      -search
        Examples:   -find name Hecate, -find id 708584008065351681
        Permission: Manage Messages
        Output:     User within your search specification.
        Methods:
            discriminator (Ex: 3523)               (Alias: discrim)
            nickname      (Ex: Heca)               (Alias: nick)
            playing       (Ex: Minecraft)          (Alias: status)
            snowflake     (Ex: 708584008065351681) (Alias: id)
            username      (Ex: Hec)                (Alias: name)
        """
        if ctx.invoked_subcommand is None:
            help_command = self.bot.get_command("help")
            await help_command(ctx, invokercommand="find")

    @find.command(name="playing", aliases=["status"])
    async def find_playing(self, ctx, *, search: str):
        loop = []
        for i in ctx.guild.members:
            if i.activities and (not i.bot):
                for g in i.activities:
                    if g.name and (search.lower() in g.name.lower()):
                        loop.append(f"{i} | {type(g).__name__}: {g.name} ({i.id})")

        await utils.prettyResults(
            ctx,
            "playing",
            f"Found **{len(loop)}** on your search for **{search}**",
            loop,
        )

    @find.command(name="username", aliases=["name"])
    async def find_name(self, ctx, *, search: str):
        loop = [
            f"{i} ({i.id})"
            for i in ctx.guild.members
            if search.lower() in i.name.lower() and not i.bot
        ]
        await utils.prettyResults(
            ctx, "name", f"Found **{len(loop)}** on your search for **{search}**", loop
        )

    @find.command(name="nickname", aliases=["nick"])
    async def find_nickname(self, ctx, *, search: str):
        loop = [
            f"{i.nick} | {i} ({i.id})"
            for i in ctx.guild.members
            if i.nick
            if (search.lower() in i.nick.lower()) and not i.bot
        ]
        await utils.prettyResults(
            ctx, "name", f"Found **{len(loop)}** on your search for **{search}**", loop
        )

    @find.command(name="id")
    async def find_id(self, ctx, *, search: int):
        loop = [
            f"{i} | {i} ({i.id})"
            for i in ctx.guild.members
            if (str(search) in str(i.id)) and not i.bot
        ]
        await utils.prettyResults(
            ctx, "name", f"Found **{len(loop)}** on your search for **{search}**", loop
        )

    @find.command(name="discrim", aliases=["discriminator"])
    async def find_discrim(self, ctx, *, search: str):
        if not len(search) == 4 or not re.compile("^[0-9]*$").search(search):
            return await ctx.send(
                reference=self.bot.rep_ref(ctx),
                content="You must provide exactly 4 digits",
            )

        loop = [f"{i} ({i.id})" for i in ctx.guild.members if search == i.discriminator]
        await utils.prettyResults(
            ctx,
            "discriminator",
            f"Found **{len(loop)}** on your search for **{search}**",
            loop,
        )

    @find.command(name="duplicates", aliases=["dups"])
    async def find_duplicates(self, ctx):
        """Show members with identical names."""
        name_list = []
        for member in ctx.guild.members:
            name_list.append(member.display_name.lower())

        name_list = Counter(name_list)
        name_list = name_list.most_common()

        loop = []
        for name_tuple in name_list:
            if name_tuple[1] > 1:
                loop.append(
                    f"Duplicates: [{str(name_tuple[1]).zfill(2)}] {name_tuple[0]}"
                )

        await utils.prettyResults(
            ctx, "name", f"Found **{len(loop)}** on your search for duplicates", loop
        )

    def _is_hard_to_mention(self, name):
        """Determine if a name is hard to mention."""
        codecs.register_error("newreplace", lambda x: (b" " * (x.end - x.start), x.end))

        encoderes, chars = codecs.getwriter("ascii").encode(name, "newreplace")

        return re.search(br"[^ ][^ ]+", encoderes) is None

    @find.command(name="weird", aliases=["hardmention"])
    async def findhardmention(self, ctx):
        """List members with difficult to mention usernames."""
        loop = [
            member
            for member in ctx.message.guild.members
            if self._is_hard_to_mention(member.name)
        ]
        await utils.prettyResults(
            ctx, "name", f"Found **{len(loop)}** on your search for weird names.", loop
        )

    @commands.command(brief="Show info on a discord snowflake.", aliases=["id"])
    async def snowflake(self, ctx, *, sid=None):
        """
        Usage: -snowflake <id>
        Alias: -id
        Example: -snowflake 810377376269205546
        Output: Date and time of the snowflake's creation
        """
        if not sid.isdigit():
            return await ctx.send(
                reference=self.bot.rep_ref(ctx),
                content=f"Usage: {ctx.prefix}snowflake <id>",
            )

        sid = int(sid)
        timestamp = (
            (sid >> 22) + 1420070400000
        ) / 1000  # python uses seconds not milliseconds
        cdate = datetime.utcfromtimestamp(timestamp)
        msg = "Snowflake created {}".format(
            cdate.strftime("%A, %B %d, %Y at %H:%M:%S UTC")
        )
        return await ctx.send(msg)

    @commands.command(name="permissions", brief="Show a user's permissions.")
    @commands.guild_only()
    async def _permissions(
        self, ctx, member: discord.Member = None, channel: discord.TextChannel = None
    ):
        """
        Usage:  -permissions [member] [channel]
        Output: Shows a member's permissions in a specific channel.
        Notes:
            Will default to yourself and the current channel
            if they are not specified.
        """
        channel = channel or ctx.channel
        if member is None:
            member = ctx.author

        await self.say_permissions(ctx, member, channel)

    async def say_permissions(self, ctx, member, channel):
        permissions = channel.permissions_for(member)
        e = discord.Embed(colour=member.colour)
        avatar = member.avatar_url_as(static_format="png")
        e.set_author(name=str(member), url=avatar)
        allowed, denied = [], []
        for name, value in permissions:
            name = name.replace("_", " ").replace("guild", "server").title()
            if value:
                allowed.append(name)
            else:
                denied.append(name)

        e.add_field(name="Allowed", value="\n".join(allowed))
        e.add_field(name="Denied", value="\n".join(denied))
        await ctx.send(reference=self.bot.rep_ref(ctx), embed=e)

    @commands.command(brief="Shows the raw content of a message.")
    async def raw(self, ctx, *, message: discord.Message):
        """
        Usage: -raw [message id]
        Output: Raw message content
        """

        raw_data = await self.bot.http.get_message(message.channel.id, message.id)

        if message.content:
            content = message.content
            for e in message.content:
                emoji_unicode = e.encode("unicode-escape").decode("ASCII")
                content = content.replace(e, emoji_unicode)
            return await ctx.send(
                "```\n" + "Raw Content\n===========\n\n" + content + "\n```"
            )

        transformer = pprint.pformat
        desc = ""
        for field_name in ("embeds", "attachments"):
            data = raw_data[field_name]

            if not data:
                continue

            total = len(data)
            for current, item in enumerate(data, start=1):
                title = f"Raw {field_name} ({current}/{total})"
                desc += f"{title}\n\n{transformer(item)}\n"
        p = pagination.MainMenu(pagination.TextPageSource(desc, prefix="```"))

        try:
            await p.start(ctx)
        except menus.MenuError as e:
            await ctx.send(str(e))

    @commands.command(brief="Snipe a deleted message.", aliases=["retrieve"])
    @commands.guild_only()
    async def snipe(self, ctx, *, member: discord.Member = None):
        """
        Usage: -snipe [user]
        Alias: -retrieve
        Output: Fetches a deleted message
        Notes:
            Will fetch a messages sent by a specific user if specified
        """
        if member is None:
            query = """SELECT author_id, message_id, content, timestamp FROM messages WHERE channel_id = $1 AND deleted = True ORDER BY unix DESC;"""
            result = await self.bot.cxn.fetchrow(query, ctx.channel.id) or None
        else:
            query = """SELECT author_id, message_id, content, timestamp FROM messages WHERE channel_id = $1 AND author_id = $2 AND deleted = True ORDER BY unix DESC;"""
            result = (
                await self.bot.cxn.fetchrow(query, ctx.channel.id, member.id) or None
            )

        if result is None:
            return await ctx.send(
                f"{self.bot.emote_dict['error']} There is nothing to snipe."
            )

        author = result[0]
        message_id = result[1]
        content = result[2]
        timestamp = result[3]

        author = await self.bot.fetch_user(author)

        if str(content).startswith("```"):
            content = f"**__Message Content__**\n {str(content)}"
        else:
            content = f"**__Message Content__**\n ```fix\n{str(content)}```"

        embed = discord.Embed(
            description=f"**Author:**  {author.mention}, **ID:** `{author.id}`\n"
            f"**Channel:** {ctx.channel.mention} **ID:** `{ctx.channel.id}`\n"
            f"**Server:** `{ctx.guild.name}` **ID:** `{ctx.guild.id},`\n\n"
            f"**Sent at:** `{timestamp}`\n\n"
            f"{content}",
            color=self.bot.constants.embed,
            timestamp=datetime.utcnow(),
        )
        embed.set_author(
            name="Deleted Message Retrieved",
            icon_url="https://media.discordapp.net/attachments/506838906872922145/603642595419357190/messagedelete.png",
        )
        embed.set_footer(text=f"Message ID: {message_id}")
        await ctx.send(reference=self.bot.rep_ref(ctx), embed=embed)

    @commands.command(brief="Emoji usage tracking.")
    @commands.guild_only()
    async def emojistats(self, ctx):
        """
        Usage -emojistats
        Output: Get detailed emoji usage stats.
        """
        async with ctx.channel.typing():
            msg = await ctx.send(
                f"{self.bot.emote_dict['loading']} **Collecting Emoji Statistics**"
            )
            query = """
                    SELECT (emoji_id, total)
                    FROM emojistats
                    WHERE server_id = $1
                    ORDER BY total DESC;
                    """

            emoji_list = []
            result = await self.bot.cxn.fetch(query, ctx.guild.id)
            for x in result:
                try:
                    emoji = await ctx.guild.fetch_emoji(int(x[0][0]))
                    emoji_list.append((emoji, x[0][1]))

                except Exception:
                    continue

            p = pagination.SimplePages(
                entries=["{}: Uses: {}".format(e[0], e[1]) for e in emoji_list],
                per_page=15,
            )
            p.embed.title = f"Emoji usage stats in **{ctx.guild.name}**"
            await msg.delete()
            try:
                await p.start(ctx)
            except menus.MenuError as e:
                await ctx.send(e)

    @commands.command(brief="Get usage stats on an emoji.")
    async def emoji(self, ctx, emoji: converters.SearchEmojiConverter = None):
        """
        Usage: -emoji <custom emoji>
        Output: Usage stats on the passed emoji
        """
        async with ctx.channel.typing():
            if emoji is None:
                return await ctx.send(
                    reference=self.bot.rep_ref(ctx),
                    content=f"Usage: `{ctx.prefix}emoji <custom emoji>`",
                )
            emoji_id = emoji.id

            msg = await ctx.send(
                f"{self.bot.emote_dict['loading']} **Collecting Emoji Statistics**"
            )
            query = f"""SELECT (author_id, content) FROM messages WHERE content ~ '<a?:.+?:{emoji_id}>';"""

            stuff = await self.bot.cxn.fetch(query)

            emoji_users = []
            for x in stuff:
                emoji_users.append(x[0][0])

            fat_msg = ""
            for x in stuff:
                fat_msg += x[0][1]

            emoji_users = Counter(emoji_users).most_common()

            matches = re.compile(f"<a?:.+?:{emoji_id}>").findall(fat_msg)
            total_uses = len(matches)

            p = pagination.SimplePages(
                entries=[
                    "`{}`: Uses: {}".format(self.bot.get_user(u[0]), u[1])
                    for u in emoji_users
                ],
                per_page=15,
            )
            p.embed.title = f"Emoji usage stats for {emoji} (Total: {total_uses})"
            await msg.delete()
            try:
                await p.start(ctx)
            except menus.MenuError as e:
                await ctx.send(e)

    @commands.command(
        brief="Remove your timezone.",
        aliases=["rmtz", "removetz", "removetimzone", "rmtimezone", "remtimezone"],
    )
    async def remtz(self, ctx):
        """Remove your timezone"""

        await self.bot.cxn.execute(
            "DELETE FROM usertime WHERE user_id = $1;", ctx.author.id
        )
        await ctx.send(
            f"{self.bot.emote_dict['success']} Your timezone has been removed."
        )

    @commands.command(brief="Set your timezone.", aliases=["settimezone", "settime"])
    async def settz(self, ctx, *, tz_search=None):
        """List all the supported timezones."""

        msg = ""
        if tz_search is None:
            title = "Available Timezones"
            entry = [x for x in pytz.all_timezones]
            p = pagination.SimplePages(
                entry,
                per_page=20,
                index=False,
                desc_head="```prolog\n",
                desc_foot="```",
            )
            p.embed.title = title
            try:
                await p.start(ctx)
            except menus.MenuError as e:
                await ctx.send(e)
        else:
            tz_list = utils.disambiguate(tz_search, pytz.all_timezones, None, 5)
            if not tz_list[0]["ratio"] == 1:
                edit = True
                tz_list = [x["result"] for x in tz_list]
                index, message = await pagination.Picker(
                    embed_title="Select one of the 5 closest matches.",
                    list=tz_list,
                    ctx=ctx,
                ).pick(embed=True, syntax="prolog")

                if index < 0:
                    return await message.edit(
                        content=f"{self.bot.emote_dict['info']} Timezone selection cancelled.",
                        embed=None,
                    )

                selection = tz_list[index]
            else:
                edit = False
                selection = tz_list[0]["result"]

            query = """
                    INSERT INTO usertime
                    VALUES ($1, $2)
                    ON CONFLICT (user_id)
                    DO UPDATE SET timezone = $2
                    WHERE usertime.user_id = $1;
                    """
            await self.bot.cxn.execute(query, ctx.author.id, selection)
            msg = f"{self.bot.emote_dict['success']} Timezone set to `{selection}`"
            if edit:
                await message.edit(content=msg, embed=None)
            else:
                await ctx.send(msg)

    @commands.command(brief="See a member's timezone.", aliases=["tz"])
    async def timezone(self, ctx, *, member: converters.DiscordUser = None):
        """See a member's timezone."""

        if member is None:
            member = ctx.author

        query = """
                SELECT timezone
                FROM usertime
                WHERE user_id = $1;
                """
        timezone = await self.bot.cxn.fetchval(query, member.id) or None
        if timezone is None:
            return await ctx.send(
                f"{self.bot.emote_dict['error']} `{member}` has not set their timezone. "
                f"Use the `{ctx.prefix}settz [Region/City]` command."
            )

        await ctx.send(
            reference=self.bot.rep_ref(ctx),
            content=f"`{member}'` timezone is *{timezone}*",
        )

    @commands.command(brief="Show a user's current time.")
    async def time(self, ctx, *, member: discord.Member = None):
        """
        Usage: -time [member]
        Output: Time for the passed user, if set.
        Notes: Will default to you if no user is specified
        """
        timenow = utils.getClockForTime(datetime.utcnow().strftime("%I:%M %p"))
        if member is None:
            member = ctx.author

        query = """
                SELECT timezone
                FROM usertime
                WHERE user_id = $1;
                """
        tz = await self.bot.cxn.fetchval(query, member.id) or None
        if tz is None:
            msg = (
                f"`{member}` hasn't set their timezone yet. "
                f"They can do so with `{ctx.prefix}settz [Region/City]` command.\n"
                f"The current UTC time is **{timenow}**."
            )
            await ctx.send(msg)
            return

        t = self.getTimeFromTZ(tz)
        if t is None:
            await ctx.send(
                f"{self.bot.emote_dict['failed']} I couldn't find that timezone."
            )
            return
        t["time"] = utils.getClockForTime(t["time"])
        if member:
            msg = f'It\'s currently **{t["time"]}** where {member.display_name} is.'
        else:
            msg = "{} is currently **{}**".format(t["zone"], t["time"])

        await ctx.send(msg)

    def getTimeFromTZ(self, tz, t=None):
        # Assume sanitized zones - as they're pulled from pytz
        # Let's get the timezone list
        tz_list = utils.disambiguate(tz, pytz.all_timezones, None, 3)
        if not tz_list[0]["ratio"] == 1:
            # We didn't find a complete match
            return None
        zone = pytz.timezone(tz_list[0]["result"])
        if t is None:
            zone_now = datetime.now(zone)
        else:
            zone_now = t.astimezone(zone)
        return {"zone": tz_list[0]["result"], "time": zone_now.strftime("%I:%M %p")}

    @commands.command(brief="Shorten a URL.")
    async def shorten(self, ctx, url=None):
        """
        Usage: -shorten <url>
        Output:
            A short url that will redirect to
            the url that was passed.
        """
        if url is None:
            return await ctx.send(
                reference=self.bot.rep_ref(ctx),
                content=f"Usage: `{ctx.prefix}shorten <url>`",
            )
        params = {"access_token": self.bot.constants.bitly, "longUrl": url}

        response = await self.bot.get(
            "https://api-ssl.bitly.com/v3/shorten", params=params
        )
        resp = json.loads(response)
        if resp["status_code"] != 200:
            return await ctx.send(
                reference=self.bot.rep_ref(ctx),
                content=f"{self.bot.emote_dict['failed']} Invalid URL received.",
            )
        else:
            await ctx.send(
                reference=self.bot.rep_ref(ctx),
                content=f"{self.bot.emote_dict['success']} Successfully shortened URL:\t"
                "<{}>".format(resp["data"]["url"]),
            )

    @commands.command(
        brief="Get the time of any location", aliases=["worldclock", "worldtime"]
    )
    async def clock(self, ctx, *, place=None):
        """
        Usage: -clock <location>
        Aliases: -worldclock, -worldtime
        Examples:
            -clock Los Angeles
            -clock Netherlands
        Output:
            The current time in the specified location
        Notes:
            Can accept cities, states, provinces,
            and countries as valid locations
        """
        if place is None:
            return await ctx.send(
                reference=self.bot.rep_ref(ctx),
                content=f"Usage: `{ctx.prefix}clock <location>`",
            )
        try:
            city_name = re.sub(r"([^\s\w]|_)+", "", place)
            location = self.geo.geocode(city_name)
            if location == None:
                await ctx.send(
                    reference=self.bot.rep_ref(ctx),
                    content=f"{self.bot.emote_dict['failed']} Invalid location.",
                )

            r = await self.bot.get(
                "http://api.timezonedb.com/v2.1/get-time-zone?key={}&format=json&by=position&lat={}&lng={}".format(
                    self.bot.constants.timezonedb, location.latitude, location.longitude
                )
            )
            request = json.loads(r)

            if request["status"] != "OK":
                await ctx.send(reference=self.bot.rep_ref(ctx), content="Fuck.")
            else:
                time = datetime.fromtimestamp(request["timestamp"])
                em = discord.Embed(
                    title=f"Time in {location}",
                    description="**{}**\n\t{} ({})\n {} ({})".format(
                        request["formatted"],
                        request["abbreviation"],
                        request["zoneName"],
                        request["countryName"],
                        request["countryCode"],
                    ),
                    color=self.bot.constants.embed,
                )
                await ctx.send(reference=self.bot.rep_ref(ctx), embed=em)
        except Exception as e:
            await ctx.send(e)

    @commands.command(aliases=["sw"])
    async def stopwatch(self, ctx):
        """Start or stop a stopwatch."""
        author = ctx.author
        if author.id not in self.stopwatches:
            self.stopwatches[author.id] = int(time.perf_counter())
            await ctx.send(f"{self.bot.emote_dict['stopwatch']} Stopwatch started!")
        else:
            tmp = abs(self.stopwatches[author.id] - int(time.perf_counter()))
            tmp = str(timedelta(seconds=tmp))
            await ctx.send(
                f"{self.bot.emote_dict['stopwatch']} Stopwatch stopped! Time: **{tmp}**"
            )
            self.stopwatches.pop(author.id, None)

    @commands.command(aliases=["math","calc"], brief="Calculate a math formula.")
    async def calculate(self, ctx, *, formula=None):
        """
        Usage: -calculate <formula>
        Aliases: -calc, -math
        """
        if formula is None:
            return await ctx.send("Usage: `{}calculate <formula>`".format(ctx.prefix))
        formula = formula.replace("*", "x")

        try:
            answer = NumericStringParser().eval(formula)
            await ctx.message.add_reaction(self.bot.emote_dict['success'])
        except Exception:
            msg = '{} I couldn\'t parse "{}"\n\n'.format(
                self.bot.emote_dict['failed'],
                formula.replace("*", "\\*").replace("`", "\\`").replace("_", "\\_")
            )
            msg += "I understand the following syntax:\n```fix\n"
            msg += "expop   :: '^'\n"
            msg += "multop  :: 'x' | '*' | '/'\n"
            msg += "addop   :: '+' | '-'\n"
            msg += "integer :: ['+' | '-'] '0'..'9'+\n"
            msg += "atom    :: PI | E | real | fn '(' expr ')' | '(' expr ')'\n"
            msg += "factor  :: atom [ expop factor ]*\n"
            msg += "term    :: factor [ multop factor ]*\n"
            msg += "expr    :: term [ addop term ]*```"
            return await ctx.send(msg)

        if int(answer) == answer:
            # Check if it's a whole number and cast to int if so
            answer = int(answer)

        # Say message
        await ctx.send("{} = {}".format(formula, answer))


class NumericStringParser(object):
    """
    Most of this code comes from the fourFn.py pyparsing example
    """

    def pushFirst(self, strg, loc, toks):
        self.exprStack.append(toks[0])

    def pushUMinus(self, strg, loc, toks):
        if toks and toks[0] == "-":
            self.exprStack.append("unary -")

    def __init__(self):
        """
        expop   :: '^'
        multop  :: 'x' | '*' | '/'
        addop   :: '+' | '-'
        integer :: ['+' | '-'] '0'..'9'+
        atom    :: PI | E | real | fn '(' expr ')' | '(' expr ')'
        factor  :: atom [ expop factor ]*
        term    :: factor [ multop factor ]*
        expr    :: term [ addop term ]*
        """
        point = Literal(".")
        e = CaselessLiteral("E")
        fnumber = Combine(
            Word("+-" + nums, nums)
            + Optional(point + Optional(Word(nums)))
            + Optional(e + Word("+-" + nums, nums))
        )
        ident = Word(alphas, alphas + nums + "_$")
        plus = Literal("+")
        minus = Literal("-")
        mult = Literal("x")
        div = Literal("/")
        lpar = Literal("(").suppress()
        rpar = Literal(")").suppress()
        addop = plus | minus
        multop = mult | div
        expop = Literal("^")
        pi = CaselessLiteral("PI")
        expr = Forward()
        atom = (
            (
                Optional(oneOf("- +"))
                + (pi | e | fnumber | ident + lpar + expr + rpar).setParseAction(
                    self.pushFirst
                )
            )
            | Optional(oneOf("- +")) + Group(lpar + expr + rpar)
        ).setParseAction(self.pushUMinus)
        # by defining exponentiation as "atom [ ^ factor ]..." instead of
        # "atom [ ^ atom ]...", we get right-to-left exponents, instead of left-to-right
        # that is, 2^3^2 = 2^(3^2), not (2^3)^2.
        factor = Forward()
        factor << atom + ZeroOrMore((expop + factor).setParseAction(self.pushFirst))
        term = factor + ZeroOrMore((multop + factor).setParseAction(self.pushFirst))
        expr << term + ZeroOrMore((addop + term).setParseAction(self.pushFirst))
        # addop_term = ( addop + term ).setParseAction( self.pushFirst )
        # general_term = term + ZeroOrMore( addop_term ) | OneOrMore( addop_term)
        # expr <<  general_term
        self.bnf = expr
        # map operator symbols to corresponding arithmetic operations
        epsilon = 1e-12
        self.opn = {
            "+": operator.add,
            "-": operator.sub,
            "x": operator.mul,
            "/": operator.truediv,
            "^": operator.pow,
        }
        self.fn = {
            "sin": math.sin,
            "cos": math.cos,
            "tan": math.tan,
            "abs": abs,
            "trunc": lambda a: int(a),
            "round": round,
            "sgn": lambda a: abs(a) > epsilon and cmp_to_key(a, 0) or 0,
        }

    def evaluateStack(self, s):
        op = s.pop()
        if op == "unary -":
            return -self.evaluateStack(s)
        if op in "+-x/^":
            op2 = self.evaluateStack(s)
            op1 = self.evaluateStack(s)
            return self.opn[op](op1, op2)
        elif op == "PI":
            return math.pi  # 3.1415926535
        elif op == "E":
            return math.e  # 2.718281828
        elif op in self.fn:
            return self.fn[op](self.evaluateStack(s))
        elif op[0].isalpha():
            return 0
        else:
            return float(op)

    def eval(self, num_string, parseAll=True):
        self.exprStack = []
        results = self.bnf.parseString(num_string, parseAll)
        val = self.evaluateStack(self.exprStack[:])
        return val
