import typing
import discord
import asyncio
import re
from discord.ext import commands
from collections import Counter
from utilities import decorators
from utilities import converters
from utilities import checks
from utilities import helpers


def setup(bot):
    bot.add_cog(Server(bot))


class Server(commands.Cog):
    """
    Module for server management
    """

    def __init__(self, bot):
        self.bot = bot
        self.mregex = re.compile(r"[0-9]{17,21}")
        self.dregex = re.compile(
            r"(?:https?://)?discord(?:app)?\.(?:com/invite|gg)/[a-zA-Z0-9]+/?"
        )
        self.uregex = re.compile(
            r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*(),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+"
        )

    ###################
    ## Prune Command ##
    ###################

    @decorators.group(
        brief="Purge any type of content.",
        aliases=["prune", "delete"],
        description="Methods:"
        "\nAll - Purge all messages."
        "\nBots - Purge messages sent by bots."
        "\nContains - Custom purge messages."
        "\nEmbeds - Purge messages with embeds."
        "\nEmojis - Purge messages with emojis."
        "\nFiles - Purge messages with attachments."
        "\nHumans - Purge  messages sent by humans."
        "\nImages - Purge messages with images."
        "\nInvites - Purge messages with invites."
        "\nMentions - Purge messages with mentions."
        "\nReactions - Purge reactions from messages."
        "\nUntil - Purge messages until a message."
        "\nUrls - Purge messages with URLs."
        "\nUser - Purge messages sent by a user."
        "\nWebhooks - Purge messages sent by wehooks.",
    )
    @checks.guild_only()
    @checks.bot_has_perms(manage_messages=True)
    @checks.has_perms(manage_messages=True)
    @checks.cooldown()
    async def purge(self, ctx):
        """
        Usage: {0}purge <option> <amount>
        Aliases: {0}prune, {0}delete
        Permission: Manage Messages
        Options:
            all, bots, contains, embeds,
            emojis, files, humans, images,
            invites, mentions, reactions,
            until, urls, user, webhooks.
        Output:
            Deletes messages that match
            a specific search criteria
        Examples:
            {0}prune user Hecate
            {0}prune bots
            {0}prune invites 1000
        Notes:
            Specify the amount kwarg
            to search that number of
            messages. For example,
            {0}prune user Hecate 1000
            will search for all messages
            in the past 1000 sent in the
            channel, and delete all that
            were sent by Hecate.
            Default amount is 100.
        """
        args = str(ctx.message.content).split()
        if ctx.invoked_subcommand is None:
            try:
                search = int(args[1])
            except (IndexError, ValueError):
                return await ctx.usage("<option> [search=100]")
            await self._remove_all(ctx, search=search)

    async def do_removal(
        self, ctx, limit, predicate, *, before=None, after=None, message=True
    ):
        if limit > 2000:
            return await ctx.send_or_reply(
                f"Too many messages to search given ({limit}/2000)",
            )

        if not before:
            before = ctx.message
        else:
            before = discord.Object(id=before)

        if after:
            after = discord.Object(id=after)

        if predicate:
            coro = ctx.channel.purge(
                limit=limit, before=before, after=after, check=predicate
            )
        else:
            coro = ctx.channel.purge(limit=limit, before=before, after=after)

        try:
            deleted = await coro
        except discord.Forbidden:
            return await ctx.fail("I do not have permissions to delete messages.")
        except discord.HTTPException as e:
            return await ctx.fail(f"Error: {e} (try a smaller search?)")

        deleted = len(deleted)
        if message is True:
            msg = await ctx.send_or_reply(
                f"{self.bot.emote_dict['trash']} Deleted {deleted} message{'' if deleted == 1 else 's'}",
            )
            await asyncio.sleep(5)
            to_delete = [msg.id, ctx.message.id]
            await ctx.channel.purge(check=lambda m: m.id in to_delete)

    @purge.command(brief="Purge messages with embeds.")
    async def embeds(self, ctx, search=100):
        """
        Usage: {0}purge embeds [amount]
        Output:
            Deletes all messages that
            contain embeds in them.
        Examples:
            {0}purge embeds 2000
            {0}prune embeds
        """
        await self.do_removal(ctx, search, lambda e: len(e.embeds))

    @purge.command(brief="Purge messages with invites.", aliases=["ads"])
    async def invites(self, ctx, search=100):
        """
        Usage: {0}purge invites [amount]
        Alias: {0}purge ads
        Output:
            Deletes all messages with
            invite links in them.
        Examples:
            {0}purge invites
            {0}prune invites 125
        """

        def predicate(m):
            return self.dregex.search(m.content)

        await self.do_removal(ctx, search, predicate)

    @purge.command(aliases=["link", "url", "links"], brief="Purge messages with URLs.")
    async def urls(self, ctx, search=100):
        """
        Usage: {0}purge urls [amount]
        Aliases:
            {0}purge link
            {0}purge links
            {0}purge url
        Output:
            Deletes all messages that
            contain URLs in them.
        Examples:
            {0}purge urls
            {0}prune urls 125
        """

        def predicate(m):
            return self.uregex.search(m.content)

        await self.do_removal(ctx, search, predicate)

    @purge.command(brief="Purge messages with attachments.", aliases=["attachments"])
    async def files(self, ctx, search=100):
        """
        Usage: {0}purge files [amount]
        Aliases:
            {0}purge attachments
        Output:
            Deletes all messages that
            contain attachments in them.
        Examples:
            {0}purge attachments
            {0}prune files 125
        """
        await self.do_removal(ctx, search, lambda e: len(e.attachments))

    @purge.command(
        brief="Purge messages with mentions.", aliases=["pings", "ping", "mention"]
    )
    async def mentions(self, ctx, search=100):
        """
        Usage: -purge mentions [amount]
        Aliases:
            {0}purge pings
            {0}purge ping
            {0}purge mention
        Output:
            Deletes all messages that
            contain user mentions in them.
        Examples:
            {0}purge mentions
            {0}prune pings 125
        """
        await self.do_removal(
            ctx, search, lambda e: len(e.mentions) or len(e.role_mentions)
        )

    @purge.command(
        brief="Purge messages with images.", aliases=["pictures", "pics", "image"]
    )
    async def images(self, ctx, search=100):
        """
        Usage: {0}purge mentions [amount]
        Aliases:
            {0}purge pics
            {0}purge pictures
            {0}purge image
        Output:
            Deletes all messages that
            contain images in them.
        Examples:
            {0}purge pictures
            {0}prune images 125
        """
        await self.do_removal(
            ctx, search, lambda e: len(e.embeds) or len(e.attachments)
        )

    @purge.command(name="all", brief="Purge all messages.", aliases=["messages"])
    async def _remove_all(self, ctx, search=100):
        """
        Usage: {0}purge all [amount]
        Aliases:
            {0}purge
            {0}purge messages
        Output:
            Deletes all messages.
        Examples:
            {0}purge
            {0}prune 2000
            {0}prune messages 125
        """
        await self.do_removal(ctx, search, lambda e: True)

    @purge.command(brief="Purge messages sent by a user.", aliases=["member"])
    async def user(self, ctx, user: converters.DiscordMember, search=100):
        """
        Usage: {0}purge user <user> [amount]
        Aliases:
            {0}purge member
        Output:
            Deletes all messages that
            were sent by the passed user.
        Examples:
            {0}purge user
            {0}prune member 125
        """
        await self.do_removal(ctx, search, lambda e: e.author.id == user.id)

    @purge.command(brief="Customize purging messages.", aliases=["has"])
    async def contains(self, ctx, *, substr: str):
        """
        Usage: {0}purge contains <string>
        Alias:
            {0}purge has
        Output:
            Deletes all messages that
            contain the passed string.
        Examples:
            {0}purge contains hello
            {0}prune has no
        Notes:
            The string must a minimum
            of 2 characters in length.
        """
        if len(substr) < 2:
            await ctx.fail("The substring length must be at least 2 characters.")
        else:
            await self.do_removal(ctx, 100, lambda e: substr in e.content)

    @purge.command(
        name="bots", brief="Purge messages sent by bots.", aliases=["robots"]
    )
    async def _bots(self, ctx, search=100, prefix=None):
        """
        Usage: {0}purge bots [amount] [prefix]
        Alias:
            {0}purge robots
        Output:
            Deletes all messages
            that were sent by bots.
        Examples:
            {0}purge robots 200
            {0}prune bots 150
        Notes:
            Specify an optional prefix to
            remove all messages that start
            with that prefix. This is useful
            for removing command invocations
        """

        if not str(search).isdigit():
            prefix = search
            search = 100
        if prefix:

            def predicate(m):
                return (m.webhook_id is None and m.author.bot) or m.content.startswith(
                    prefix
                )

        else:

            def predicate(m):
                return m.webhook_id is None and m.author.bot

        await self.do_removal(ctx, search, predicate)

    @purge.command(
        name="webhooks", aliases=["webhook"], brief="Purge messages sent by wehooks."
    )
    async def webhooks(self, ctx, search=100):
        """
        Usage: {0}purge webhooks [amount]
        Alias:
            {0}purge webhook
        Output:
            Deletes all messages that
            were sent by webhooks.
        Examples:
            {0}purge webhook
            {0}prune webhooks 125
        """

        def predicate(m):
            return m.webhook_id

        await self.do_removal(ctx, search, predicate)

    @purge.command(
        name="humans",
        aliases=["users", "members", "people"],
        brief="Purge messages sent by humans.",
    )
    async def _users(self, ctx, search=100):
        """
        Usage: {0}purge humans [amount]
        Aliases:
            {0}purge users
            {0}purge members
            {0}purge people
        Output:
            Deletes all messages
            sent by user accounts.
            Bot and webhook messages
            will not be deleted.
        Examples:
            {0}purge humans
            {0}prune people 125
        """

        def predicate(m):
            return m.author.bot is False

        await self.do_removal(ctx, search, predicate)

    @purge.command(
        name="emojis",
        aliases=["emotes", "emote", "emoji"],
        brief="Purge messages with emojis.",
    )
    async def _emojis(self, ctx, search=100):
        """
        Usage: {0}purge emojis [amount]
        Aliases:
            {0}purge emotes
            {0}purge emote
            {0}purge emoji
        Output:
            Deletes all messages that
            contain custom discord emojis.
        Examples:
            {0}purge emojis
            {0}prune emotes 125
        """
        custom_emoji = re.compile(r"<a?:(.*?):(\d{17,21})>|[\u263a-\U0001f645]")

        def predicate(m):
            return custom_emoji.search(m.content)

        await self.do_removal(ctx, search, predicate)

    @purge.command(name="reactions", brief="Purge reactions from messages.")
    async def _reactions(self, ctx, search=100):
        """
        Usage: {0}purge emojis [amount]
        Output:
            Demoves all reactions from
            messages that were reacted on.
        Examples:
            {0}purge reactions
            {0}prune reactions 125
        Notes:
            The messages are not deleted.
            Only the reactions are removed.
        """
        if search > 2000:
            return await ctx.send_or_reply(
                content=f"Too many messages to search for ({search}/2000)",
            )

        total_reactions = 0
        async for message in ctx.history(limit=search, before=ctx.message):
            if len(message.reactions):
                total_reactions += sum(r.count for r in message.reactions)
                await message.clear_reactions()
        msg = await ctx.send_or_reply(
            f'{self.bot.emote_dict["trash"]} Successfully removed {total_reactions} reactions.'
        )
        to_delete = [msg.id, ctx.message.id]
        await ctx.channel.purge(check=lambda m: m.id in to_delete)

    @purge.command(
        name="until", aliases=["after"], brief="Purge messages after a message."
    )
    async def _until(self, ctx, message: discord.Message = None):
        """
        Usage: {0}purge until <message id>
        Alias: {0}purge after
        Output:
            Purges all messages until
            the given message_id.
            Given ID is not deleted
        Examples:
            {0}purge until 810377376269
            {0}prune after 810377376269
        """
        if not message:
            message = await converters.DiscordMessage().convert(ctx)
        await self.do_removal(ctx, 100, None, after=message.id)

    @purge.command(name="between", brief="Purge messages between 2 messages.")
    async def _between(self, ctx, message1: discord.Message, message2: discord.Message):
        """
        Usage: {0}purge between <message id> <message id>
        Output:
            Purges all messages until
            the given message_id.
            Given ID is not deleted
        Examples:
            {0}purge until 810377376269
            {0}prune after 810377376269
        """
        await self.do_removal(ctx, 100, None, before=message2.id, after=message1.id)

    async def _basic_cleanup_strategy(self, ctx, search):
        count = 0
        async for msg in ctx.history(limit=search, before=ctx.message):
            if msg.author == ctx.me and not (msg.mentions or msg.role_mentions):
                await msg.delete()
                count += 1
        return {"Bot": count}

    async def _complex_cleanup_strategy(self, ctx, search):
        prefixes = tuple(self.bot.get_guild_prefixes(ctx.guild))

        def check(m):
            return m.author == ctx.me or m.content.startswith(prefixes)

        deleted = await ctx.channel.purge(limit=search, check=check, before=ctx.message)
        return Counter(m.author.display_name for m in deleted)

    async def _regular_user_cleanup_strategy(self, ctx, search):
        prefixes = tuple(self.bot.get_guild_prefixes(ctx.guild))

        def check(m):
            return (m.author == ctx.me or m.content.startswith(prefixes)) and not (
                m.mentions or m.role_mentions
            )

        deleted = await ctx.channel.purge(limit=search, check=check, before=ctx.message)
        return Counter(m.author.display_name for m in deleted)

    @decorators.command(
        brief="Clean up bot command usage.",
        aliases=["clean"],
        updated="2021-05-05 16:00:23.974656",
    )
    @checks.guild_only()
    @checks.cooldown()
    async def cleanup(self, ctx, search=100):
        """
        Usage: {0}cleanup [search]
        Alias: {0}clean
        Output: Cleans up the bot's messages from the channel.
        Notes:
            If a search number is specified, it searches that many messages to delete.
            If the bot has Manage Messages permissions then it will try to delete
            messages that look like they invoked the bot as well.
            After the cleanup is completed, the bot will send you a message with
            which people got their messages deleted and their count. This is useful
            to see which users are spammers. Regular users can delete up to 25 while
            moderators can delete up to 2000 messages
        """
        strategy = self._basic_cleanup_strategy
        is_mod = ctx.channel.permissions_for(ctx.author).manage_messages
        if ctx.channel.permissions_for(ctx.me).manage_messages:
            if is_mod:
                strategy = self._complex_cleanup_strategy
            else:
                strategy = self._regular_user_cleanup_strategy

        if is_mod:
            search = min(max(2, search), 2000)
        else:
            search = min(max(2, search), 25)

        spammers = await strategy(ctx, search)
        deleted = sum(spammers.values())
        messages = [
            f"**{self.bot.emote_dict['trash']} Deleted {deleted} message{'' if deleted == 1 else 's'}\n**"
        ]
        if deleted:
            spammers = sorted(spammers.items(), key=lambda t: t[1], reverse=True)
            messages.extend(f"`{author}`: {count}" for author, count in spammers)
        desc = "\n".join(messages)
        em = discord.Embed()
        em.color = self.bot.constants.embed
        em.description = desc

        msg = await ctx.send_or_reply(embed=em)
        await asyncio.sleep(5)
        to_delete = [msg.id, ctx.message.id]
        await ctx.channel.purge(check=lambda m: m.id in to_delete)

    @commands.group(name="emoji", aliases=["emote"], brief="Manage server emojis.")
    @checks.guild_only()
    @checks.bot_has_perms(manage_emojis=True)
    @checks.has_perms(manage_emojis=True)
    @checks.cooldown()
    async def _emoji(self, ctx):
        """
        Usage: {0}emoji <subcommand> [emoji(s)]
        Alias: {0}emote
        Subcommands:
            create/add # Create an emoji for the server.
            delete/remove # Delete emojis from the server.
        """
        if ctx.subcommand_passed is None:
            await ctx.usage("<subcommand> [emoji]")

    @_emoji.command(name="create", aliases=["add"])
    async def _emoji_create(
        self, ctx, name: converters.emoji_name, *, emoji: converters.EmojiURL
    ):
        """
        Create an emoji for the server under the given name.
        You must have Manage Emoji permission to use this.
        The bot must have this permission too.
        """
        reason = f"Action done by {ctx.author} (ID: {ctx.author.id})"

        emoji_count = sum(e.animated == emoji.animated for e in ctx.guild.emojis)
        if emoji_count >= ctx.guild.emoji_limit:
            return await ctx.fail(
                "There are no more emoji slots available in this server."
            )

        async with self.bot.session.get(emoji.url) as resp:
            if resp.status >= 400:
                return await ctx.fail("Could not fetch the image.")
            if int(resp.headers["Content-Length"]) >= (256 * 1024):
                return await ctx.fail("Image size is too large.")
            data = await resp.read()
            coro = ctx.guild.create_custom_emoji(name=name, image=data, reason=reason)
            async with ctx.typing():
                try:
                    created = await asyncio.wait_for(coro, timeout=10.0)
                except asyncio.TimeoutError:
                    return await ctx.fail(
                        "Rate limit reached. Please retry again later."
                    )
                except discord.HTTPException as e:
                    return await ctx.fail(f"Failed to create emoji: {e}")
                else:
                    return await ctx.success(f"Created {created}")

    @_emoji.command(
        name="delete", aliases=["remove"], brief="Delete emojis from the server."
    )
    async def _emoji_delete(self, ctx, *emojis: converters.GuildEmojiConverter):
        """
        Usage: {0}emoji delete [emojis]...
        Alias: {0}emoji remove
        Output: Delete an emoji from the server.
        Notes:
            You can pass several emojis to delete
            them all with the same command.
        """
        failed = []
        success = []
        for emoji in emojis:
            try:
                await emoji.delete()
            except Exception as e:
                failed.append((emoji.name, e))
                continue
            success.append(emoji.name)

        if success:
            await ctx.success(
                f"Deleted the emoji{'' if len(success) == 1 else 's'}: `{', '.join(success)}`"
            )
        if failed:
            await helpers.error_info(ctx, failed, option="Emoji")

    @decorators.group(name="role", brief="Role management commands.")
    @checks.bot_has_perms(manage_roles=True)
    @checks.has_perms(manage_roles=True)
    async def _role(self, ctx):
        if ctx.subcommand_passed is None:
            return await ctx.usage("<subcommand> [role]")

    @_role.command(name="create", aliases=["add"], brief="Create a server role.")
    async def _role_create(
        self,
        ctx,
        name: str,
        color: typing.Optional[typing.Union[int, discord.Color]],
        hoist: bool = False,
    ):
        """
        Usage: {0}role create <name> [color] [hoist=False]
        Alias: {0}role add
        Output: Creates a server role
        """
        try:
            role = await ctx.guild.create_role(
                reason=f"Role created by {ctx.author}",
                name=name,
                color=color,
                hoist=hoist,
            )
        except Exception as e:
            return await ctx.fail(str(e))
        await ctx.success(f"Successfully created the role {role.mention}")

    @_role.command(name="delete", aliases=["remove"], brief="Delete a server role.")
    async def _role_delete(self, ctx, *roles: converters.UniqueRole):
        """
        Usage: {0}role delete [roles]...
        Alias: {0}role remove
        Output: Delete multiple roles from the server.
        """
        failed = []
        success = []
        for role in roles:
            try:
                await role.delete(reason=f"Role deleted by {ctx.author}")
            except Exception as e:
                failed.append((role.name, e))
                continue
            success.append(role.name)
        if success:
            await ctx.success(
                f"Successfully deleted the role{'' if len(success) == 1 else 's'} `{', '.join(success)}`"
            )
        if failed:
            await helpers.error_info(ctx, failed, option="Role")
