import discord
import re
import os
import requests
import io

from collections import Counter
from discord.ext import commands, menus

from utilities import pagination, converters, utils, permissions, image


def setup(bot):
    bot.add_cog(Emojis(bot))


class Emojis(commands.Cog):
    """
    Module for emoji functions
    """

    def __init__(self, bot):
        self.bot = bot

    async def query(self, url, method="get", res_method="text", *args, **kwargs):
        async with getattr(self.bot.session, method.lower())(
            url, *args, **kwargs
        ) as res:
            return await getattr(res, res_method)()

    async def get(self, url, *args, **kwargs):
        return await self.query(url, "get", *args, **kwargs)

    async def post(self, url, *args, **kwargs):
        return await self.query(url, "post", *args, **kwargs)

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

        # @commands.command(brief="Emoji usage tracking.")
        # @commands.guild_only()
        # async def emojistats(self, ctx, member: discord.Member = None):
        """
        This was how I used to do the emoji stats, 
        I would regex search the entire messages table
        It saves quite a bit of space on the db server, 
        but it takes far too long to be practical
        """

    #     async with ctx.channel.typing():
    #         if member is None:
    #             msg = await ctx.send(f"{self.bot.emote_dict['loading']} **Collecting Emoji Statistics**")
    #             query = """SELECT content FROM messages WHERE content ~ '<a?:.+?:([0-9]{15,21})>' AND server_id = $1;"""

    #             stuff = await self.bot.cxn.fetch(query, ctx.guild.id)
    #             fat_msg = ""
    #             for x in stuff:
    #                 fat_msg += '\n'.join(x)
    #             matches = EMOJI_REGEX.findall(fat_msg)

    #             emoji_list = []
    #             for x in matches:
    #                 try:
    #                     emoji = await ctx.guild.fetch_emoji(int(x))
    #                 except discord.NotFound:
    #                     continue
    #                 emoji_list.append(emoji)

    #             emoji_list = Counter(emoji_list)
    #             emoji_list = emoji_list.most_common()

    #             p = pagination.SimplePages(entries = ['{}: Uses: {}'.format(e[0], e[1]) for e in emoji_list], per_page = 15)
    #             p.embed.title = f"Emoji usage stats in **{ctx.guild.name}**"
    #             await msg.delete()
    #             try:
    #                 await p.start(ctx)
    #             except menus.MenuError as e:
    #                 await ctx.send(e)
    #         else:
    #             msg = await ctx.send(f"{self.bot.emote_dict['loading']} **Collecting Emoji Statistics**")
    #             query = """SELECT content FROM messages WHERE content ~ '<a?:.+?:([0-9]{15,21})>' AND server_id = $1 AND author_id = $2;"""

    #             stuff = await self.bot.cxn.fetch(query, ctx.guild.id, member.id)
    #             fat_msg = ""
    #             for x in stuff:
    #                 fat_msg += '\n'.join(x)
    #             matches = EMOJI_REGEX.findall(fat_msg)
    #             emoji_list = []

    #             for x in matches:
    #                 try:
    #                     emoji = await ctx.guild.fetch_emoji(int(x))
    #                 except discord.NotFound:
    #                     continue
    #                 emoji_list.append(emoji)

    #             emoji_list = Counter(emoji_list)
    #             emoji_list = emoji_list.most_common()
    #             p = pagination.SimplePages(entries = ['{}: Uses: {}'.format(e[0], e[1]) for e in emoji_list], per_page = 15)
    #             p.embed.title = f"Emoji usage stats for **{member.display_name}**"
    #             await msg.delete()
    #             try:
    #                 await p.start(ctx)
    #             except menus.MenuError as e:
    #                 await ctx.send(e)

    @commands.command(brief="Get usage stats on an emoji.")
    async def emoji(self, ctx, emoji: converters.SearchEmojiConverter = None):
        """
        Usage: -emoji <custom emoji>
        Output: Usage stats on the passed emoji
        """
        async with ctx.channel.typing():
            if emoji is None:
                return await ctx.send(f"Usage: `{ctx.prefix}emoji <custom emoji>`")
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

    def _get_emoji_url(self, emoji):
        if len(emoji) < 3:
            # Emoji is likely a built-in like :)
            h = "-".join([hex(ord(x)).lower()[2:] for x in emoji])
            return (
                "https://github.com/twitter/twemoji/raw/master/assets/72x72/{}.png".format(
                    h
                ),
                h,
            )
        # Must be a custom emoji
        emojiparts = emoji.replace("<", "").replace(">", "").split(":") if emoji else []
        if not len(emojiparts) == 3:
            return None
        emoji_obj = discord.PartialEmoji(
            animated=len(emojiparts[0]) > 0, name=emojiparts[1], id=emojiparts[2]
        )
        return (emoji_obj.url, emoji_obj.name)

    def _get_emoji_mention(self, emoji):
        return "<{}:{}:{}>".format("a" if emoji.animated else "", emoji.name, emoji.id)

    async def be(self, ctx, emoji=None):
        """Outputs the passed emoji... but bigger!"""
        if emoji is None:
            await ctx.send("Usage: `{}emoji [emoji]`".format(ctx.prefix))
            return
        # Get the emoji
        emoji_url = self._get_emoji_url(emoji)
        if not emoji_url:
            return await ctx.send("Usage: `{}emoji [emoji]`".format(ctx.prefix))
        f = await image.download(emoji_url[0])
        if not f:
            return await ctx.send("I could not access that emoji.")
        await ctx.send(file=discord.File(f))
        os.remove(f)

    def find_emoji(self, msg):
        msg = re.sub("<a?:(.+):([0-9]+)>", "\\2", msg)
        color_modifiers = [
            "1f3fb",
            "1f3fc",
            "1f3fd",
            "1f44c",
            "1f3fe",
            "1f3ff",
        ]  # these colors arent in twemoji

        name = None

        for guild in self.bot.guilds:
            for emoji in guild.emojis:
                if msg.strip().lower() in emoji.name.lower():
                    name = emoji.name + (".gif" if emoji.animated else ".png")
                    url = emoji.url
                    id = emoji.id
                    guild_name = guild.name
                if msg.strip() in (str(emoji.id), emoji.name):
                    name = emoji.name + (".gif" if emoji.animated else ".png")
                    url = emoji.url
                    return name, url, emoji.id, guild.name
        if name:
            return name, url, id, guild_name

        codepoint_regex = re.compile("([\d#])?\\\\[xuU]0*([a-f\d]*)")
        unicode_raw = msg.encode("unicode-escape").decode("ascii")
        codepoints = codepoint_regex.findall(unicode_raw)
        if codepoints == []:
            return "", "", "", ""

        if len(codepoints) > 1 and codepoints[1][1] in color_modifiers:
            codepoints.pop(1)

        if codepoints[0][0] == "#":
            emoji_code = "23-20e3"
        elif codepoints[0][0] == "":
            codepoints = [x[1] for x in codepoints]
            emoji_code = "-".join(codepoints)
        else:
            emoji_code = "3{}-{}".format(codepoints[0][0], codepoints[0][1])
        url = "https://raw.githubusercontent.com/astronautlevel2/twemoji/gh-pages/128x128/{}.png".format(
            emoji_code
        )
        name = "emoji.png"
        return name, url, "N/A", "Official"

    @commands.command(
        brief="View enlarged emojis.",
        aliases=["bigemotes", "bigemojis", "bigemote", "bem"],
    )
    async def bigemoji(self, ctx, *, emojis=None):
        """
        Usage: bigemoji [info] <emojis>
        Aliases: -bigemote, -bigemojis, -bigemotes, -be
        Output: Large version of the passed emoji
        Notes:
            Pass the optional info argument to show
            the emoji's server, name, and url.
        """
        if emojis is None:
            return await ctx.send(f"Usage: `{ctx.prefix}bigemoji [info] <emojis>`")
        msg = emojis

        emojis = msg.split()
        if msg.startswith("info "):
            emojis = emojis[1:]
            get_guild = True
        else:
            get_guild = False

        if len(emojis) > 5:
            raise commands.BadArgument("Maximum of 5 emojis at a time.")

        images = []
        for emoji in emojis:
            name, url, id, guild = self.find_emoji(emoji)
            if url == "":
                downloader = self.bot.get_command("be")
                await downloader(ctx, emoji)
            response = requests.get(url, stream=True)
            if response.status_code == 404:
                await self.be(ctx, emoji)
                continue

            img = io.BytesIO()
            for block in response.iter_content(1024):
                if not block:
                    break
                img.write(block)
            img.seek(0)
            images.append((guild, str(id), url, discord.File(img, name)))

        for (guild, id, url, fp) in images:
            if ctx.channel.permissions_for(ctx.author).attach_files:
                if get_guild:
                    await ctx.send(
                        "**ID:** {}\n**Server:** {}\n**URL: {}**".format(id, guild, url)
                    )
                    await ctx.send(file=fp)
                else:
                    await ctx.send(file=fp)
            else:
                if get_guild:
                    await ctx.send(
                        "**ID:** {}\n**Server:** {}\n**URL: {}**".format(id, guild, url)
                    )
                    await ctx.send(url)
                else:
                    await ctx.send(url)
            fp.close()

    @commands.command(
        aliases=["emojisteal", "emotecopy", "emotesteal"],
        brief="Copy an emoji from another server.",
    )
    @commands.guild_only()
    @permissions.has_permissions(manage_emojis=True)
    async def emojicopy(self, ctx, *, msg):
        """Copy a custom emoji from another server and add it."""
        msg = re.sub("<:(.+):([0-9]+)>", "\\2", msg)

        match = None
        exact_match = False
        for guild in self.bot.guilds:
            if ctx.author not in guild.members:
                continue
            for emoji in guild.emojis:
                if msg.strip().lower() in str(emoji):
                    match = emoji
                if msg.strip() in (str(emoji.id), emoji.name):
                    match = emoji
                    exact_match = True
                    break
            if exact_match:
                break

        if not match:
            return await ctx.send(
                f"{self.bot.emote_dict['failed']} No emoji found in servers you share with me."
            )
        response = await self.get(str(match.url), res_method="read")
        try:
            emoji = await ctx.guild.create_custom_emoji(name=match.name, image=response)
            await ctx.send(
                f"{self.bot.emote_dict['success']} Successfully added the emoji {emoji.name} <{'a' if emoji.animated else ''}:{emoji.name}:{emoji.id}>"
            )
        except discord.HTTPException:
            await ctx.send(f"{self.bot.emote_dict['failed']} No available emoji slots.")

    @commands.command(
        brief="Add an emoji to the server.",
        aliases=["addemoji", "addemote", "emoteadd"],
    )
    @commands.guild_only()
    @permissions.bot_has_permissions(manage_emojis=True)
    @permissions.has_permissions(manage_emojis=True)
    async def emojiadd(self, ctx, *, emoji=None, name=None):
        """Adds the passed emoji, url, or attachment as a custom emoji."""

        if not len(ctx.message.attachments) and emoji == name is None:
            return await ctx.send(
                "Usage: `{}addemoji [emoji, url, attachment] [name]`".format(ctx.prefix)
            )

        if len(ctx.message.attachments):
            name = emoji
            emoji = " ".join([x.url for x in ctx.message.attachments])
            if name:
                emoji += " " + name

        emojis_to_add = []
        last_name = []
        for x in emoji.split():
            # Check for a url
            urls = utils.get_urls(x)
            if len(urls):
                url = (urls[0], os.path.basename(urls[0]).split(".")[0])
            else:
                # Check for an emoji
                url = self._get_emoji_url(x)
                if not url:
                    # Gotta be a part of the name - add it
                    last_name.append(x)
                    continue
            if len(emojis_to_add) and last_name:
                # Update the previous name if need be
                emojis_to_add[-1][1] = "".join(
                    [z for z in "_".join(last_name) if z.isalnum() or z == "_"]
                )
            # We have a valid url or emoji here - let's make sure it's unique
            if not url[0] in [x[0] for x in emojis_to_add]:
                emojis_to_add.append([url[0], url[1]])
            # Reset last_name
            last_name = []
        if len(emojis_to_add) and last_name:
            # Update the final name if need be
            emojis_to_add[-1][1] = "".join(
                [z for z in "_".join(last_name) if z.isalnum() or z == "_"]
            )
        if not emojis_to_add:
            return await ctx.send(
                f"Usage: `{ctx.prefix}addemoji [emoji, url, attachment] [name]`"
            )
        # Now we have a list of emojis and names
        added_emojis = []
        allowed = len(emojis_to_add) if len(emojis_to_add) <= 10 else 10
        omitted = (
            " ({} omitted, beyond the limit of {})".format(len(emojis_to_add) - 10, 10)
            if len(emojis_to_add) > 10
            else ""
        )
        message = await ctx.send(
            "Adding {} emoji{}{}...".format(
                allowed, "" if allowed == 1 else "s", omitted
            )
        )
        for emoji_to_add in emojis_to_add[:10]:
            # Let's try to download it
            emoji, e_name = emoji_to_add
            f = await self.get(str(emoji), res_method="read")
            if not f:
                await message.edit(
                    content=f"{self.bot.emote_dict['failed']} Could not read emoji."
                )
                continue
            # format
            if not e_name.replace("_", ""):
                continue
            # Create the emoji and save it
            try:
                new_emoji = await ctx.guild.create_custom_emoji(
                    name=e_name,
                    image=f,
                    roles=None,
                    reason="Added by {}#{}".format(
                        ctx.author.name, ctx.author.discriminator
                    ),
                )
            except discord.HTTPException:
                await message.edit(
                    content=f"{self.bot.emote_dict['failed']} Out of emoji slots."
                )
                continue
            except Exception:
                continue
            added_emojis.append(new_emoji)
        if len(added_emojis):
            msg = f"{self.bot.emote_dict['success']} Created {len(added_emojis)} emote{'' if len(added_emojis) == 1 else 's'}:"
            msg += "\n\n"
            emoji_text = [
                "{} - `:{}:`".format(self._get_emoji_mention(x), x.name)
                for x in added_emojis
            ]
            msg += "\n".join(emoji_text)
            await message.edit(content=msg)

    @commands.command(
        aliases=["emoteremove", "removeemoji", "removeemote"],
        brief="Remove an emoji from the server.",
    )
    @commands.guild_only()
    @permissions.bot_has_permissions(manage_emojis=True)
    @permissions.has_permissions(manage_emojis=True)
    async def emojiremove(self, ctx, name):
        """Remove an emoji from the current server."""
        emotes = [x for x in ctx.guild.emojis if x.name == name]
        emote_length = len(emotes)
        if not emotes:
            return await ctx.send(
                "No emotes with that name could be found on this server."
            )
        for emote in emotes:
            await emote.delete()
        if emote_length == 1:
            await ctx.send("Successfully removed the {} emoji!".format(name))
        else:
            await ctx.send(
                "Successfully removed {} emoji with the name {}.".format(
                    emote_length, name
                )
            )

    @commands.command(aliases=["se", "nitro"], brief="Send an emoji using the bot.")
    async def sendemoji(self, ctx, msg: str = None):
        """Sends an emoji"""
        if msg is None:
            await ctx.send("Usage: `{}emoji [emoji]`".format(ctx.prefix))
            return

        msg = re.sub("<:(.+):([0-9]+)>", "\\2", msg)

        match = None
        exact_match = False
        for guild in self.bot.guilds:
            for emoji in guild.emojis:
                if msg.strip().lower() in str(emoji):
                    match = emoji
                if msg.strip() in (str(emoji.id), emoji.name):
                    match = emoji
                    exact_match = True
                    break
            if exact_match:
                break

        if not match:
            return await ctx.send("Could not find emoji.")

        # await ctx.send(match.url)
        await ctx.send(match)

    @commands.command(aliases=["listemotes"], brief="Shows all server emojis")
    async def listemojis(self, ctx):
        """Displays all emotes avaiable on a server."""
        title = "Available Emojis"
        width = max([len(x.name) for x in ctx.guild.emojis])
        entry = [f"{x.name: <{width}}: {x.id}" for x in ctx.guild.emojis]
        p = pagination.SimplePages(
            entry, per_page=20, index=False, desc_head="```yaml\n", desc_foot="```"
        )
        p.embed.title = title
        try:
            await p.start(ctx)
        except menus.MenuError as e:
            await ctx.send(e)

    # TODO use TextPageSource and make this decent.

    # @commands.command(aliases=['es'], brief="Scan all servers for an emoji.")
    # async def emojiscan(self, ctx, msg):
    #     """Scan all servers for a certain emote"""
    #     bool = None
    #     servers = ""
    #     emote = msg.split(":")[1] if msg.startswith("<") else msg
    #     for guild in self.bot.guilds:
    #         if ctx.author not in guild.members:
    #             continue
    #         if len(servers + "{}\n".format(guild.name)) > 2000:
    #             bool = False
    #             break
    #         for emoji in guild.emojis:
    #             if emoji.name == emote:
    #                 servers += guild.name + "\n"
    #     if servers is None:
    #         await ctx.send("That emote is not on any of your servers.")
    #     else:
    #         if len(servers) <= 1964 and bool is False:
    #             servers += "**Could not print the rest, sorry.**"
    #         elif bool is False:
    #             bool = True
    #         try:
    #             embed = discord.Embed(title="Servers with the {} emote".format(msg), color=self.bot.constants.embed)
    #             embed.description = servers
    #             await ctx.send(embed=embed)
    #         except Exception:
    #             await ctx.send("```{}```".format(servers))
    #         if bool is True:
    #             await ctx.send("**Could not print the rest, sorry**")
