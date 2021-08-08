import io
import re
import json
import codecs
import discord

from collections import defaultdict, Counter
from discord.ext import commands, menus, tasks

from utilities import utils
from utilities import checks
from utilities import converters
from utilities import decorators
from utilities import exceptions
from utilities import pagination


CREATED_MESSAGE = "https://cdn.discordapp.com/attachments/846597178918436885/846841649542725632/messagecreate.png"
UPDATED_MESSAGE = "https://cdn.discordapp.com/attachments/846597178918436885/846841668639653939/messageupdate.png"
DELETED_MESSAGE = "https://cdn.discordapp.com/attachments/846597178918436885/846841722994163722/messagedelete.png"

CDN_POOP = "https://cdn.discordapp.com/attachments/846597178918436885/873793100613582878/poop.png"

def setup(bot):
    bot.add_cog(Logging(bot))


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
            "avatars",
            "channels",
            "emojis",
            "invites",
            "joins",
            "leaves",
            "messages",
            "moderation",
            "nicknames",
            "usernames",
            "roles",
            "server",
            "voice",
        ]  # Helper list with all our logging types.

        # self.dispatch_webhooks.add_exception_type(discord.NotFound)
        self.dispatch_webhooks.start()  # Start the task loop

        self.map = {
            True: bot.emote_dict["pass"],
            False: bot.emote_dict["fail"],
        }  # Map for determining the emote.

    def cog_unload(self):  # Stop the task loop
        self.dispatch_webhooks.stop()

    async def load_settings(self):
        query = """
                SELECT 
                logs.server_id,
                (SELECT ROW_TO_JSON(_) FROM (SELECT
                    logs.avatars,
                    logs.channels,
                    logs.emojis,
                    logs.invites,
                    logs.joins,
                    logs.leaves,
                    logs.messages,
                    logs.moderation,
                    logs.nicknames,
                    logs.usernames,
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
        try:  # Here we get a partial webhook from the ID and Token
            webhook = discord.Webhook.partial(
                id=webhook_id,
                token=webhook_token,
                session=self.bot.session,
            )
        except Exception:  # Failed so do nothing
            return
        else:  # Got the webhook
            return webhook

    def get_webhook(self, guild, event=None):
        """
        Helper function to get the webhook for a guild.
        Also checks if an event is being logged.
        """
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
                    try:
                        await webhook.send(
                            embeds=embeds,
                            files=files,
                            username=f"{self.bot.user.name}-logger",
                            avatar_url=self.bot.user.avatar.url,
                        )
                    except discord.NotFound:  # Raised when users manually delete the webhook.
                        pass
                    except discord.HTTPException:  # Embed too large
                        pass  # TODO truncate instead of ignoring size errors.
                    except Exception as e:
                        self.bot.dispatch(
                            "error", "logging_error", tb=utils.traceback_maker(e)
                        )
                    embeds.clear()
                    files.clear()
                    self.tasks[webhook] = objects[10:]

    @dispatch_webhooks.error  # For unhandled errors
    async def logging_error(self, exc):
        self.bot.dispatch("error", "logging_error", tb=utils.traceback_maker(exc))

    @decorators.group(
        name="log",
        brief="Enable specific logging events.",
        implemented="2021-03-17 07:09:57.666073",
        updated="2021-06-08 17:18:43.698120",
        invoke_without_command=True,
        case_insensitive=True,
    )
    @checks.guild_only()
    @checks.bot_has_guild_perms(manage_webhooks=True, view_audit_log=True)
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
            avatars
            channels
            emojis
            invites
            joins
            leaves
            messages
            moderation
            nicknames
            usernames
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
        hidden=True,
    )
    @checks.cooldown()
    @checks.bot_has_guild_perms(manage_webhooks=True, view_audit_log=True)
    @checks.bot_has_perms(embed_links=True)
    @checks.has_perms(manage_guild=True)
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
        hidden=True,
    )
    @checks.cooldown()
    @checks.bot_has_guild_perms(manage_webhooks=True, view_audit_log=True)
    @checks.bot_has_perms(embed_links=True)
    @checks.has_perms(manage_guild=True)
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
            raise exceptions.WebhookLimit(channel)

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
        brief="Disable specific logging events.",
        implemented="2021-03-17 07:09:57.666073",
        updated="2021-06-08 17:18:43.698120",
    )
    @checks.guild_only()
    @checks.cooldown(2, 30, bucket=commands.BucketType.guild)
    @checks.bot_has_guild_perms(manage_webhooks=True, view_audit_log=True)
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

            args = [False] * 13
            query = """
                    INSERT INTO logs
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
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
    @checks.guild_only()
    @checks.cooldown(2, 30, bucket=commands.BucketType.guild)
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
        brief="Remove the server logging channel.",
        aliases=["unlogserver"],
    )
    @checks.guild_only()
    @checks.cooldown(2, 30, bucket=commands.BucketType.guild)
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
            timestamp=discord.utils.utcnow(),
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

        if before.icon != after.icon:
            if after.icon:
                embed = discord.Embed(
                    description=f"**Author:**  `{str(audit.user)}`\n" "**New icon below**",
                    color=self.bot.constants.embed,
                )

                embed.set_author(
                    name="Server Icon Updated",
                    icon_url=UPDATED_MESSAGE,
                )

                embed.set_image(url=after.icon.url)
                await self.send_webhook(webhook, embed=embed)
            else:
                embed = discord.Embed(
                    description=f"**Author:**  `{str(audit.user)}`\n",
                    color=self.bot.constants.embed,
                )

                embed.set_author(
                    name="Server Icon Removed",
                    icon_url=DELETED_MESSAGE,
                )

                embed.set_image(url=CDN_POOP)
                await self.send_webhook(webhook, embed=embed)

        if before.banner != after.banner:
            embed = discord.Embed(
                description=f"**Author:**  `{str(audit.user)}`\n"
                "**New banner below**",
                color=self.bot.constants.embed,
            )

            embed.set_author(
                name="Server Banner Updated",
                icon_url=UPDATED_MESSAGE,
            )

            embed.set_image(url=after.banner.url)
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
            timestamp=discord.utils.utcnow(),
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
        embed.set_footer(text=f"Emoji ID: {emoji.id}")

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
            timestamp=discord.utils.utcnow(),
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
            timestamp=discord.utils.utcnow(),
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
                timestamp=discord.utils.utcnow(),
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
                timestamp=discord.utils.utcnow(),
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
                    timestamp=discord.utils.utcnow(),
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
                    timestamp=discord.utils.utcnow(),
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
                    timestamp=discord.utils.utcnow(),
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
                timestamp=discord.utils.utcnow(),
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
            f"**Targets:** `{', '.join(str(t) for t in targets)}`\n\n"
            f"**__Message Content__**\n ```fix\n{ctx.message.clean_content}```\n"
            f"**[Jump to action](https://discord.com/channels/{ctx.guild.id}/{ctx.channel.id}/{ctx.message.id})**",
            color=self.bot.constants.embed,
            timestamp=discord.utils.utcnow(),
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
            timestamp=discord.utils.utcnow(),
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
            timestamp=discord.utils.utcnow(),
        )
        embed.set_author(name=f"User Left")
        embed.set_footer(text=f"User ID: {member.id}")
        await self.send_webhook(webhook, embed=embed)

    @commands.Cog.listener()
    @decorators.wait_until_ready()
    @decorators.event_check(lambda s, b, a: not a.bot)
    async def on_member_update(self, before, after):
        if before.display_name != after.display_name:
            webhook = self.get_webhook(after.guild, "nicknames")
            if webhook:
                embed = discord.Embed(
                    description=f"**User:** {after.mention} **Name:** `{after}`\n"
                    f"**Old Nickname:** `{before.display_name}`\n"
                    f"**New Nickname:** `{after.display_name}`\n",
                    colour=self.bot.constants.embed,
                    timestamp=discord.utils.utcnow(),
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
                    timestamp=discord.utils.utcnow(),
                )
                embed.set_author(name=f"Role Updates")
                embed.set_footer(text=f"User ID: {after.id}")

                await self.send_webhook(webhook, embed=embed)

    @commands.Cog.listener()
    @decorators.wait_until_ready()
    @decorators.event_check(lambda s, b, a: not a.bot)
    async def on_user_update(self, before, after):
        for guild in after.mutual_guilds:

            if before.name != after.name:

                webhook = self.get_webhook(guild, "usernames")
                if not webhook:
                    continue

                embed = discord.Embed(
                    description=f"**User:** {after.mention} **Name:** `{after}`\n"
                    f"**Old Username:** `{before.name}`\n"
                    f"**New Username:** `{after.name}`\n",
                    colour=self.bot.constants.embed,
                    timestamp=discord.utils.utcnow(),
                )
                embed.set_author(name=f"Username Change")
                embed.set_footer(text=f"User ID: {after.id}")

                await self.send_webhook(webhook, embed=embed)

            elif before.discriminator != after.discriminator:

                webhook = self.get_webhook(guild, "usernames")
                if not webhook:
                    continue

                embed = discord.Embed(
                    description=f"**User:** {after.mention} **Name:** `{after}`\n"
                    f"**Old Discriminator:** `{before.discriminator}`\n"
                    f"**New Discriminator:** `{after.discriminator}`\n",
                    colour=self.bot.constants.embed,
                    timestamp=discord.utils.utcnow(),
                )
                embed.set_author(name=f"Discriminator Change")
                embed.set_footer(text=f"User ID: {after.id}")

                await self.send_webhook(webhook, embed=embed)

            elif before.avatar.url != after.avatar.url:

                webhook = self.get_webhook(guild, "avatars")
                if not webhook:
                    continue

                embed = discord.Embed(
                    description=f"**User:** {after.mention} **Name:** `{after}`\n"
                    "New image below",
                    colour=self.bot.constants.embed,
                    timestamp=discord.utils.utcnow(),
                )

                embed.set_image(url=after.avatar.url)
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
                timestamp=discord.utils.utcnow(),
            )
            embed.set_author(name=f"User Joined Voice Channel")
            embed.set_footer(text=f"User ID: {member.id}")

            await self.send_webhook(webhook, embed=embed)

        elif before.channel and not after.channel:
            embed = discord.Embed(
                description=f"**User:** {member.mention} **Name:** `{member}`\n**Channel:** {before.channel.mention} **ID:** `{before.channel.id}`\n",
                colour=self.bot.constants.embed,
                timestamp=discord.utils.utcnow(),
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
                    timestamp=discord.utils.utcnow(),
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
            timestamp=discord.utils.utcnow(),
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
            timestamp=discord.utils.utcnow(),
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

        message = messages[0]
        messages = [m for m in messages if not m.author.bot]
        if not messages:
            return

        if len(messages) == 1:
            self.bot.dispatch("message_delete", messages[0])
            return

        webhook = self.get_webhook(message.guild, "messages")
        if not webhook:
            return

        msg = f"{len(messages):,} bulk deleted messages in #{message.channel.name} (ID: {message.channel.id})\n"
        for m in messages:
            msg += "\nMessage: " + m.clean_content
            msg += "\nSent-By: " + f"{str(m.author)} ID: {m.author.id}"
            msg += "\nSent-At: " + m.created_at.strftime("%Y-%m-%d %-I.%M %p UTC")
            msg += "\n"

        data = io.BytesIO(msg[:-2].encode("utf-8"))

        date_fmt = discord.utils.utcnow().__format__("%Y-%m-%d")
        file = discord.File(
            data,
            filename=f"Bulk-Deleted-Messages-{date_fmt}.yml",
        )
        await self.send_webhook(webhook, file=file)

    ####################
    ## Other Commands ##
    ####################

    @decorators.command(brief="Snipe a deleted message.", aliases=["retrieve"])
    @checks.guild_only()
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
            timestamp=discord.utils.utcnow(),
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
    @checks.guild_only()
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
            timestamp=discord.utils.utcnow(),
        )
        embed.set_author(
            name="Edited Message Retrieved",
            icon_url=UPDATED_MESSAGE,
        )
        embed.set_footer(text=f"Message ID: {message_id}")
        await ctx.send_or_reply(embed=embed)

    # command idea from Alex Flipnote's discord_bot.py bot
    # https://github.com/AlexFlipnote/discord_bot.py
    # Subcommands added & converted to use a paginator.

    @decorators.group(
        aliases=["search"],
        brief="Find any user using a search.",
        implemented="2021-03-14 18:18:20.175991",
        updated="2021-05-07 05:13:20.340824",
    )
    @commands.guild_only()
    @checks.has_perms(manage_messages=True)
    @checks.cooldown()
    async def find(self, ctx):
        """
        Usage: {0}find <option> <search>
        Alias: {0}search
        Output: Users matching your search.
        Examples:
            {0}find name Hecate
            {0}find id 708584008065351681
        Options:
            duplicates
            hardmention
            hash       (Ex: 3523)
            nickname   (Ex: Hecate)
            playing    (Ex: Visual Studio Code)
            snowflake  (Ex: 708584008065351681)
            username   (Ex: Hecate)
        """
        if ctx.invoked_subcommand is None:
            return await ctx.usage("<option> <search>")

    @find.command(
        name="playing",
        aliases=["status", "activity"],
        brief="Search for users by game.",
    )
    async def find_playing(self, ctx, *, search: str):
        """
        Usage: {0}find playing <search>
        Alias: {0}find status, {0}find activity
        Output:
            All the users currently playing
            the specified activity
        """
        loop = []
        for i in ctx.guild.members:
            if i.activities and (not i.bot):
                for g in i.activities:
                    if g.name and (search.lower() in g.name.lower()):
                        loop.append(f"{i} | {type(g).__name__}: {g.name} ({i.id})")

        if not loop:
            return await ctx.fail(f"**No results.**")
        stuff = "\r\n".join(
            [f"[{str(num).zfill(2)}] {data}" for num, data in enumerate(loop, start=1)]
        )
        await ctx.send_or_reply(
            f"Found **{len(loop)}** on your search for **{search}**"
        )
        p = pagination.MainMenu(
            pagination.TextPageSource(text=str(stuff), prefix="```ini\n", max_size=800)
        )
        try:
            await p.start(ctx)
        except menus.MenuError as e:
            await ctx.send_or_reply(e)

    @find.command(
        name="username", aliases=["name", "user"], brief="Search for users by username."
    )
    async def find_name(self, ctx, *, search: str):
        """
        Usage: {0}find username <search>
        Aliases:
            {0}find name
            {0}find user
        Output:
            A pagination session with all user's
            usernames that match your search
        """
        loop = [
            f"{i} ({i.id})"
            for i in ctx.guild.members
            if search.lower() in i.name.lower() and not i.bot
        ]
        if not loop:
            return await ctx.fail(f"**No results.**")
        stuff = "\r\n".join(
            [f"[{str(num).zfill(2)}] {data}" for num, data in enumerate(loop, start=1)]
        )
        await ctx.send_or_reply(
            f"Found **{len(loop)}** on your search for **{search}**"
        )
        p = pagination.MainMenu(
            pagination.TextPageSource(text=str(stuff), prefix="```ini\n", max_size=800)
        )
        try:
            await p.start(ctx)
        except menus.MenuError as e:
            await ctx.send_or_reply(e)

    @find.command(
        name="nicknames",
        aliases=["nick", "nicks", "nickname"],
        brief="Search for users by nickname.",
    )
    async def find_nickname(self, ctx, *, search: str):
        """
        Usage: {0}find nicknames <search>
        Aliases:
            {0}find nicks
            {0}find nick
            {0}find nickname
        Output:
            A pagination session with all user's
            nicknames that match your search
        """
        loop = [
            f"{i.nick} | {i} ({i.id})"
            for i in ctx.guild.members
            if i.nick
            if (search.lower() in i.nick.lower()) and not i.bot
        ]
        if not loop:
            return await ctx.fail(f"**No results.**")
        stuff = "\r\n".join(
            [f"[{str(num).zfill(2)}] {data}" for num, data in enumerate(loop, start=1)]
        )
        await ctx.send_or_reply(
            f"Found **{len(loop)}** on your search for **{search}**"
        )
        p = pagination.MainMenu(
            pagination.TextPageSource(text=str(stuff), prefix="```ini\n", max_size=800)
        )
        try:
            await p.start(ctx)
        except menus.MenuError as e:
            await ctx.send_or_reply(e)

    @find.command(name="id", aliases=["snowflake"], brief="Search for users by id.")
    async def find_id(self, ctx, *, search: int):
        """
        Usage: {0}find id <search>
        Alias: {0}find snowflake
        Output:
            Starts a pagination session
            showing all users who's IDs
            contain your search.
        """
        loop = [
            f"{i} | {i} ({i.id})"
            for i in ctx.guild.members
            if (str(search) in str(i.id)) and not i.bot
        ]
        if not loop:
            return await ctx.fail(f"**No results.**")
        stuff = "\r\n".join(
            [f"[{str(num).zfill(2)}] {data}" for num, data in enumerate(loop, start=1)]
        )
        await ctx.send_or_reply(
            f"Found **{len(loop)}** on your search for **{search}**"
        )
        p = pagination.MainMenu(
            pagination.TextPageSource(text=str(stuff), prefix="```ini\n", max_size=800)
        )
        try:
            await p.start(ctx)
        except menus.MenuError as e:
            await ctx.send_or_reply(e)

    @find.command(
        name="hash",
        aliases=["discriminator", "discrim"],
        brief="Search for users by discriminator.",
    )
    async def find_discrim(self, ctx, *, search: str):
        """
        Usage: {0}find hash <search>
        Aliases:
            {0}find discrim
            {0}find discriminator
        Output:
            Starts a pagination session
            showing all users who's hash
            (discriminator) contain your search
        """
        if not len(search) == 4 or not re.compile("^[0-9]*$").search(search):
            return await ctx.send_or_reply(
                content="You must provide exactly 4 digits",
            )

        loop = [f"{i} ({i.id})" for i in ctx.guild.members if search == i.discriminator]
        if not loop:
            return await ctx.fail(f"**No results.**")
        stuff = "\r\n".join(
            [f"[{str(num).zfill(2)}] {data}" for num, data in enumerate(loop, start=1)]
        )
        await ctx.send_or_reply(
            f"Found **{len(loop)}** on your search for **{search}**"
        )
        p = pagination.MainMenu(
            pagination.TextPageSource(text=str(stuff), prefix="```ini\n", max_size=1250)
        )
        try:
            await p.start(ctx)
        except menus.MenuError as e:
            await ctx.send_or_reply(e)

    @find.command(
        aliases=["dups"],
        name="duplicates",
        brief="Find users with identical names.",
    )
    async def find_duplicates(self, ctx):
        """
        Usage: {0}find duplicates
        Alias: {0}find dups
        Output:
            Starts a pagination session
            showing all users who's nicknames
            are not unique on the server
        """
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

        if not loop:
            return await ctx.fail(f"**No results.**")
        stuff = "\r\n".join(
            [f"[{str(num).zfill(2)}] {data}" for num, data in enumerate(loop, start=1)]
        )
        await ctx.send_or_reply(
            f"Found **{len(loop)}** on your search for **duplicates**"
        )
        p = pagination.MainMenu(
            pagination.TextPageSource(text=str(stuff), prefix="```ini\n", max_size=800)
        )
        try:
            await p.start(ctx)
        except menus.MenuError as e:
            await ctx.send_or_reply(e)

    def _is_hard_to_mention(self, name):
        """Determine if a name is hard to mention."""
        codecs.register_error("newreplace", lambda x: (b" " * (x.end - x.start), x.end))

        encoderes, chars = codecs.getwriter("ascii").encode(name, "newreplace")

        return re.search(br"[^ ][^ ]+", encoderes) is None

    @find.command(
        name="hard",
        aliases=["weird", "special", "hardmentions", "hardmention"],
        brief="Find users with hard to mention names.",
    )
    async def find_hard(self, ctx, username: str = None):
        """
        Usage: {0}find hard [--username]
        Alias:
            {0}find weird
            {0}find special
            {0}find hardmention
        Output:
            Starts a pagination session showing
            all users who use special characters
            that make their name hard to mention
        Notes:
            Specify a username kwarg, as in
            {0}find hardmention --username
            to search for hard to mention
            usernames instead of nicknames.
        """
        if str(username).lower() in ["--username", " -u", "-username", "--u"]:
            loop = [
                member
                for member in ctx.message.guild.members
                if self._is_hard_to_mention(str(member.name))
            ]
        else:
            loop = [
                member
                for member in ctx.message.guild.members
                if self._is_hard_to_mention(member.display_name)
            ]
        if not loop:
            return await ctx.fail(f"**No results.**")
        stuff = "\r\n".join(
            [f"[{str(num).zfill(2)}] {data}" for num, data in enumerate(loop, start=1)]
        )
        await ctx.send_or_reply(
            f"Found **{len(loop)}** on your search for **hard mentions**"
        )
        p = pagination.MainMenu(
            pagination.TextPageSource(text=str(stuff), prefix="```ini\n", max_size=800)
        )
        try:
            await p.start(ctx)
        except menus.MenuError as e:
            await ctx.send_or_reply(e)
