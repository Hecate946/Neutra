import discord
from discord.ext import commands, menus
import codecs
import re
import datetime
import pprint
from collections import Counter

from utilities import utils, permissions, pagination, converters


def setup(bot):
    bot.add_cog(Utility(bot))


class Utility(commands.Cog):
    """
    Module for general utilities
    """

    def __init__(self, bot):
        self.bot = bot

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
                return await ctx.send("You cannot move my master.")
            if (
                ctx.author.top_role.position < target.top_role.position
                and ctx.author.id not in self.bot.constants.owners
            ):
                return await ctx.send("You cannot move other staff members")
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
        await ctx.send(f"{self.emote_dict['success']} Purged {channel.mention}.")

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
            return await ctx.send(f"Usage: `{ctx.prefix}vckick <target> [target]...`")
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
        await ctx.send(embed=embed)

    @commands.command(brief="Show a user's avatar.", aliases=["av", "pfp"])
    async def avatar(self, ctx, *, user: converters.DiscordUser = None):
        """
        Usage:    -avatar [user]
        Aliases:  -av, -pfp
        Examples: -avatar 810377376269205546, -avatar NGC0000
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
        Examples: -defaultavatar 810377376269205546, -davatar NGC0000
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
        Examples:   -nickname NGC0000 NGC, -nickname NGC0000
        Permission: Manage Nicknames
        Output:     Edits a member's nickname on the server.
        Notes:      Nickname will reset if no member is passed.
        """
        if user is None:
            return await ctx.send(f"Usage: `{ctx.prefix}nickname <user> <nickname>`")
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
            return await ctx.send("You must provide exactly 4 digits")

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
        print(loop)
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
            return await ctx.send(f"Usage: {ctx.prefix}snowflake <id>")

        sid = int(sid)
        timestamp = (
            (sid >> 22) + 1420070400000
        ) / 1000  # python uses seconds not milliseconds
        cdate = datetime.datetime.utcfromtimestamp(timestamp)
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
        await ctx.send(embed=e)

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
            timestamp=datetime.datetime.utcnow(),
        )
        embed.set_author(
            name="Deleted Message Retrieved",
            icon_url="https://media.discordapp.net/attachments/506838906872922145/603642595419357190/messagedelete.png",
        )
        embed.set_footer(text=f"Message ID: {message_id}")
        await ctx.send(embed=embed)
