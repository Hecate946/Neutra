import io
import json
import discord

from collections import defaultdict
from datetime import datetime
from discord.ext import commands, tasks

from utilities import utils
from utilities import checks
from utilities import humantime
from utilities import converters
from utilities import decorators


CREATED_MESSAGE = "https://cdn.discordapp.com/attachments/846597178918436885/846841649542725632/messagecreate.png"
UPDATED_MESSAGE = "https://cdn.discordapp.com/attachments/846597178918436885/846841668639653939/messageupdate.png"
DELETED_MESSAGE = "https://cdn.discordapp.com/attachments/846597178918436885/846841722994163722/messagedelete.png"


def setup(bot):
    bot.add_cog(Logging(bot))


class WebhookLimit(commands.BadArgument):
    """
    Custom exception to raise when the max
    webhook limit for a channel is reached.
    """

    def __init__(self, channel, *args):
        msg = f"Channel {channel.mention} has reached the maximum number of webhooks (10). Please delete a webhook and retry."
        super().__init__(message=msg, *args)


class Logging(commands.Cog):
    """
    Manage the logging system
    """

    def __init__(self, bot):
        self.bot = bot
        self.entities = defaultdict(list)
        self.log_data = defaultdict(dict)
        self.settings = defaultdict(dict)
        self.tasks = defaultdict(list)
        self.webhooks = defaultdict(discord.Webhook)

        bot.loop.create_task(self.load_settings())
        bot.loop.create_task(self.load_log_data())

        self.log_types = [
            "channels",
            "emojis",
            "invites",
            "joins",
            "messages",
            "moderation",
            "users",
            "roles",
            "server",
            "voice",
        ]  # Helper list with all our logging types.

        self.dispatch_webhooks.add_exception_type(discord.NotFound)
        self.dispatch_webhooks.start()  # Start the task loop

        self.map = {
            True: bot.emote_dict["pass"],
            False: bot.emote_dict["fail"],
        }  # Map for determining the emote.

    def cog_unload(self):
        self.dispatch_webhooks.stop()

    async def load_settings(self):
        query = """
                SELECT 
                logs.server_id,
                (SELECT ROW_TO_JSON(_) FROM (SELECT
                    logs.channels,
                    logs.emojis,
                    logs.invites,
                    logs.joins,
                    logs.messages,
                    logs.moderation,
                    logs.users,
                    logs.roles,
                    logs.server,
                    logs.voice
                ) AS _) AS settings
                FROM logs;
                """
        records = await self.bot.cxn.fetch(query)
        if records:
            for record in records:
                self.settings[record["server_id"]].update(
                    json.loads(record["settings"])
                )

    async def load_log_data(self):
        query = """
                SELECT 
                d.server_id, d.entities,
                (SELECT ROW_TO_JSON(_) FROM (SELECT
                    d.channel_id,
                    d.webhook_id,
                    d.webhook_token
                ) AS _) AS log_data
                FROM log_data as d;
                """
        records = await self.bot.cxn.fetch(query)
        if records:
            for record in records:
                self.log_data[record["server_id"]].update(
                    json.loads(record["log_data"])
                )
                self.entities[record["server_id"]].extend(record["entities"])
                webhook = self.parse_json(json.loads(record["log_data"]))
                self.webhooks[record["server_id"]] = webhook

    def parse_json(self, data):
        return self.fetch_webhook(data["webhook_id"], data["webhook_token"])

    def fetch_webhook(self, webhook_id, webhook_token):
        try:
            webhook = discord.Webhook.partial(
                id=webhook_id,
                token=webhook_token,
                adapter=discord.AsyncWebhookAdapter(self.bot.session),
            )
        except Exception:
            return
        else:
            return webhook

    def get_webhook(self, guild, event=None):
        webhook = self.webhooks.get(guild.id)
        if event is None:
            return webhook
        settings = self.get_settings(guild, event)
        if webhook and settings:
            return webhook

    def get_settings(self, guild, event=None):
        settings = self.settings.get(guild.id)
        if event is None:
            return settings
        if settings:
            return self.settings[guild.id].get(event)

    def get_log_data(self, guild):
        return self.log_data.get(guild.id)

    def get_wh_channel(self, guild):
        data = self.get_log_data(guild)
        if data:
            return self.bot.get_channel(data.get("channel_id"))

    async def destroy_logging(self, guild):
        async with self.bot.cxn.acquire() as conn:
            async with conn.transaction():
                query = """
                        DELETE FROM log_data
                        WHERE server_id = $1;
                        """
                await conn.execute(query, guild.id)

                query = """
                        DELETE FROM logs
                        WHERE server_id = $1;
                        """
                await conn.execute(query, guild.id)

        webhook = self.get_webhook(guild)
        if webhook:
            try:
                await webhook.delete()
            except discord.NotFound:  # Couldn't get the webhook
                pass

    async def send_webhook(self, webhook, *, embed=None, file=None):
        if embed:
            self.tasks[webhook].append(embed)
        if file:
            self.tasks[webhook].append(file)

    # Helper function to truncate oversized strings.
    def truncate(self, string, max_chars):
        return (string[: max_chars - 3] + "...") if len(string) > max_chars else string

    # Helper function to check if an object is ignored
    def is_ignored(self, guild, objects):
        return any([obj in self.entities[guild.id] for obj in objects])

    @tasks.loop(seconds=3.0)
    async def dispatch_webhooks(self):
        if self.tasks:
            for webhook, objects in self.tasks.items():
                if objects:
                    to_send = objects[:10]
                    embeds = [x for x in to_send if type(x) is discord.Embed]
                    files = [x for x in to_send if type(x) is discord.File]
                    await webhook.send(
                        embeds=embeds,
                        files=files,
                        username=f"{self.bot.user.name}-logger",
                        avatar_url=self.bot.user.avatar_url,
                    )
                    embeds.clear()
                    files.clear()
                    self.tasks[webhook] = objects[10:]

    @dispatch_webhooks.error
    async def logging_error(self, exc):
        self.bot.dispatch("error", "logging_error", tb=utils.traceback_maker(exc))

    @decorators.group(
        name="log",
        brief="Manage the logging setup.",
        implemented="2021-03-17 07:09:57.666073",
        updated="2021-06-08 17:18:43.698120",
        invoke_without_command=True,
        case_insensitive=True,
    )
    @commands.guild_only()
    @commands.cooldown(2.0, 30, commands.BucketType.guild)
    @commands.bot_has_guild_permissions(manage_webhooks=True)
    @checks.bot_has_perms(embed_links=True)
    @checks.has_perms(manage_guild=True)
    async def _log(self, ctx, event: converters.LoggingEvent = None):
        """
        Usage: {0}log [event or subcommand]
        Permission: Manage Server
        Output:
            Manages the server logging system
        Notes:
            use {0}log
            with no arguments to output the
            current logging configuration.
        Events:
            channels
            emojis
            invites
            joins
            messages
            moderation
            users
            roles
            server
            voice
        Subcommands:
            {0}log channel [channel]  # Set up the server's logging
            {0}log disable  # Remove the server's logging
        """
        if ctx.invoked_subcommand is None:
            settings = self.get_settings(ctx.guild)
            if not settings:  # No settings = No logging
                return await ctx.fail("Logging is disabled on this server.")

            if event is None:  # Output the current settings
                embed = discord.Embed(
                    title="Logging Settings",
                    description="",
                    color=self.bot.constants.embed,
                )

                for key, value in settings.items():
                    embed.description += f"{self.map.get(value)} {key.capitalize()}\n"

                embed.add_field(
                    name="Logging channel",
                    value=self.get_wh_channel(ctx.guild).mention,
                )  # Show the logging channel

                await ctx.send_or_reply(embed=embed)
            else:
                if event == "all":  # Want to log all events.
                    current = all([e is True for e in settings.values()])
                    if current is True:  # All events already enabled...
                        return await ctx.success(
                            "All logging events are already enabled."
                        )

                    query = """
                            DELETE FROM logs
                            WHERE server_id = $1
                            """  # Delete what we have if we have it.
                    await self.bot.cxn.execute(query, ctx.guild.id)

                    query = """
                            INSERT INTO logs
                            VALUES ($1)
                            """  # Reinsert to refresh the log config.
                    await self.bot.cxn.execute(query, ctx.guild.id)

                    # Update the logging settings in the cache
                    self.settings[ctx.guild.id] = {x: True for x in self.log_types}
                    await ctx.success("All logging events have been enabled.")
                else:  # They specified an event
                    current = settings.get(event)
                    if current is True:  # Already logging this event.
                        return await ctx.success(
                            f"Logging event `{event}` is already enabled."
                        )

                    query = f"""
                            UPDATE logs
                            SET {event} = $1
                            WHERE server_id = $2
                            """  # Update the event column, set it to True.
                    await self.bot.cxn.execute(query, True, ctx.guild.id)

                    # Update the event in the cache to reflect the db.
                    self.settings[ctx.guild.id][event] = True
                    await ctx.success(f"Logging event `{event}` has been enabled.")

    @_log.command(
        aliases=["teardown"],
        brief="Disable server logging.",
    )
    async def disable(self, ctx):
        """
        Usage: {0}log disable
        Alias {0}log teardown
        Permission: Manage Server
        Output:
            Disables the server's logging system
        """
        webhook = self.get_webhook(ctx.guild)
        if not webhook:  # No webhook = No logging.
            return await ctx.fail("Logging is already disabled on this server.")
        c = await ctx.confirm("This action will delete all current logging settings.")
        if c:  # They confirmed they wanted to teardown the logging system
            await self.destroy_logging(ctx.guild)  # Drop from DB and delete webhooks.
            self.log_data[ctx.guild.id].clear()  # Clear data cache
            self.settings[ctx.guild.id].clear()  # Clear settings cache
            self.webhooks.pop(ctx.guild.id, None)  # Clear cached webhook
            self.tasks.pop(webhook, None)  # Delete any pending embeds/files to be sent.
            await ctx.success("Logging successfully disabled.")

    @_log.command(
        name="channel",
        aliases=["enable"],
        brief="Setup default logging.",
    )
    async def _channel(self, ctx, *, channel: discord.TextChannel = None):
        """
        Usage: {0}log channel [channel]
        Alias: {0}log enable [channel]
        Permission: Manage Server
        Output:
            Sets the given channel as the
            server's logging channel.
        Notes:
            Will default to the current channel
            if no channel is specified.
        """
        if channel is None:  # Default to current channel
            channel = ctx.channel

        if len(await channel.webhooks()) == 10:
            # Too many webhooks to create a new one.
            raise WebhookLimit(channel)

        settings = self.get_settings(ctx.guild)
        if settings:  # Logging already set up. Check if they want to override.
            c = await ctx.confirm(
                "Logging is already set up on this server. "
                f"Clicking the {self.bot.emote_dict['success']} button will override the current configuration."
            )
            if not c:  # They didn't want to override.
                return

        msg = await ctx.load(f"Setting up logging in channel {channel.mention}...")

        await self.destroy_logging(ctx.guild)  # Delete what we have if anything.

        try:  # Who knows. If there's an error while making the webhook.
            wh = await channel.create_webhook(name="webhook")
        except Exception as e:  # Tell them what went wrong.
            return await msg.edit(content=f"{self.bot.emote_dict['failed']} {str(e)}")

        query = """
                INSERT INTO logs (server_id)
                VALUES ($1)
                """  # Insert server_id into DB
        await self.bot.cxn.execute(query, ctx.guild.id)

        query = """
                INSERT INTO log_data (server_id, channel_id, webhook_id, webhook_token)
                VALUES ($1, $2, $3, $4)
                """  # Insert logging data.
        await self.bot.cxn.execute(query, ctx.guild.id, channel.id, wh.id, wh.token)

        # Update log_data so it matches the data in the DB
        self.log_data[ctx.guild.id] = {
            "channel_id": channel.id,
            "webhook_id": wh.id,
            "webhook_token": wh.token,
        }
        # Update the settings to reflect the default logging config.
        self.settings[ctx.guild.id] = {log_type: True for log_type in self.log_types}
        # Set the server logging webhook to the webhook we just created.
        self.webhooks[ctx.guild.id] = wh

        await msg.edit(  # Output confirmation
            content=f"{self.bot.emote_dict['success']} **Logging enabled for channel {channel.mention}**"
        )

    @decorators.command(
        brief="Disable logging events.",
        implemented="2021-03-17 07:09:57.666073",
        updated="2021-06-08 17:18:43.698120",
    )
    @commands.guild_only()
    @commands.cooldown(2.0, 30, commands.BucketType.guild)
    @commands.bot_has_guild_permissions(manage_webhooks=True)
    @checks.has_perms(manage_guild=True)
    async def unlog(self, ctx, event: converters.LoggingEvent):
        """
        Usage: {0}unlog [event]
        Permission: Manage Server
        Output:
            Stop logging a specific event.
        Notes:
            Use {0}log disable
            to teardown the server's
            logging system.
        """
        settings = self.get_settings(ctx.guild)
        if not settings:  # No settings = No logging.
            return await ctx.fail(f"Logging is disabled on this server.")

        if event == "all":  # They want to disable all.
            current = all([e is not True for e in settings.values()])
            if current is True:  # Already have all events disabled.
                return await ctx.success("All logging events are already disabled.")

            query = """
                    DELETE FROM logs
                    WHERE server_id = $1
                    """  # Delete what we have in the DB
            await self.bot.cxn.execute(query, ctx.guild.id)

            args = [False] * 10
            query = """
                    INSERT INTO logs
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                    """  # Insert false for all events
            await self.bot.cxn.execute(query, ctx.guild.id, *args)

            # Update all the cached event settings to false
            self.settings[ctx.guild.id] = {x: False for x in self.log_types}
            await ctx.success("All logging events have been disabled.")
        else:  # They specified an event.
            current = settings.get(event)
            if current is not True:  # Not logging this event.
                return await ctx.success(
                    f"Logging event `{event}` is already disabled."
                )

            query = f"""
                    UPDATE logs
                    SET {event} = $1
                    WHERE server_id = $2
                    """  # Update the setting to false for this event.
            await self.bot.cxn.execute(query, False, ctx.guild.id)

            # Update the cache to match the DB
            self.settings[ctx.guild.id][event] = False
            await ctx.success(f"Logging event `{event}` has been disabled.")

    ###################
    ## Group Aliases ##
    ###################

    @decorators.command(
        brief="Set your server's logging channel.",
        aliases=["logserver", "setlogchannel"],
    )
    @commands.guild_only()
    @commands.cooldown(2.0, 30, commands.BucketType.guild)
    @checks.bot_has_perms(manage_webhooks=True)
    @checks.has_perms(manage_guild=True)
    async def logchannel(self, ctx, *, channel: discord.TextChannel = None):
        """
        Usage: {0}logchannel [channel]
        Aliases: {0}logserver, {0}setlogchannel
        Output: Sets up a logging channel for the server
        Notes:
            Use {0}log [event] and {0}unlog [event] to enable/disable
            specific logging events that are sent to the logchannel
        """
        await ctx.invoke(self._channel, channel=channel)

    @decorators.command(
        brief="Remove your server's logging channel.",
        aliases=["unlogserver"],
    )
    @commands.guild_only()
    @commands.cooldown(2.0, 30, commands.BucketType.guild)
    @checks.bot_has_perms(manage_webhooks=True)
    @checks.has_perms(manage_guild=True)
    async def unlogchannel(self, ctx):
        """
        Usage: {0}unlogchannel
        Aliases: {0}unlogserver
        Output: Removes the server's logging channel
        Notes:
            Use {0}log [event] and {0}unlog [event] to enable/disable
            specific logging events that are sent to the logchannel
        """
        await ctx.invoke(self.disable)

    #####################
    ## Event Listeners ##
    #####################

    @commands.Cog.listener()
    @decorators.wait_until_ready()
    async def on_guild_remove(self, guild):
        webhook = self.get_webhook(guild)
        if webhook:
            await self.destroy_logging(guild)  # Drop from DB and delete webhooks.
            self.log_data[guild.id].clear()  # Clear data cache
            self.settings[guild.id].clear()  # Clear settings cache
            self.webhooks.pop(guild.id, None)  # Clear cached webhook
            self.tasks.pop(webhook, None)  # Delete any pending embeds/files to be sent.

    @commands.Cog.listener()
    @decorators.wait_until_ready()
    @decorators.event_check(lambda s, m: m.guild and not m.author.bot)
    async def on_message(self, message):
        webhook = self.get_webhook(message.guild, "invites")
        if not webhook:
            return

        regex_match = self.bot.dregex.search(message.content)
        if not regex_match:
            return

        embed = discord.Embed(
            description=f"**Author:**  {message.author.mention}, **ID:** `{message.author.id}`\n"
            f"**Channel:** {message.channel.mention} **ID:** `{message.channel.id}`\n"
            f"**Server:** `{message.guild.name}` **ID:** `{message.guild.id}`\n\n"
            f"**__Invite Link:___**```fix\n{regex_match.group(0)}```\n"
            f"**[Jump to message](https://discord.com/channels/{message.guild.id}/{message.channel.id}/{message.id})**",
            color=self.bot.constants.embed,
            timestamp=datetime.utcnow(),
        )
        embed.set_author(
            name="Invite Link Posted",
            icon_url=UPDATED_MESSAGE,
        )
        await self.send_webhook(webhook, embed=embed)

    @commands.Cog.listener()
    async def on_guild_update(self, before, after):
        webhook = self.get_webhook(after, "server")
        if not webhook:
            return

        audit = [
            entry
            async for entry in after.audit_logs(
                action=discord.AuditLogAction.guild_update
            )
        ][0]
        if before.name != after.name:
            embed = discord.Embed(
                description=f"**Author:**  `{str(audit.user)}`\n\n"
                f"**___Previous Name___**: ```fix\n{before.name}```"
                f"**___Current Name___**: ```fix\n{after.name}```",
                color=self.bot.constants.embed,
            )

            embed.set_author(
                name="Server Name Edited",
                icon_url=UPDATED_MESSAGE,
            )

            await self.send_webhook(webhook, embed=embed)

        if before.icon_url != after.icon_url:
            embed = discord.Embed(
                description=f"**Author:**  `{str(audit.user)}`\n" "**New icon below**",
                color=self.bot.constants.embed,
            )

            embed.set_author(
                name="Server Icon Updated",
                icon_url=UPDATED_MESSAGE,
            )

            embed.set_image(url=after.icon_url)
            await self.send_webhook(webhook, embed=embed)

        if before.banner_url != after.banner_url:
            embed = discord.Embed(
                description=f"**Author:**  `{str(audit.user)}`\n"
                "**New banner below**",
                color=self.bot.constants.embed,
            )

            embed.set_author(
                name="Server Banner Updated",
                icon_url=UPDATED_MESSAGE,
            )

            embed.set_image(url=after.banner_url)
            await self.send_webhook(webhook, embed=embed)

    @commands.Cog.listener()
    async def on_guild_emojis_update(self, guild, before, after):
        webhook = self.get_webhook(guild, "emojis")
        if not webhook:
            return

        new = True if len(after) > len(before) else False
        emoji = after[-1] if new else None

        if not new:
            for emoji in before:
                if emoji not in after:
                    new = False

        embed = discord.Embed(
            color=self.bot.constants.embed,
            timestamp=datetime.utcnow(),
            footer={"text": emoji.id},
        )

        embed.description = (
            f"**Emoji: {str(emoji)}\nName: `{emoji.name}`**\n"
            if new
            else f"**Name: `{emoji.name}`**\n"
        )

        embed.set_author(
            name=f"Emoji {'created' if new else 'deleted'}.",
            icon_url=f"{CREATED_MESSAGE if new else DELETED_MESSAGE}",
        )

        await self.send_webhook(webhook, embed=embed)

    @commands.Cog.listener()
    @decorators.wait_until_ready()
    async def on_guild_channel_create(self, channel):
        webhook = self.get_webhook(channel.guild, "channels")
        if not webhook:
            return

        embed = discord.Embed(
            description=f"**Channel:** `{channel.name}` **ID:** `{channel.id}`\n"
            f"**Server:** `{channel.guild.name}` **ID:** `{channel.guild.id}`\n\n",
            color=self.bot.constants.embed,
            timestamp=datetime.utcnow(),
        )
        embed.set_author(
            name="Channel Created",
            icon_url="https://cdn.discordapp.com/emojis/810659118045331517.png?v=1",
        )
        embed.set_footer(text=f"Channel ID: {channel.id}")
        await self.send_webhook(webhook, embed=embed)

    @commands.Cog.listener()
    @decorators.wait_until_ready()
    async def on_guild_channel_delete(self, channel):
        webhook = self.get_webhook(channel.guild, "channels")
        if not webhook:
            return

        embed = discord.Embed(
            description=f"**Channel:** `{channel.name}` **ID:** `{channel.id}`\n"
            f"**Server:** `{channel.guild.name}` **ID:** `{channel.guild.id}`\n\n",
            color=self.bot.constants.embed,
            timestamp=datetime.utcnow(),
        )
        embed.set_author(
            name="Channel Deleted",
            icon_url="https://cdn.discordapp.com/emojis/810659118045331517.png?v=1",
        )
        embed.set_footer(text=f"Channel ID: {channel.id}")
        await self.send_webhook(webhook, embed=embed)

    @commands.Cog.listener()
    @decorators.wait_until_ready()
    async def on_guild_channel_update(self, before, after):
        webhook = self.get_webhook(after.guild, "channels")
        if not webhook:
            return

        if before.name != after.name:
            embed = discord.Embed(
                description=f"**Channel:** {after.mention} **Name:** `{after}`\n"
                f"**Old Name:** `{before.name}`\n"
                f"**New Name:** `{after.name}`\n",
                colour=self.bot.constants.embed,
                timestamp=datetime.utcnow(),
            )
            embed.set_author(name=f"Channel Update")
            embed.set_footer(text=f"Channel ID: {after.id}")
            await self.send_webhook(webhook, embed=embed)

        elif before.category != after.category:
            embed = discord.Embed(
                description=f"**Channel:** {after.mention} **Name:** `{after}`\n"
                f"**Old Category:** `{before.category}`\n"
                f"**New Category:** `{after.category}`\n",
                colour=self.bot.constants.embed,
                timestamp=datetime.utcnow(),
            )
            embed.set_author(name=f"Channel Update")
            embed.set_footer(text=f"Channel ID: {after.id}")
            await self.send_webhook(webhook, embed=embed)

        if isinstance(before, discord.TextChannel):
            if before.topic != after.topic:
                embed = discord.Embed(
                    description=f"**Channel:** {after.mention} **Name:** `{after}`\n"
                    f"**Old Topic:** `{before.topic}`\n"
                    f"**New Topic:** `{after.topic}`\n",
                    colour=self.bot.constants.embed,
                    timestamp=datetime.utcnow(),
                )
                embed.set_author(name=f"Channel Update")
                embed.set_footer(text=f"Channel ID: {after.id}")
                await self.send_webhook(webhook, embed=embed)

        if isinstance(before, discord.TextChannel):
            if before.slowmode_delay != after.slowmode_delay:
                embed = discord.Embed(
                    description=f"**Channel:** {after.mention} **Name:** `{after}`\n"
                    f"**Old Slowmode:** `{before.slowmode_delay}`\n"
                    f"**New Slowmode:** `{after.slowmode_delay}`\n",
                    colour=self.bot.constants.embed,
                    timestamp=datetime.utcnow(),
                )
                embed.set_author(name=f"Channel Update")
                embed.set_footer(text=f"Channel ID: {after.id}")
                await self.send_webhook(webhook, embed=embed)

        if isinstance(before, discord.VoiceChannel):
            if before.user_limit != after.user_limit:
                embed = discord.Embed(
                    description=f"**Channel:** {after.mention} **Name:** `{after}`\n"
                    f"**Old User Limit:** `{before.user_limit}`\n"
                    f"**New User Limit:** `{after.user_limit}`\n",
                    colour=self.bot.constants.embed,
                    timestamp=datetime.utcnow(),
                )
                embed.set_author(name=f"Channel Update")
                embed.set_footer(text=f"Channel ID: {after.id}")
                await self.send_webhook(webhook, embed=embed)

        elif before.changed_roles != after.changed_roles:
            old_overwrites = (
                str(
                    [
                        r.mention
                        for r in before.changed_roles
                        if r != after.guild.default_role
                    ]
                )
                .replace("'", "")
                .replace("[", "")
                .replace("]", "")
            )
            new_overwrites = (
                str(
                    [
                        r.mention
                        for r in after.changed_roles
                        if r != after.guild.default_role
                    ]
                )
                .replace("'", "")
                .replace("[", "")
                .replace("]", "")
            )
            embed = discord.Embed(
                description=f"**Channel:** {after.mention} **Name:** `{after}`\n"
                f"**Old Role Overwrites:** {old_overwrites}\n"
                f"**New Role Overwrites:** {new_overwrites}\n",
                colour=self.bot.constants.embed,
                timestamp=datetime.utcnow(),
            )
            embed.set_author(name=f"Channel Update")
            embed.set_footer(text=f"Channel ID: {after.id}")
            await self.send_webhook(webhook, embed=embed)

    # Create our custom event listener for all moderation actions
    @commands.Cog.listener()
    async def on_mod_action(self, ctx, targets):
        webhook = self.get_webhook(ctx.guild, "moderation")
        if not webhook:
            return

        embed = discord.Embed(
            description=f"**Mod:**  {ctx.author.mention}, **ID:** `{ctx.author.id}`\n"
            f"**Command:** `{ctx.command}` **Category:** `{ctx.command.cog_name}`\n"
            f"**Targets:** `{', '.join(targets)}`\n\n"
            f"**__Message Content__**\n ```fix\n{ctx.message.clean_content}```\n"
            f"**[Jump to action](https://discord.com/channels/{ctx.guild.id}/{ctx.channel.id}/{ctx.message.id})**",
            color=self.bot.constants.embed,
            timestamp=datetime.utcnow(),
        )
        embed.set_author(
            name="Moderation Action",
            icon_url="https://cdn.discordapp.com/attachments/811396494304608309/830158456647581767/hammer-512.png",
        )
        embed.set_footer(text=f"Message ID: {ctx.message.id}")
        await self.send_webhook(webhook, embed=embed)

    @commands.Cog.listener()
    @decorators.wait_until_ready()
    async def on_member_join(self, member):
        webhook = self.get_webhook(member.guild, "joins")
        if not webhook:
            return

        embed = discord.Embed(
            description=f"**User:** {member.mention} **Name:** `{member}`\n",
            colour=self.bot.constants.embed,
            timestamp=datetime.utcnow(),
        )
        embed.set_author(name=f"User Joined")
        embed.set_footer(text=f"User ID: {member.id}")
        await self.send_webhook(webhook, embed=embed)

    @commands.Cog.listener()
    @decorators.wait_until_ready()
    async def on_member_remove(self, member):
        webhook = self.get_webhook(member.guild, "joins")
        if not webhook:
            return

        embed = discord.Embed(
            description=f"**User:** {member.mention} **Name:** `{member}`\n",
            colour=self.bot.constants.embed,
            timestamp=datetime.utcnow(),
        )
        embed.set_author(name=f"User Left")
        embed.set_footer(text=f"User ID: {member.id}")
        await self.send_webhook(webhook, embed=embed)

    @commands.Cog.listener()
    @decorators.wait_until_ready()
    @decorators.event_check(lambda s, b, a: not a.bot)
    async def on_member_update(self, before, after):
        if before.display_name != after.display_name:
            webhook = self.get_webhook(after.guild, "users")
            if webhook:
                embed = discord.Embed(
                    description=f"**User:** {after.mention} **Name:** `{after}`\n"
                    f"**Old Nickname:** `{before.display_name}`\n"
                    f"**New Nickname:** `{after.display_name}`\n",
                    colour=self.bot.constants.embed,
                    timestamp=datetime.utcnow(),
                )
                embed.set_author(name=f"Nickname Change")
                embed.set_footer(text=f"User ID: {after.id}")

                await self.send_webhook(webhook, embed=embed)

        elif before.roles != after.roles:
            if "@everyone" not in [x.name for x in before.roles]:
                return
            webhook = self.get_webhook(after.guild, "roles")
            if webhook:
                embed = discord.Embed(
                    description=f"**User:** {after.mention} **Name:** `{after}`\n"
                    f"**Old Roles:** {', '.join([r.mention for r in before.roles if r != after.guild.default_role])}\n"
                    f"**New Roles:** {', '.join([r.mention for r in after.roles if r != after.guild.default_role])}\n",
                    colour=self.bot.constants.embed,
                    timestamp=datetime.utcnow(),
                )
                embed.set_author(name=f"Role Updates")
                embed.set_footer(text=f"User ID: {after.id}")

                await self.send_webhook(webhook, embed=embed)

    @commands.Cog.listener()
    @decorators.wait_until_ready()
    @decorators.event_check(lambda s, b, a: not a.bot)
    async def on_user_update(self, before, after):
        for guild in after.mutual_guilds:
            webhook = self.get_webhook(guild, "users")
            if not webhook:
                continue

            if before.name != after.name:
                embed = discord.Embed(
                    description=f"**User:** {after.mention} **Name:** `{after}`\n"
                    f"**Old Username:** `{before.name}`\n"
                    f"**New Username:** `{after.name}`\n",
                    colour=self.bot.constants.embed,
                    timestamp=datetime.utcnow(),
                )
                embed.set_author(name=f"Username Change")
                embed.set_footer(text=f"User ID: {after.id}")

                await self.send_webhook(webhook, embed=embed)

            elif before.discriminator != after.discriminator:
                embed = discord.Embed(
                    description=f"**User:** {after.mention} **Name:** `{after}`\n"
                    f"**Old Discriminator:** `{before.discriminator}`\n"
                    f"**New Discriminator:** `{after.discriminator}`\n",
                    colour=self.bot.constants.embed,
                    timestamp=datetime.utcnow(),
                )
                embed.set_author(name=f"Discriminator Change")
                embed.set_footer(text=f"User ID: {after.id}")

                await self.send_webhook(webhook, embed=embed)

            elif before.avatar_url != after.avatar_url:
                embed = discord.Embed(
                    description=f"**User:** {after.mention} **Name:** `{after}`\n"
                    "New image below, old image to the right.",
                    colour=self.bot.constants.embed,
                    timestamp=datetime.utcnow(),
                )

                embed.set_thumbnail(url=before.avatar_url)
                embed.set_image(url=after.avatar_url)
                embed.set_author(name=f"Avatar Change")
                embed.set_footer(text=f"User ID: {after.id}")
                await self.send_webhook(webhook, embed=embed)

    @commands.Cog.listener()
    @decorators.wait_until_ready()
    @decorators.event_check(lambda s, m, b, a: not m.bot)
    async def on_voice_state_update(self, member, before, after):
        webhook = self.get_webhook(member.guild, "voice")
        if not webhook:
            return

        if not before.channel and after.channel:
            embed = discord.Embed(
                description=f"**User:** {member.mention} **Name:** `{member}`\n**Channel:** {after.channel.mention} ID: `{after.channel.id}`\n",
                colour=self.bot.constants.embed,
                timestamp=datetime.utcnow(),
            )
            embed.set_author(name=f"User Joined Voice Channel")
            embed.set_footer(text=f"User ID: {member.id}")

            await self.send_webhook(webhook, embed=embed)

        elif before.channel and not after.channel:
            embed = discord.Embed(
                description=f"**User:** {member.mention} **Name:** `{member}`\n**Channel:** {before.channel.mention} **ID:** `{before.channel.id}`\n",
                colour=self.bot.constants.embed,
                timestamp=datetime.utcnow(),
            )
            embed.set_author(name=f"User Left Voice Channel")
            embed.set_footer(text=f"User ID: {member.id}")

            await self.send_webhook(webhook, embed=embed)

        elif before.channel and after.channel:
            if before.channel.id != after.channel.id:
                embed = discord.Embed(
                    description=f"**User:** {member.mention} **Name:** `{member}`\n"
                    f"**Old Channel:** {before.channel.mention} **ID:** `{before.channel.id}`\n"
                    f"**New Channel:** {after.channel.mention} **ID:** `{after.channel.id}`\n",
                    colour=self.bot.constants.embed,
                    timestamp=datetime.utcnow(),
                )
                embed.set_author(name=f"User Switched Voice Channels")
                embed.set_footer(text=f"User ID: {member.id}")

                await self.send_webhook(webhook, embed=embed)

    @commands.Cog.listener()
    @decorators.wait_until_ready()
    @decorators.event_check(lambda s, b, a: a.guild and not a.author.bot)
    async def on_message_edit(self, before, after):
        if before.content == after.content:
            return  # giphy, tenor, and imgur links trigger this but they shouldn't be logged

        webhook = self.get_webhook(after.guild, "messages")
        if not webhook:
            return

        if before.content == "":
            bcontent = "```fix\nNo Content```" + "**\n**"
        elif before.content.startswith("```"):
            bcontent = self.truncate(before.clean_content, 1000) + "**\n**"
        else:
            bcontent = (
                f"```fix\n{self.truncate(before.clean_content, 1000)}```" + "**\n**"
            )

        if after.content == "":
            acontent = "```fix\nNo Content```"
        elif after.content.startswith("```"):
            acontent = self.truncate(after.clean_content, 1000)
        else:
            acontent = f"```fix\n{self.truncate(after.clean_content, 1000)}```"

        jump_url = f"**[Jump to message](https://discord.com/channels/{after.guild.id}/{after.channel.id}/{after.id})**"
        embed = discord.Embed(
            description=f"**Author:**  {after.author.mention} **ID:** `{after.author.id}`\n"
            f"**Channel:** {after.channel.mention} **ID:** `{after.channel.id}`\n"
            f"**Server:** `{after.guild.name}` **ID:** `{after.guild.id}`\n **\n**",
            color=self.bot.constants.embed,
            timestamp=datetime.utcnow(),
        )
        embed.add_field(
            name="__**Old Message Content**__", value=bcontent, inline=False
        )
        embed.add_field(
            name="__**New Message Content**__", value=acontent, inline=False
        )
        embed.add_field(name="** **", value=jump_url)
        embed.set_author(
            name="Message Edited",
            icon_url=UPDATED_MESSAGE,
        )
        embed.set_footer(text=f"Message ID: {after.id}")
        await self.send_webhook(webhook, embed=embed)

    @commands.Cog.listener()
    @decorators.wait_until_ready()
    @decorators.event_check(lambda s, m: m.guild and not m.author.bot)
    async def on_message_delete(self, message):

        webhook = self.get_webhook(message.guild, "messages")
        if not webhook:
            return

        if message.content == "":
            content = ""
        elif message.content.startswith("```"):
            content = f"**__Message Content__**\n {message.clean_content}"
        else:
            content = f"**__Message Content__**\n ```fix\n{message.clean_content}```"

        if len(message.attachments):
            attachment_list = "\n".join(
                [f"[**`{x.filename}`**]({x.url})" for x in message.attachments]
            )
            attachments = f"**__Attachment{'' if len(message.attachments) == 1 else 's'}__**\n {attachment_list}"
            if message.content != "":
                content = content + "\n"
        else:
            attachments = ""
        embed = discord.Embed(
            description=f"**Author:**  {message.author.mention}, **ID:** `{message.author.id}`\n"
            f"**Channel:** {message.channel.mention} **ID:** `{message.channel.id}`\n"
            f"**Server:** `{message.guild.name}` **ID:** `{message.guild.id}`\n\n"
            f"{content}"
            f"{attachments}",
            color=self.bot.constants.embed,
            timestamp=datetime.utcnow(),
        )
        embed.set_author(
            name="Message Deleted",
            icon_url=DELETED_MESSAGE,
        )
        embed.set_footer(text=f"Message ID: {message.id}")
        await self.send_webhook(webhook, embed=embed)

    @commands.Cog.listener()
    @decorators.wait_until_ready()
    @decorators.event_check(lambda s, m: m[0].guild is not None)
    async def on_bulk_message_delete(self, messages):

        webhook = self.get_webhook(messages[0].guild, "messages")
        if not webhook:
            return

        allmessages = ""
        spaces = " " * 10
        for message in messages:
            if message.author.bot:
                continue
            allmessages += f"Content: {message.content}{spaces}Author: {message.author}{spaces}ID: {message.id}\n\n"

        embed = discord.Embed(
            description=f"**Channel:** {message.channel.mention} **ID:** `{message.channel.id}`\n"
            f"**Server:** `{message.guild.name}` **ID:** `{message.guild.id}`\n\n",
            color=self.bot.constants.embed,
            timestamp=datetime.utcnow(),
        )
        embed.set_author(
            name="Bulk Message Delete",
            icon_url=DELETED_MESSAGE,
        )

        await self.send_webhook(webhook, embed=embed)

        counter = 0
        msg = ""
        for message in messages:
            counter += 1
            msg += message.content + "\n"
            msg += (
                "----Sent-By: "
                + message.author.name
                + "#"
                + message.author.discriminator
                + "\n"
            )
            msg += (
                "---------At: " + message.created_at.strftime("%Y-%m-%d %H.%M") + "\n"
            )
            if message.edited_at:
                msg += (
                    "--Edited-At: "
                    + message.edited_at.strftime("%Y-%m-%d %H.%M")
                    + "\n"
                )
            msg += "\n"

        data = io.BytesIO(msg[:-2].encode("utf-8"))

        file = discord.File(
            data,
            filename=f"Bulk-Deleted-Messages-{datetime.now().__format__('%m-%d-%Y')}.txt",
        )
        await self.send_webhook(webhook, file=file)

    ####################
    ## Other Commands ##
    ####################

    @decorators.group(
        aliases=["actioncount", "ac"],
        brief="Count the audit log entries of a user.",
        case_insensitive=True,
        invoke_without_command=True,
        implemented="2021-05-07 22:34:00.515826",
        updated="2021-05-07 22:34:00.515826",
        examples="""
                {0}ac
                {0}ac Hecate 4d
                {0}ac @Hecate
                {0}ac Hecate#3523 2m
                {0}ac 708584008065351681 5months
                {0}auditcount
                {0}auditcount Hecate 4d
                {0}auditcount @Hecate 3 years ago
                {0}auditcount Hecate#3523 2 minutes
                {0}auditcount 708584008065351681 6 months ago
                {0}actioncount
                {0}actioncount Hecate 4d
                {0}actioncount @Hecate yesterday
                {0}actioncount Hecate#3523 2m
                {0}actioncount 708584008065351681 5 months
                """,
    )
    @checks.bot_has_perms(view_audit_log=True)
    @checks.has_perms(view_audit_log=True)
    async def auditcount(
        self,
        ctx,
        user: converters.DiscordMember = None,
        *,
        after: humantime.PastTime = None,
    ):
        """
        Usage: {0}auditcount <user> [unit]
        Aliases: {0}actioncount, {0}ac
        Options:
            bans, botadds, bulkdeletes,
            channeladds, channeldeletes,
            channelupdates, deletes, emojiadds,
            emojideletes, emojiupdates,
            integrationadds, integrationdeletes,
            integrationupdates, inviteadds,
            invitedeletes, inviteupdates, kicks,
            moves, pins, roleadds, roledeletes,
            roleupdates, serverupdates, unbans,
            unpins, vckicks, webhookadds,
            webhookdeletes, webhookupdates
        Output:
            The number of audit log
            actions a user has caused
            across all time unless a time
            is specified.
        Notes:
            Will default to the total if no
            user is specified. Enter a
            past time argument to only
            check entry counts from after
            that day. If no subcommands
            are entered, the bot will
            count all the actions made.
        Explanation:
            {0}auditcount Hecate 3d
            This will select all audit
            entries made by the user Hecate
            in the past 3 days.
        """
        if not user:
            user = ctx.author
        msg = await self.get_action_count(
            ctx, user, after, None, "executed", "audit log actions"
        )
        await ctx.send_or_reply(self.bot.emote_dict["search"] + msg)

    @auditcount.command(
        aliases=["bc"],
        brief="Count the audit log entries of a user.",
        implemented="2021-05-07 22:34:00.515826",
        updated="2021-05-07 22:34:00.515826",
        examples="""
                {0}bc
                {0}bc Hecate 4d
                {0}bc @Hecate
                {0}bc Hecate#3523 2m
                {0}bc 708584008065351681 5months
                {0}bans
                {0}bans Hecate 4d
                {0}bans @Hecate yesterday
                {0}bans Hecate#3523 2m
                {0}bans 708584008065351681 5 months
                {0}bancount
                {0}bancount Hecate 4d
                {0}bancount @Hecate yesterday
                {0}bancount Hecate#3523 2m
                {0}bancount 708584008065351681 5 months
                """,
    )
    async def bans(
        self,
        ctx,
        user: converters.DiscordMember = None,
        *,
        after: humantime.PastTime = None,
    ):
        """
        Usage: {0}bans <user> [unit]
        Aliases: {0}bancount, {0}bc
        Output:
            The number of people a user
            has banned across all time,
            or after a specified time.
        Notes:
            Will default to you if no
            user is specified. Enter a
            past time argument to only
            check entry counts from after
            that day. If you wish to
            select audits by you and
            specify a past time argument,
            you must mention yourself.
        Explanation:
            {0}auditcount bans Hecate 3d
            This will select all ban
            entries made by the user
            Hecate in the past 3 days.
        """
        if not user:
            user = ctx.author
        msg = await self.get_action_count(
            ctx, user, after, discord.AuditLogAction.ban, "banned", "users"
        )
        await ctx.send_or_reply(self.bot.emote_dict["ban"] + msg)

    @auditcount.command()
    async def botadds(
        self,
        ctx,
        user: converters.DiscordMember = None,
        *,
        after: humantime.PastTime = None,
    ):
        """
        Usage: {0}botadds <user> [unit]
        Output:
            The number of bots  a user
            has invited to the server
            across all time unless a time
            is specified.
        Notes:
            Will default to you if no
            user is specified. Enter a
            past time argument to only
            check entry counts from after
            that day. If you wish to
            select audits by you and
            specify a past time argument,
            you must mention yourself.
        Explanation:
            {0}auditcount botadds Hecate 3d
            This will select all audit
            entries made by the user Hecate
            in the past 3 days.
        """
        if not user:
            user = ctx.author
        msg = await self.get_action_count(
            ctx, user, after, discord.AuditLogAction.bot_add, "added", "bots"
        )
        await ctx.send_or_reply(self.bot.emote_dict["robot"] + msg)

    @auditcount.command(
        aliases=["channelcreates"],
        brief="Count the audit log entries of a user.",
        implemented="2021-05-07 22:34:00.515826",
        updated="2021-05-07 22:34:00.515826",
        examples="""
                {0}bc
                {0}bc Hecate 4d
                {0}bc @Hecate
                {0}bc Hecate#3523 2m
                {0}bc 708584008065351681 5months
                {0}bans
                {0}bans Hecate 4d
                {0}bans @Hecate yesterday
                {0}bans Hecate#3523 2m
                {0}bans 708584008065351681 5 months
                {0}bancount
                {0}bancount Hecate 4d
                {0}bancount @Hecate yesterday
                {0}bancount Hecate#3523 2m
                {0}bancount 708584008065351681 5 months
                """,
    )
    async def channeladds(
        self,
        ctx,
        user: converters.DiscordMember = None,
        *,
        after: humantime.PastTime = None,
    ):
        """
        Usage: {0}channeladds <user> [unit]
        Aliases: {0}channelcreates
        Output:
            The number of channels a user
            has created in the server
            across all time unless a time
            is specified.
        Notes:
            Will default to you if no
            user is specified. Enter a
            past time argument to only
            check entry counts from after
            that day. If you wish to
            select audits by you and
            specify a past time argument,
            you must mention yourself.
        Explanation:
            {0}auditcount channeladds Hecate 3d
            This will select all audit
            entries made by the user Hecate
            in the past 3 days.
        """
        if not user:
            user = ctx.author
        msg = await self.get_action_count(
            ctx,
            user,
            after,
            discord.AuditLogAction.channel_create,
            "created",
            "channels",
        )
        await ctx.send_or_reply(self.bot.emote_dict["plus"] + msg)

    @auditcount.command(
        aliases=["channelchanges"],
        brief="Count the audit log entries of a user.",
        implemented="2021-05-07 22:34:00.515826",
        updated="2021-05-07 22:34:00.515826",
        examples="""
                {0}bc
                {0}bc Hecate 4d
                {0}bc @Hecate
                {0}bc Hecate#3523 2m
                {0}bc 708584008065351681 5months
                {0}bans
                {0}bans Hecate 4d
                {0}bans @Hecate yesterday
                {0}bans Hecate#3523 2m
                {0}bans 708584008065351681 5 months
                {0}bancount
                {0}bancount Hecate 4d
                {0}bancount @Hecate yesterday
                {0}bancount Hecate#3523 2m
                {0}bancount 708584008065351681 5 months
                """,
    )
    async def channelupdates(
        self,
        ctx,
        user: converters.DiscordMember = None,
        *,
        after: humantime.PastTime = None,
    ):
        """
        Usage: {0}channelupdates <user> [unit]
        Aliases: {0}channelchanges
        Output:
            The number of channels a user
            has updated in the server across
            all time unless a time is specified.
        Notes:
            Will default to you if no
            user is specified. Enter a
            past time argument to only
            check entry counts from after
            that day. If you wish to
            select audits by you and
            specify a past time argument,
            you must mention yourself.
        Explanation:
            {0}auditcount channelupdates Hecate 3d
            This will select all audit
            entries made by the user Hecate
            in the past 3 days.
        """
        if not user:
            user = ctx.author
        msg = await self.get_action_count(
            ctx,
            user,
            after,
            discord.AuditLogAction.channel_update,
            "updated",
            "channels",
        )
        await ctx.send_or_reply(self.bot.emote_dict["redo"] + msg)

    @auditcount.command(
        aliases=["channelremoves"],
        brief="Count the audit log entries of a user.",
        implemented="2021-05-07 22:34:00.515826",
        updated="2021-05-07 22:34:00.515826",
        examples="""
                {0}bc
                {0}bc Hecate 4d
                {0}bc @Hecate
                {0}bc Hecate#3523 2m
                {0}bc 708584008065351681 5months
                {0}bans
                {0}bans Hecate 4d
                {0}bans @Hecate yesterday
                {0}bans Hecate#3523 2m
                {0}bans 708584008065351681 5 months
                {0}bancount
                {0}bancount Hecate 4d
                {0}bancount @Hecate yesterday
                {0}bancount Hecate#3523 2m
                {0}bancount 708584008065351681 5 months
                """,
    )
    async def channeldeletes(
        self,
        ctx,
        user: converters.DiscordMember = None,
        *,
        after: humantime.PastTime = None,
    ):
        """
        Usage: {0}channeldeletes <user> [unit]
        Aliases: {0}channelremoves
        Output:
            The number of channels a user
            has created in the server across
            all time unless a time is specified.
        Notes:
            Will default to you if no
            user is specified. Enter a
            past time argument to only
            check entry counts from after
            that day. If you wish to
            select audits by you and
            specify a past time argument,
            you must mention yourself.
        Explanation:
            {0}auditcount channeldeletes Hecate 3d
            This will select all audit
            entries made by the user Hecate
            in the past 3 days.
        """
        if not user:
            user = ctx.author
        msg = await self.get_action_count(
            ctx,
            user,
            after,
            discord.AuditLogAction.channel_delete,
            "deleted",
            "channels",
        )
        await ctx.send_or_reply(self.bot.emote_dict["minus"] + msg)

    @auditcount.command(
        aliases=["emojicreates", "emoteadds", "emotecreates"],
        brief="Count the audit log entries of a user.",
        implemented="2021-05-07 22:34:00.515826",
        updated="2021-05-07 22:34:00.515826",
        examples="""
                {0}bc
                {0}bc Hecate 4d
                {0}bc @Hecate
                {0}bc Hecate#3523 2m
                {0}bc 708584008065351681 5months
                {0}bans
                {0}bans Hecate 4d
                {0}bans @Hecate yesterday
                {0}bans Hecate#3523 2m
                {0}bans 708584008065351681 5 months
                {0}bancount
                {0}bancount Hecate 4d
                {0}bancount @Hecate yesterday
                {0}bancount Hecate#3523 2m
                {0}bancount 708584008065351681 5 months
                """,
    )
    async def emojiadds(
        self,
        ctx,
        user: converters.DiscordMember = None,
        *,
        after: humantime.PastTime = None,
    ):
        """
        Usage: {0}emojiadds <user> [unit]
        Aliases:
            {0}emojicreates,
            {0}emoteadds,
            {0}emotecreates
        Output:
            The number of emojis a user
            has created in the server
            across all time unless a time
            is specified.
        Notes:
            Will default to you if no
            user is specified. Enter a
            past time argument to only
            check entry counts from after
            that day. If you wish to
            select audits by you and
            specify a past time argument,
            you must mention yourself.
        Explanation:
            {0}auditcount channeldeletes Hecate 3d
            This will select all audit
            entries made by the user Hecate
            in the past 3 days.
        """
        if not user:
            user = ctx.author
        msg = await self.get_action_count(
            ctx, user, after, discord.AuditLogAction.emoji_create, "created", "emojis"
        )
        await ctx.send_or_reply(self.bot.emote_dict["plus"] + msg)

    @auditcount.command(
        aliases=["emojichanges"],
        brief="Count the audit log entries of a user.",
        implemented="2021-05-07 22:34:00.515826",
        updated="2021-05-07 22:34:00.515826",
        examples="""
                {0}bc
                {0}bc Hecate 4d
                {0}bc @Hecate
                {0}bc Hecate#3523 2m
                {0}bc 708584008065351681 5months
                {0}bans
                {0}bans Hecate 4d
                {0}bans @Hecate yesterday
                {0}bans Hecate#3523 2m
                {0}bans 708584008065351681 5 months
                {0}bancount
                {0}bancount Hecate 4d
                {0}bancount @Hecate yesterday
                {0}bancount Hecate#3523 2m
                {0}bancount 708584008065351681 5 months
                """,
    )
    async def emojiupdates(
        self,
        ctx,
        user: converters.DiscordMember = None,
        *,
        after: humantime.PastTime = None,
    ):
        """
        Usage: {0}emojiupdates <user> [unit]
        Aliases: {0}emojichanges
        Output:
            The number of emojis a user
            has updated in the server
            across all time unless a time
            is specified.
        Notes:
            Will default to you if no
            user is specified. Enter a
            past time argument to only
            check entry counts from after
            that day. If you wish to
            select audits by you and
            specify a past time argument,
            you must mention yourself.
        Explanation:
            {0}auditcount emojiupdates Hecate 3d
            This will select all audit
            entries made by the user Hecate
            in the past 3 days.
        """
        if not user:
            user = ctx.author
        msg = await self.get_action_count(
            ctx, user, after, discord.AuditLogAction.emoji_update, "updated", "emojis"
        )
        await ctx.send_or_reply(self.bot.emote_dict["redo"] + msg)

    @auditcount.command(
        aliases=["emojiremoves"],
        brief="Count the audit log entries of a user.",
        implemented="2021-05-07 22:34:00.515826",
        updated="2021-05-07 22:34:00.515826",
        examples="""
                {0}bc
                {0}bc Hecate 4d
                {0}bc @Hecate
                {0}bc Hecate#3523 2m
                {0}bc 708584008065351681 5months
                {0}bans
                {0}bans Hecate 4d
                {0}bans @Hecate yesterday
                {0}bans Hecate#3523 2m
                {0}bans 708584008065351681 5 months
                {0}bancount
                {0}bancount Hecate 4d
                {0}bancount @Hecate yesterday
                {0}bancount Hecate#3523 2m
                {0}bancount 708584008065351681 5 months
                """,
    )
    async def emojideletes(
        self,
        ctx,
        user: converters.DiscordMember = None,
        *,
        after: humantime.PastTime = None,
    ):
        """
        Usage: {0}emojideletes <user> [unit]
        Aliases: {0}emojiremoves
        Output:
            The number of emojis a user
            has deleted in the server
            across all time unless a time
            is specified.
        Notes:
            Will default to you if no
            user is specified. Enter a
            past time argument to only
            check entry counts from after
            that day. If you wish to
            select audits by you and
            specify a past time argument,
            you must mention yourself.
        Explanation:
            {0}auditcount emojiremoves Hecate 3d
            This will select all audit
            entries made by the user Hecate
            in the past 3 days.
        """
        if not user:
            user = ctx.author
        msg = await self.get_action_count(
            ctx, user, after, discord.AuditLogAction.emoji_delete, "deleted", "emojis"
        )
        await ctx.send_or_reply(self.bot.emote_dict["minus"] + msg)

    @auditcount.command(
        aliases=["serverchanges", "guildupdates", "guildchanges"],
        brief="Count the audit log entries of a user.",
        implemented="2021-05-07 22:34:00.515826",
        updated="2021-05-07 22:34:00.515826",
        examples="""
                {0}bc
                {0}bc Hecate 4d
                {0}bc @Hecate
                {0}bc Hecate#3523 2m
                {0}bc 708584008065351681 5months
                {0}bans
                {0}bans Hecate 4d
                {0}bans @Hecate yesterday
                {0}bans Hecate#3523 2m
                {0}bans 708584008065351681 5 months
                {0}bancount
                {0}bancount Hecate 4d
                {0}bancount @Hecate yesterday
                {0}bancount Hecate#3523 2m
                {0}bancount 708584008065351681 5 months
                """,
    )
    async def serverupdates(
        self,
        ctx,
        user: converters.DiscordMember = None,
        *,
        after: humantime.PastTime = None,
    ):
        """
        Usage: {0}serverupdates <user> [unit]
        Aliases:
            {0}serverchanges,
            {0}guildupdates,
            {0}guildchanges
        Output:
            The number of updates a user has
            made to the server across all
            time unless a time is specified.
        Notes:
            Will default to you if no
            user is specified. Enter a
            past time argument to only
            check entry counts from after
            that day. If you wish to
            select audits by you and
            specify a past time argument,
            you must mention yourself.
        Explanation:
            {0}auditcount serverupdates Hecate 3d
            This will select all audit
            entries made by the user
            Hecate in the past 3 days.
        """
        if not user:
            user = ctx.author
        msg = await self.get_action_count(
            ctx,
            user,
            after,
            discord.AuditLogAction.guild_update,
            "updated the server",
            "times",
        )
        await ctx.send_or_reply(self.bot.emote_dict["redo"] + msg)

    @auditcount.command(
        aliases=["integrationcreates"],
        brief="Count the audit log entries of a user.",
        implemented="2021-05-07 22:34:00.515826",
        updated="2021-05-07 22:34:00.515826",
        examples="""
                {0}bc
                {0}bc Hecate 4d
                {0}bc @Hecate
                {0}bc Hecate#3523 2m
                {0}bc 708584008065351681 5months
                {0}bans
                {0}bans Hecate 4d
                {0}bans @Hecate yesterday
                {0}bans Hecate#3523 2m
                {0}bans 708584008065351681 5 months
                {0}bancount
                {0}bancount Hecate 4d
                {0}bancount @Hecate yesterday
                {0}bancount Hecate#3523 2m
                {0}bancount 708584008065351681 5 months
                """,
    )
    async def integrationadds(
        self,
        ctx,
        user: converters.DiscordMember = None,
        *,
        after: humantime.PastTime = None,
    ):
        """
        Usage: {0}integrationadds <user> [unit]
        Alias: {0}integrationcreates
        Output:
            The number of integrations a user
            has created in the server across
            all time unless a time is specified.
        Notes:
            Will default to you if no
            user is specified. Enter a
            past time argument to only
            check entry counts from after
            that day. If you wish to
            select audits by you and
            specify a past time argument,
            you must mention yourself.
        Explanation:
            {0}integrationadds Hecate 3d
            This will select all audit
            entries made by the user
            Hecate in the past 3 days.
        """
        if not user:
            user = ctx.author
        msg = await self.get_action_count(
            ctx,
            user,
            after,
            discord.AuditLogAction.integration_create,
            "created",
            "integrations",
        )
        await ctx.send_or_reply(self.bot.emote_dict["plus"] + msg)

    @auditcount.command(
        aliases=["integrationchanges"],
        brief="Count the audit log entries of a user.",
        implemented="2021-05-07 22:34:00.515826",
        updated="2021-05-07 22:34:00.515826",
        examples="""
                {0}bc
                {0}bc Hecate 4d
                {0}bc @Hecate
                {0}bc Hecate#3523 2m
                {0}bc 708584008065351681 5months
                {0}bans
                {0}bans Hecate 4d
                {0}bans @Hecate yesterday
                {0}bans Hecate#3523 2m
                {0}bans 708584008065351681 5 months
                {0}bancount
                {0}bancount Hecate 4d
                {0}bancount @Hecate yesterday
                {0}bancount Hecate#3523 2m
                {0}bancount 708584008065351681 5 months
                """,
    )
    async def integrationupdates(
        self,
        ctx,
        user: converters.DiscordMember = None,
        *,
        after: humantime.PastTime = None,
    ):
        """
        Usage: {0}integrationupdates <user> [unit]
        Alias: {0}integrationchanges
        Output:
            The number of integrations a user
            has created in the server across
            all time unless a time is specified.
        Notes:
            Will default to you if no
            user is specified. Enter a
            past time argument to only
            check entry counts from after
            that day. If you wish to
            select audits by you and
            specify a past time argument,
            you must mention yourself.
        Explanation:
            {0}auditcount integrationupdates Hecate 3d
            This will select all audit
            entries made by the user
            Hecate in the past 3 days.
        """
        if not user:
            user = ctx.author
        msg = await self.get_action_count(
            ctx,
            user,
            after,
            discord.AuditLogAction.integration_update,
            "updated",
            "integrations",
        )
        await ctx.send_or_reply(self.bot.emote_dict["redo"] + msg)

    @auditcount.command(
        aliases=["integrationremoves"],
        brief="Count the audit log entries of a user.",
        implemented="2021-05-07 22:34:00.515826",
        updated="2021-05-07 22:34:00.515826",
        examples="""
                {0}bc
                {0}bc Hecate 4d
                {0}bc @Hecate
                {0}bc Hecate#3523 2m
                {0}bc 708584008065351681 5months
                {0}bans
                {0}bans Hecate 4d
                {0}bans @Hecate yesterday
                {0}bans Hecate#3523 2m
                {0}bans 708584008065351681 5 months
                {0}bancount
                {0}bancount Hecate 4d
                {0}bancount @Hecate yesterday
                {0}bancount Hecate#3523 2m
                {0}bancount 708584008065351681 5 months
                """,
    )
    async def integrationdeletes(
        self,
        ctx,
        user: converters.DiscordMember = None,
        *,
        after: humantime.PastTime = None,
    ):
        """
        Usage: {0}integrationdeletes <user> [unit]
        Alias: {0}integrationremoves
        Output:
            The number of integrations a user
            has deleted in the server across
            all time unless a time is specified.
        Notes:
            Will default to you if no
            user is specified. Enter a
            past time argument to only
            check entry counts from after
            that day. If you wish to
            select audits by you and
            specify a past time argument,
            you must mention yourself.
        Explanation:
            {0}auditcount integrationdeletes Hecate 3d
            This will select all audit
            entries made by the user
            Hecate in the past 3 days.
        """
        if not user:
            user = ctx.author
        msg = await self.get_action_count(
            ctx,
            user,
            after,
            discord.AuditLogAction.integration_delete,
            "deleted",
            "integrations",
        )
        await ctx.send_or_reply(self.bot.emote_dict["minus"] + msg)

    @auditcount.command(
        aliases=["invitecreates"],
        brief="Count the audit log entries of a user.",
        implemented="2021-05-07 22:34:00.515826",
        updated="2021-05-07 22:34:00.515826",
        examples="""
                {0}bc
                {0}bc Hecate 4d
                {0}bc @Hecate
                {0}bc Hecate#3523 2m
                {0}bc 708584008065351681 5months
                {0}bans
                {0}bans Hecate 4d
                {0}bans @Hecate yesterday
                {0}bans Hecate#3523 2m
                {0}bans 708584008065351681 5 months
                {0}bancount
                {0}bancount Hecate 4d
                {0}bancount @Hecate yesterday
                {0}bancount Hecate#3523 2m
                {0}bancount 708584008065351681 5 months
                """,
    )
    async def inviteadds(
        self,
        ctx,
        user: converters.DiscordMember = None,
        *,
        after: humantime.PastTime = None,
    ):
        """
        Usage: {0}inviteadds <user> [unit]
        Alias: {0}invitecreates
        Output:
            The number of invites a user has
            created in the server across all
            time unless a time is specified.
        Notes:
            Will default to you if no
            user is specified. Enter a
            past time argument to only
            check entry counts from after
            that day. If you wish to
            select audits by you and
            specify a past time argument,
            you must mention yourself.
        Explanation:
            {0}auditcount inviteadds Hecate 3d
            This will select all audit
            entries made by the user
            Hecate in the past 3 days.
        """
        if not user:
            user = ctx.author
        msg = await self.get_action_count(
            ctx,
            user,
            after,
            discord.AuditLogAction.invite_create,
            "created",
            "invite links",
        )
        await ctx.send_or_reply(self.bot.emote_dict["plus"] + msg)

    @auditcount.command(
        aliases=["invitechanges"],
        brief="Count the audit log entries of a user.",
        implemented="2021-05-07 22:34:00.515826",
        updated="2021-05-07 22:34:00.515826",
        examples="""
                {0}bc
                {0}bc Hecate 4d
                {0}bc @Hecate
                {0}bc Hecate#3523 2m
                {0}bc 708584008065351681 5months
                {0}bans
                {0}bans Hecate 4d
                {0}bans @Hecate yesterday
                {0}bans Hecate#3523 2m
                {0}bans 708584008065351681 5 months
                {0}bancount
                {0}bancount Hecate 4d
                {0}bancount @Hecate yesterday
                {0}bancount Hecate#3523 2m
                {0}bancount 708584008065351681 5 months
                """,
    )
    async def inviteupdates(
        self,
        ctx,
        user: converters.DiscordMember = None,
        *,
        after: humantime.PastTime = None,
    ):
        """
        Usage: {0}inviteupdates <user> [unit]
        Alias: {0}invitechanges
        Output:
            The number of invites a user has
            updated in the server across all
            time unless a time is specified.
        Notes:
            Will default to you if no
            user is specified. Enter a
            past time argument to only
            check entry counts from after
            that day. If you wish to
            select audits by you and
            specify a past time argument,
            you must mention yourself.
        Explanation:
            {0}auditcount inviteupdates Hecate 3d
            This will select all audit
            entries made by the user
            Hecate in the past 3 days.
        """
        if not user:
            user = ctx.author
        msg = await self.get_action_count(
            ctx,
            user,
            after,
            discord.AuditLogAction.invite_update,
            "updated",
            "invite links",
        )
        await ctx.send_or_reply(self.bot.emote_dict["redo"] + msg)

    @auditcount.command(
        aliases=["inviteremoves"],
        brief="Count the audit log entries of a user.",
        implemented="2021-05-07 22:34:00.515826",
        updated="2021-05-07 22:34:00.515826",
        examples="""
                {0}bc
                {0}bc Hecate 4d
                {0}bc @Hecate
                {0}bc Hecate#3523 2m
                {0}bc 708584008065351681 5months
                {0}bans
                {0}bans Hecate 4d
                {0}bans @Hecate yesterday
                {0}bans Hecate#3523 2m
                {0}bans 708584008065351681 5 months
                {0}bancount
                {0}bancount Hecate 4d
                {0}bancount @Hecate yesterday
                {0}bancount Hecate#3523 2m
                {0}bancount 708584008065351681 5 months
                """,
    )
    async def invitedeletes(
        self,
        ctx,
        user: converters.DiscordMember = None,
        *,
        after: humantime.PastTime = None,
    ):
        """
        Usage: {0}invitedeletes <user> [unit]
        Alias: {0}inviteremoves
        Output:
            The number of invites a user has
            updated in the server across all
            time unless a time is specified.
        Notes:
            Will default to you if no
            user is specified. Enter a
            past time argument to only
            check entry counts from after
            that day. If you wish to
            select audits by you and
            specify a past time argument,
            you must mention yourself.
        Explanation:
            {0}auditcount inviteupdates Hecate 3d
            This will select all audit
            entries made by the user
            Hecate in the past 3 days.
        """
        if not user:
            user = ctx.author
        msg = await self.get_action_count(
            ctx,
            user,
            after,
            discord.AuditLogAction.invite_delete,
            "deleted",
            "invite links",
        )
        await ctx.send_or_reply(self.bot.emote_dict["minus"] + msg)

    @auditcount.command(
        aliases=["kickcount", "kc"],
        brief="Count the audit log entries of a user.",
        implemented="2021-05-07 22:34:00.515826",
        updated="2021-05-07 22:34:00.515826",
        examples="""
                {0}bc
                {0}bc Hecate 4d
                {0}bc @Hecate
                {0}bc Hecate#3523 2m
                {0}bc 708584008065351681 5months
                {0}bans
                {0}bans Hecate 4d
                {0}bans @Hecate yesterday
                {0}bans Hecate#3523 2m
                {0}bans 708584008065351681 5 months
                {0}bancount
                {0}bancount Hecate 4d
                {0}bancount @Hecate yesterday
                {0}bancount Hecate#3523 2m
                {0}bancount 708584008065351681 5 months
                """,
    )
    async def kicks(
        self,
        ctx,
        user: converters.DiscordMember = None,
        *,
        after: humantime.PastTime = None,
    ):
        """
        Usage: {0}kicks <user> [unit]
        Aliases: {0}kickcount, {0}kc
        Output:
            The number of users a user has
            kicked in the server across all
            time unless a time is specified.
        Notes:
            Will default to you if no
            user is specified. Enter a
            past time argument to only
            check entry counts from after
            that day. If you wish to
            select audits by you and
            specify a past time argument,
            you must mention yourself.
        Explanation:
            {0}auditcount kicks Hecate 3d
            This will select all audit
            entries made by the user
            Hecate in the past 3 days.
        """
        if not user:
            user = ctx.author
        msg = await self.get_action_count(
            ctx, user, after, discord.AuditLogAction.kick, "kicked", "users"
        )
        await ctx.send_or_reply(self.bot.emote_dict["kick"] + msg)

    @auditcount.command(
        aliases=["vckickvount", "vckc"],
        brief="Count the audit log entries of a user.",
        implemented="2021-05-07 22:34:00.515826",
        updated="2021-05-07 22:34:00.515826",
        examples="""
                {0}bc
                {0}bc Hecate 4d
                {0}bc @Hecate
                {0}bc Hecate#3523 2m
                {0}bc 708584008065351681 5months
                {0}bans
                {0}bans Hecate 4d
                {0}bans @Hecate yesterday
                {0}bans Hecate#3523 2m
                {0}bans 708584008065351681 5 months
                {0}bancount
                {0}bancount Hecate 4d
                {0}bancount @Hecate yesterday
                {0}bancount Hecate#3523 2m
                {0}bancount 708584008065351681 5 months
                """,
    )
    async def vckicks(
        self,
        ctx,
        user: converters.DiscordMember = None,
        *,
        after: humantime.PastTime = None,
    ):
        """
        Usage: {0}vckicks <user> [unit]
        Aliases: {0}vckickcount, {0}vckc
        Output:
            The number of users a user has
            voice kicked in the server across
            all time unless a time is specified.
        Notes:
            Will default to you if no
            user is specified. Enter a
            past time argument to only
            check entry counts from after
            that day. If you wish to
            select audits by you and
            specify a past time argument,
            you must mention yourself.
        Explanation:
            {0}auditcount vckicks Hecate 3d
            This will select all audit
            entries made by the user
            Hecate in the past 3 days.
        """
        if not user:
            user = ctx.author
        msg = await self.get_action_count(
            ctx,
            user,
            after,
            discord.AuditLogAction.member_disconnect,
            "vckicked",
            "users",
        )
        await ctx.send_or_reply(self.bot.emote_dict["audioremove"] + msg)

    @auditcount.command(
        aliases=["vcmoves", "vcmvs"],
        brief="Count the audit log entries of a user.",
        implemented="2021-05-07 22:34:00.515826",
        updated="2021-05-07 22:34:00.515826",
        examples="""
                {0}bc
                {0}bc Hecate 4d
                {0}bc @Hecate
                {0}bc Hecate#3523 2m
                {0}bc 708584008065351681 5months
                {0}bans
                {0}bans Hecate 4d
                {0}bans @Hecate yesterday
                {0}bans Hecate#3523 2m
                {0}bans 708584008065351681 5 months
                {0}bancount
                {0}bancount Hecate 4d
                {0}bancount @Hecate yesterday
                {0}bancount Hecate#3523 2m
                {0}bancount 708584008065351681 5 months
                """,
    )
    async def moves(
        self,
        ctx,
        user: converters.DiscordMember = None,
        *,
        after: humantime.PastTime = None,
    ):
        """
        Usage: {0}moves <user> [unit]
        Aliases: {0}vcmoves, {0}vcmvs
        Output:
            The number of users a user has
            voice moved in the server across
            all time unless a time is specified.
        Notes:
            Will default to you if no
            user is specified. Enter a
            past time argument to only
            check entry counts from after
            that day. If you wish to
            select audits by you and
            specify a past time argument,
            you must mention yourself.
        Explanation:
            {0}auditcount moves Hecate 3d
            This will select all audit
            entries made by the user
            Hecate in the past 3 days.
        """
        if not user:
            user = ctx.author
        msg = await self.get_action_count(
            ctx, user, after, discord.AuditLogAction.member_move, "vcmoved", "users"
        )
        await ctx.send_or_reply(self.bot.emote_dict["forward1"] + msg)

    @auditcount.command(
        aliases=["bds", "bd"],
        brief="Count the audit log entries of a user.",
        implemented="2021-05-07 22:34:00.515826",
        updated="2021-05-07 22:34:00.515826",
        examples="""
                {0}bc
                {0}bc Hecate 4d
                {0}bc @Hecate
                {0}bc Hecate#3523 2m
                {0}bc 708584008065351681 5months
                {0}bans
                {0}bans Hecate 4d
                {0}bans @Hecate yesterday
                {0}bans Hecate#3523 2m
                {0}bans 708584008065351681 5 months
                {0}bancount
                {0}bancount Hecate 4d
                {0}bancount @Hecate yesterday
                {0}bancount Hecate#3523 2m
                {0}bancount 708584008065351681 5 months
                """,
    )
    async def bulkdeletes(
        self,
        ctx,
        user: converters.DiscordMember = None,
        *,
        after: humantime.PastTime = None,
    ):
        """
        Usage: {0}bulkdeletes <user> [unit]
        Aliases: {0}bds, {0}bd
        Output:
            The number of times a user has
            bulk deleted in the server across
            all time unless a time is specified.
        Notes:
            Will default to you if no
            user is specified. Enter a
            past time argument to only
            check entry counts from after
            that day. If you wish to
            select audits by you and
            specify a past time argument,
            you must mention yourself.
        Explanation:
            {0}auditcount bulkdeletes Hecate 3d
            This will select all audit
            entries made by the user
            Hecate in the past 3 days.
        """
        if not user:
            user = ctx.author
        msg = await self.get_action_count(
            ctx,
            user,
            after,
            discord.AuditLogAction.message_bulk_delete,
            "bulk deleted messages",
            "times",
        )
        await ctx.send_or_reply(self.bot.emote_dict["trash"] + msg)

    @auditcount.command(
        aliases=["removes"],
        brief="Count the audit log entries of a user.",
        implemented="2021-05-07 22:34:00.515826",
        updated="2021-05-07 22:34:00.515826",
        examples="""
                {0}bc
                {0}bc Hecate 4d
                {0}bc @Hecate
                {0}bc Hecate#3523 2m
                {0}bc 708584008065351681 5months
                {0}bans
                {0}bans Hecate 4d
                {0}bans @Hecate yesterday
                {0}bans Hecate#3523 2m
                {0}bans 708584008065351681 5 months
                {0}bancount
                {0}bancount Hecate 4d
                {0}bancount @Hecate yesterday
                {0}bancount Hecate#3523 2m
                {0}bancount 708584008065351681 5 months
                """,
    )
    async def deletes(
        self,
        ctx,
        user: converters.DiscordMember = None,
        *,
        after: humantime.PastTime = None,
    ):
        """
        Usage: {0}deletes <user> [unit]
        Alias: {0}removes
        Output:
            The number of times a user has deleted
            a message in the server across all time
            unless a time is specified.
        Notes:
            Will default to you if no
            user is specified. Enter a
            past time argument to only
            check entry counts from after
            that day. If you wish to
            select audits by you and
            specify a past time argument,
            you must mention yourself.
        Explanation:
            {0}auditcount deletes Hecate 3d
            This will select all audit
            entries made by the user
            Hecate in the past 3 days.
        """
        if not user:
            user = ctx.author
        msg = await self.get_action_count(
            ctx,
            user,
            after,
            discord.AuditLogAction.message_delete,
            "deleted",
            "messages",
        )
        await ctx.send_or_reply(self.bot.emote_dict["trash"] + msg)

    @auditcount.command(
        aliases=["pincount", "pc"],
        brief="Count the audit log entries of a user.",
        implemented="2021-05-07 22:34:00.515826",
        updated="2021-05-07 22:34:00.515826",
        examples="""
                {0}bc
                {0}bc Hecate 4d
                {0}bc @Hecate
                {0}bc Hecate#3523 2m
                {0}bc 708584008065351681 5months
                {0}bans
                {0}bans Hecate 4d
                {0}bans @Hecate yesterday
                {0}bans Hecate#3523 2m
                {0}bans 708584008065351681 5 months
                {0}bancount
                {0}bancount Hecate 4d
                {0}bancount @Hecate yesterday
                {0}bancount Hecate#3523 2m
                {0}bancount 708584008065351681 5 months
                """,
    )
    async def pins(
        self,
        ctx,
        user: converters.DiscordMember = None,
        *,
        after: humantime.PastTime = None,
    ):
        """
        Usage: {0}pins <user> [unit]
        Aliases: {0}pincount, {0}pc
        Output:
            The number of times a user has
            pinned a message in the server
            across all time unless a time
            is specified.
        Notes:
            Will default to you if no
            user is specified. Enter a
            past time argument to only
            check entry counts from after
            that day. If you wish to
            select audits by you and
            specify a past time argument,
            you must mention yourself.
        Explanation:
            {0}auditcount pins Hecate 3d
            This will select all audit
            entries made by the user
            Hecate in the past 3 days.
        """
        if not user:
            user = ctx.author
        msg = await self.get_action_count(
            ctx, user, after, discord.AuditLogAction.message_pin, "pinned", "messages"
        )
        await ctx.send_or_reply(self.bot.emote_dict["pin"] + msg)

    @auditcount.command(
        aliases=["unpincount", "upc"],
        brief="Count the audit log entries of a user.",
        implemented="2021-05-07 22:34:00.515826",
        updated="2021-05-07 22:34:00.515826",
        examples="""
                {0}bc
                {0}bc Hecate 4d
                {0}bc @Hecate
                {0}bc Hecate#3523 2m
                {0}bc 708584008065351681 5months
                {0}bans
                {0}bans Hecate 4d
                {0}bans @Hecate yesterday
                {0}bans Hecate#3523 2m
                {0}bans 708584008065351681 5 months
                {0}bancount
                {0}bancount Hecate 4d
                {0}bancount @Hecate yesterday
                {0}bancount Hecate#3523 2m
                {0}bancount 708584008065351681 5 months
                """,
    )
    async def unpins(
        self,
        ctx,
        user: converters.DiscordMember = None,
        *,
        after: humantime.PastTime = None,
    ):
        """
        Usage: {0}pins <user> [unit]
        Aliases: {0}unpincount, {0}upc
        Output:
            The number of times a user has
            unpinned a message in the server
            across all time unless a time
            is specified.
        Notes:
            Will default to you if no
            user is specified. Enter a
            past time argument to only
            check entry counts from after
            that day. If you wish to
            select audits by you and
            specify a past time argument,
            you must mention yourself.
        Explanation:
            {0}auditcount unpins Hecate 3d
            This will select all audit
            entries made by the user
            Hecate in the past 3 days.
        """
        if not user:
            user = ctx.author
        msg = await self.get_action_count(
            ctx,
            user,
            after,
            discord.AuditLogAction.message_unpin,
            "unpinned",
            "messages",
        )
        await ctx.send_or_reply(self.bot.emote_dict["pin"] + msg)

    @auditcount.command(
        aliases=["rolecreates"],
        brief="Count the audit log entries of a user.",
        implemented="2021-05-07 22:34:00.515826",
        updated="2021-05-07 22:34:00.515826",
        examples="""
                {0}bc
                {0}bc Hecate 4d
                {0}bc @Hecate
                {0}bc Hecate#3523 2m
                {0}bc 708584008065351681 5months
                {0}bans
                {0}bans Hecate 4d
                {0}bans @Hecate yesterday
                {0}bans Hecate#3523 2m
                {0}bans 708584008065351681 5 months
                {0}bancount
                {0}bancount Hecate 4d
                {0}bancount @Hecate yesterday
                {0}bancount Hecate#3523 2m
                {0}bancount 708584008065351681 5 months
                """,
    )
    async def roleadds(
        self,
        ctx,
        user: converters.DiscordMember = None,
        *,
        after: humantime.PastTime = None,
    ):
        """
        Usage: {0}pins <user> [unit]
        Aliases: {0}rolecreates
        Output:
            The number of times a user has
            created a role in the server
            across all time unless a time
            is specified.
        Notes:
            Will default to you if no
            user is specified. Enter a
            past time argument to only
            check entry counts from after
            that day. If you wish to
            select audits by you and
            specify a past time argument,
            you must mention yourself.
        Explanation:
            {0}auditcount roleadds Hecate 3d
            This will select all audit
            entries made by the user
            Hecate in the past 3 days.
        """
        if not user:
            user = ctx.author
        msg = await self.get_action_count(
            ctx, user, after, discord.AuditLogAction.role_create, "created", "roles"
        )
        await ctx.send_or_reply(self.bot.emote_dict["plus"] + msg)

    @auditcount.command(
        aliases=["rolechanges"],
        brief="Count the audit log entries of a user.",
        implemented="2021-05-07 22:34:00.515826",
        updated="2021-05-07 22:34:00.515826",
        examples="""
                {0}bc
                {0}bc Hecate 4d
                {0}bc @Hecate
                {0}bc Hecate#3523 2m
                {0}bc 708584008065351681 5months
                {0}bans
                {0}bans Hecate 4d
                {0}bans @Hecate yesterday
                {0}bans Hecate#3523 2m
                {0}bans 708584008065351681 5 months
                {0}bancount
                {0}bancount Hecate 4d
                {0}bancount @Hecate yesterday
                {0}bancount Hecate#3523 2m
                {0}bancount 708584008065351681 5 months
                """,
    )
    async def roleupdates(
        self,
        ctx,
        user: converters.DiscordMember = None,
        *,
        after: humantime.PastTime = None,
    ):
        """
        Usage: {0}roleupdates <user> [unit]
        Aliases: {0}rolechanges
        Output:
            The number of times a user has
            updated a role in the server
            across all time unless a time
            is specified.
        Notes:
            Will default to you if no
            user is specified. Enter a
            past time argument to only
            check entry counts from after
            that day. If you wish to
            select audits by you and
            specify a past time argument,
            you must mention yourself.
        Explanation:
            {0}auditcount roleupdates Hecate 3d
            This will select all audit
            entries made by the user
            Hecate in the past 3 days.
        """
        if not user:
            user = ctx.author
        msg = await self.get_action_count(
            ctx, user, after, discord.AuditLogAction.role_update, "updated", "roles"
        )
        await ctx.send_or_reply(self.bot.emote_dict["redo"] + msg)

    @auditcount.command(
        aliases=["roleremoves"],
        brief="Count the audit log entries of a user.",
        implemented="2021-05-07 22:34:00.515826",
        updated="2021-05-07 22:34:00.515826",
        examples="""
                {0}bc
                {0}bc Hecate 4d
                {0}bc @Hecate
                {0}bc Hecate#3523 2m
                {0}bc 708584008065351681 5months
                {0}bans
                {0}bans Hecate 4d
                {0}bans @Hecate yesterday
                {0}bans Hecate#3523 2m
                {0}bans 708584008065351681 5 months
                {0}bancount
                {0}bancount Hecate 4d
                {0}bancount @Hecate yesterday
                {0}bancount Hecate#3523 2m
                {0}bancount 708584008065351681 5 months
                """,
    )
    async def roledeletes(
        self,
        ctx,
        user: converters.DiscordMember = None,
        *,
        after: humantime.PastTime = None,
    ):
        """
        Usage: {0}roledeletes <user> [unit]
        Alias: {0}roleremoves
        Output:
            The number of times a user has
            updated a role in the server
            across all time unless a time
            is specified.
        Notes:
            Will default to you if no
            user is specified. Enter a
            past time argument to only
            check entry counts from after
            that day. If you wish to
            select audits by you and
            specify a past time argument,
            you must mention yourself.
        Explanation:
            {0}auditcount roledeletes Hecate 3d
            This will select all audit
            entries made by the user
            Hecate in the past 3 days.
        """
        if not user:
            user = ctx.author
        msg = await self.get_action_count(
            ctx, user, after, discord.AuditLogAction.role_delete, "deleted", "roles"
        )
        await ctx.send_or_reply(self.bot.emote_dict["minus"] + msg)

    @auditcount.command(
        aliases=["unbancount", "ubc"],
        brief="Count the audit log entries of a user.",
        implemented="2021-05-07 22:34:00.515826",
        updated="2021-05-07 22:34:00.515826",
        examples="""
                {0}bc
                {0}bc Hecate 4d
                {0}bc @Hecate
                {0}bc Hecate#3523 2m
                {0}bc 708584008065351681 5months
                {0}bans
                {0}bans Hecate 4d
                {0}bans @Hecate yesterday
                {0}bans Hecate#3523 2m
                {0}bans 708584008065351681 5 months
                {0}bancount
                {0}bancount Hecate 4d
                {0}bancount @Hecate yesterday
                {0}bancount Hecate#3523 2m
                {0}bancount 708584008065351681 5 months
                """,
    )
    async def unbans(
        self,
        ctx,
        user: converters.DiscordMember = None,
        *,
        after: humantime.PastTime = None,
    ):
        """
        Usage: {0}unbans <user> [after]
        Aliases: {0}unbancount, {0}ubc
        Output:
            The number of times a user has
            unbanned a user in the server
            across all time unless a time
            is specified.
        Notes:
            Will default to you if no
            user is specified. Enter a
            past time argument to only
            check entry counts from after
            that day. If you wish to
            select audits by you and
            specify a past time argument,
            you must mention yourself.
        Explanation:
            {0}auditcount unbans Hecate 3d
            This will select all audit
            entries made by the user
            Hecate in the past 3 days.
        """
        if not user:
            user = ctx.author
        msg = await self.get_action_count(
            ctx, user, after, discord.AuditLogAction.unban, "unbanned", "users"
        )
        await ctx.send_or_reply(self.bot.emote_dict["hammer"] + msg)

    @auditcount.command(
        aliases=["webhookcreates"],
        brief="Count the audit log entries of a user.",
        implemented="2021-05-07 22:34:00.515826",
        updated="2021-05-07 22:34:00.515826",
        examples="""
                {0}bc
                {0}bc Hecate 4d
                {0}bc @Hecate
                {0}bc Hecate#3523 2m
                {0}bc 708584008065351681 5months
                {0}bans
                {0}bans Hecate 4d
                {0}bans @Hecate yesterday
                {0}bans Hecate#3523 2m
                {0}bans 708584008065351681 5 months
                {0}bancount
                {0}bancount Hecate 4d
                {0}bancount @Hecate yesterday
                {0}bancount Hecate#3523 2m
                {0}bancount 708584008065351681 5 months
                """,
    )
    async def webhookadds(
        self,
        ctx,
        user: converters.DiscordMember = None,
        *,
        after: humantime.PastTime = None,
    ):
        """
        Usage: {0}webhookadds <user> [after]
        Aliases: {0}webhookcreates
        Output:
            The number of times a user has
            created a webhook in the server
            across all time unless a time
            is specified.
        Notes:
            Will default to you if no
            user is specified. Enter a
            past time argument to only
            check entry counts from after
            that day. If you wish to
            select audits by you and
            specify a past time argument,
            you must mention yourself.
        Explanation:
            {0}auditcount webhookadds Hecate 3d
            This will select all audit
            entries made by the user
            Hecate in the past 3 days.
        """
        if not user:
            user = ctx.author
        msg = await self.get_action_count(
            ctx,
            user,
            after,
            discord.AuditLogAction.webhook_create,
            "created",
            "webhooks",
        )
        await ctx.send_or_reply(self.bot.emote_dict["plus"] + msg)

    @auditcount.command(
        aliases=["webhookchanges"],
        brief="Count the audit log entries of a user.",
        implemented="2021-05-07 22:34:00.515826",
        updated="2021-05-07 22:34:00.515826",
        examples="""
                {0}bc
                {0}bc Hecate 4d
                {0}bc @Hecate
                {0}bc Hecate#3523 2m
                {0}bc 708584008065351681 5months
                {0}bans
                {0}bans Hecate 4d
                {0}bans @Hecate yesterday
                {0}bans Hecate#3523 2m
                {0}bans 708584008065351681 5 months
                {0}bancount
                {0}bancount Hecate 4d
                {0}bancount @Hecate yesterday
                {0}bancount Hecate#3523 2m
                {0}bancount 708584008065351681 5 months
                """,
    )
    async def webhookupdates(
        self,
        ctx,
        user: converters.DiscordMember = None,
        *,
        after: humantime.PastTime = None,
    ):
        """
        Usage: {0}webhookupdates <user> [after]
        Aliases: {0}webhookchanges
        Output:
            The number of times a user has
            updated a webhook in the server
            across all time unless a time
            is specified.
        Notes:
            Will default to you if no
            user is specified. Enter a
            past time argument to only
            check entry counts from after
            that day. If you wish to
            select audits by you and
            specify a past time argument,
            you must mention yourself.
        Explanation:
            {0}auditcount webhookupdates Hecate 3d
            This will select all audit
            entries made by the user
            Hecate in the past 3 days.
        """
        if not user:
            user = ctx.author
        msg = await self.get_action_count(
            ctx,
            user,
            after,
            discord.AuditLogAction.webhook_update,
            "updated",
            "webhooks",
        )
        await ctx.send_or_reply(self.bot.emote_dict["redo"] + msg)

    @auditcount.command(
        aliases=["webhookremoves"],
        brief="Count the audit log entries of a user.",
        implemented="2021-05-07 22:34:00.515826",
        updated="2021-05-07 22:34:00.515826",
        examples="""
                {0}bc
                {0}bc Hecate 4d
                {0}bc @Hecate
                {0}bc Hecate#3523 2m
                {0}bc 708584008065351681 5months
                {0}bans
                {0}bans Hecate 4d
                {0}bans @Hecate yesterday
                {0}bans Hecate#3523 2m
                {0}bans 708584008065351681 5 months
                {0}bancount
                {0}bancount Hecate 4d
                {0}bancount @Hecate yesterday
                {0}bancount Hecate#3523 2m
                {0}bancount 708584008065351681 5 months
                """,
    )
    async def webhookdeletes(
        self,
        ctx,
        user: converters.DiscordMember = None,
        *,
        after: humantime.PastTime = None,
    ):
        """
        Usage: {0}webhookdeletes <user> [after]
        Aliases: {0}webhookremoves
        Output:
            The number of times a user has
            deleted a webhook in the server
            across all time unless a time
            is specified.
        Notes:
            Will default to you if no
            user is specified. Enter a
            past time argument to only
            check entry counts from after
            that day. If you wish to
            select audits by you and
            specify a past time argument,
            you must mention yourself.
        Explanation:
            {0}auditcount webhookdeletes Hecate 3d
            This will select all audit
            entries made by the user
            Hecate in the past 3 days.
        """
        if not user:
            user = ctx.author
        msg = await self.get_action_count(
            ctx,
            user,
            after,
            discord.AuditLogAction.webhook_delete,
            "deleted",
            "webhooks",
        )
        await ctx.send_or_reply(self.bot.emote_dict["minus"] + msg)

    async def get_action_count(self, ctx, user, after, action, string1, string2):
        """
        Helper function to get audit counts
        from a user object and an action
        """
        await ctx.trigger_typing()
        entries = await ctx.guild.audit_logs(
            limit=None, user=user, action=action
        ).flatten()
        if after:
            valid = []
            for entry in entries:
                if entry.created_at > after.dt:
                    valid.append(entry)
            msg = f" User `{user}` has {string1} {len(valid)} {string2 if len(entries) != 1 else string2[:-1]} since **{utils.timeago(after.dt)}.**"
        else:
            msg = f" User `{user}` has {string1} {len(entries)} {string2 if len(entries) != 1 else string2[:-1]}."
        return msg

    @decorators.command(brief="Snipe a deleted message.", aliases=["retrieve"])
    @commands.guild_only()
    @checks.bot_has_perms(embed_links=True)
    @checks.has_perms(manage_messages=True)
    async def snipe(self, ctx, *, member: converters.DiscordMember = None):
        """
        Usage: {0}snipe [user]
        Alias: {0}retrieve
        Output: Fetches a deleted message
        Notes:
            Will fetch a messages sent by a specific user if specified
        """
        if member is None:
            query = """
                    SELECT author_id, message_id, content, timestamp
                    FROM messages
                    WHERE channel_id = $1
                    AND deleted = True
                    ORDER BY unix DESC;
                    """
            result = await self.bot.cxn.fetchrow(query, ctx.channel.id)
        else:
            query = """
                    SELECT author_id, message_id, content, timestamp
                    FROM messages
                    WHERE channel_id = $1
                    AND author_id = $2
                    AND deleted = True
                    ORDER BY unix DESC;
                    """
            result = await self.bot.cxn.fetchrow(query, ctx.channel.id, member.id)

        if not result:
            return await ctx.fail(f"There is nothing to snipe.")

        author = result["author_id"]
        message_id = result["message_id"]
        content = result["content"]
        timestamp = result["timestamp"]

        author = self.bot.get_user(author)
        if not author:
            author = await self.bot.fetch_user(author)

        if str(content).startswith("```"):
            content = f"**__Message Content__**\n {str(content)}"
        else:
            content = f"**__Message Content__**\n ```fix\n{str(content)}```"

        embed = discord.Embed(
            description=f"**Author:**  {author.mention}, **ID:** `{author.id}`\n"
            f"**Channel:** {ctx.channel.mention} **ID:** `{ctx.channel.id}`\n"
            f"**Server:** `{ctx.guild.name}` **ID:** `{ctx.guild.id}`\n"
            f"**Sent at:** `{timestamp}`\n\n"
            f"{content}",
            color=self.bot.constants.embed,
            timestamp=datetime.utcnow(),
        )
        embed.set_author(
            name="Deleted Message Retrieved",
            icon_url=DELETED_MESSAGE,
        )
        embed.set_footer(text=f"Message ID: {message_id}")
        await ctx.send_or_reply(embed=embed)

    @decorators.command(
        brief="Snipe an edited message.",
        aliases=["snipeedit", "retrieveedit", "editretrieve"],
    )
    @commands.guild_only()
    @checks.bot_has_perms(embed_links=True)
    @checks.has_perms(manage_messages=True)
    async def editsnipe(self, ctx, *, member: converters.DiscordMember = None):
        """
        Usage: {0}editsnipe [user]
        Alias: {0}editretrieve, {0}snipeedit, {0}retriveedit
        Output: Fetches an edited message
        Notes:
            Will fetch a messages sent by a specific user if specified
        """
        if member is None:
            query = """
                    SELECT author_id, message_id, content, timestamp
                    FROM messages
                    WHERE channel_id = $1
                    AND edited = True
                    ORDER BY unix DESC;
                    """
            result = await self.bot.cxn.fetchrow(query, ctx.channel.id)
        else:
            query = """
                    SELECT author_id, message_id, content, timestamp
                    FROM messages
                    WHERE channel_id = $1
                    AND author_id = $2
                    AND edited = True
                    ORDER BY unix DESC;
                    """
            result = await self.bot.cxn.fetchrow(query, ctx.channel.id, member.id)

        if not result:
            return await ctx.fail("There are no edits to snipe.")

        author = result["author_id"]
        message_id = result["message_id"]
        content = result["content"]
        timestamp = result["timestamp"]

        author = self.bot.get_user(author)
        if not author:
            author = await self.bot.fetch_user(author)

        if str(content).startswith("```"):
            content = f"**__Previous Message Content__**\n {str(content)}"
        else:
            content = f"**__Previous Message Content__**\n ```fix\n{str(content)}```"

        embed = discord.Embed(
            description=f"**Author:**  {author.mention}, **ID:** `{author.id}`\n"
            f"**Channel:** {ctx.channel.mention} **ID:** `{ctx.channel.id}`\n"
            f"**Server:** `{ctx.guild.name}` **ID:** `{ctx.guild.id}`\n"
            f"**Sent at:** `{timestamp}`\n\n"
            f"{content}",
            color=self.bot.constants.embed,
            timestamp=datetime.utcnow(),
        )
        embed.set_author(
            name="Edited Message Retrieved",
            icon_url=UPDATED_MESSAGE,
        )
        embed.set_footer(text=f"Message ID: {message_id}")
        await ctx.send_or_reply(embed=embed)
