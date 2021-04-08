import discord
import io
import re

from discord.ext import commands
from datetime import datetime

from utilities import permissions


def setup(bot):
    bot.add_cog(Logging(bot))


class Logging(commands.Cog):

    """
    Log your server events
    """

    def __init__(self, bot):
        self.bot = bot

        self.emote_dict = bot.emote_dict
        self.uregex = re.compile(
            r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*(),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+"
        )

        self.current_streamers = list()

    ##############################
    ## Aiohttp Helper Functions ##
    ##############################

    async def query(self, url, method="get", res_method="text", *args, **kwargs):
        async with getattr(self.bot.session, method.lower())(
            url, *args, **kwargs
        ) as res:
            return await getattr(res, res_method)()

    async def get(self, url, *args, **kwargs):
        return await self.query(url, "get", *args, **kwargs)

    async def post(self, url, *args, **kwargs):
        return await self.query(url, "post", *args, **kwargs)

    #####################
    ## Event Listeners ##
    #####################

    async def check(self, snowflake, event):
        try:
            logchannel = self.bot.server_settings[snowflake]["logging"]["logchannel"]
        except KeyError:
            return
        if logchannel is None:
            return
        indicator = self.bot.server_settings[snowflake]["logging"][event]
        if indicator is not True:
            return
        return True

    async def get_webhook(self, guild):
        try:
            logchannel_id = self.bot.server_settings[guild.id]["logging"]["logchannel"]
            webhook_id = self.bot.server_settings[guild.id]["logging"]["webhook_id"]
        except KeyError:
            return
        if logchannel_id is None or webhook_id is None:
            return
        if not guild.me.guild_permissions.manage_webhooks:
            return
        try:
            logchannel = self.bot.get_channel(logchannel_id)
        except Exception:
            return
        try:
            logging_webhook = await self.bot.fetch_webhook(webhook_id)
        except Exception:
            return
        if logging_webhook.guild.id != logchannel.guild.id:
            return

        if logging_webhook:
            return logging_webhook
        # Should never get here but idk.
        return

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel):
        if not self.bot.bot_ready:
            return
        if not await self.check(snowflake=channel.guild.id, event="channel_updates"):
            return

        webhook = await self.get_webhook(guild=channel.guild)
        if webhook is None:
            return

        embed = discord.Embed(
            description=f"**Channel:** {channel.mention} **Name:** `{channel.name}`\n"
            f"**Server:** `{channel.guild.name}` **ID:** `{channel.guild.id},`\n\n",
            color=self.bot.constants.embed,
            timestamp=datetime.utcnow(),
        )
        embed.set_author(
            name="Channel Created",
            icon_url="https://cdn.discordapp.com/emojis/810659118045331517.png?v=1",
        )
        embed.set_footer(text=f"Channel ID: {channel.id}")
        await webhook.execute(embed=embed, username=self.bot.user.name)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        if not self.bot.bot_ready:
            return

        if not await self.check(snowflake=channel.guild.id, event="channel_updates"):
            return

        webhook = await self.get_webhook(guild=channel.guild)
        if webhook is None:
            return

        embed = discord.Embed(
            description=f"**Channel:** {channel.mention} **Name:** `{channel.name}`\n"
            f"**Server:** `{channel.guild.name}` **ID:** `{channel.guild.id},`\n\n",
            color=self.bot.constants.embed,
            timestamp=datetime.utcnow(),
        )
        embed.set_author(
            name="Channel Deleted",
            icon_url="https://cdn.discordapp.com/emojis/810659118045331517.png?v=1",
        )
        embed.set_footer(text=f"Channel ID: {channel.id}")
        await webhook.execute(embed=embed, username=self.bot.user.name)

    @commands.Cog.listener()
    async def on_guild_channel_update(self, before, after):
        if not self.bot.bot_ready:
            return

        if not await self.check(snowflake=after.guild.id, event="channel_updates"):
            return

        webhook = await self.get_webhook(guild=after.guild)
        if webhook is None:
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
            await webhook.execute(embed=embed, username=self.bot.user.name)

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
            await webhook.execute(embed=embed, username=self.bot.user.name)

        elif before.topic != after.topic:
            if not isinstance(before, discord.TextChannel):
                return
            embed = discord.Embed(
                description=f"**Channel:** {after.mention} **Name:** `{after}`\n"
                f"**Old Topic:** `{before.topic}`\n"
                f"**New Topic:** `{after.topic}`\n",
                colour=self.bot.constants.embed,
                timestamp=datetime.utcnow(),
            )
            embed.set_author(name=f"Channel Update")
            embed.set_footer(text=f"Channel ID: {after.id}")
            await webhook.execute(embed=embed, username=self.bot.user.name)

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
            await webhook.execute(embed=embed, username=self.bot.user.name)

    '''
    @commands.Cog.listener()
    async def on_user_update(self, before, after):
        # TODO Fix up this listener. Possibly remove altogether.

        if before.name != after.name:
            to_send = []
            for guild in self.bot.guilds:

                to_log_or_not_to_log = await self.bot.cxn.fetchrow("""
                SELECT name_updates FROM logging WHERE server_id = $1
                """, guild.id)
                if to_log_or_not_to_log[0] != True: return

                for member in guild.members:
                    if member.id != before.id:
                        continue
                    to_send.append(guild.id)
            if to_send:
                for i in to_send:
                    webhook_id = await self.bot.cxn.fetchrow("SELECT logging_webhook_id FROM logging WHERE server_id = $1", i) or None
                    if webhook_id is None or "None" in str(webhook_id):
                        continue
                    webhook_id = int(webhook_id[0])
                    webhook = await self.bot.fetch_webhook(webhook_id)
                embed = discord.Embed(
                              description=f"**User:** {after.mention} **Name:** `{after}`\n"
                                          f"**Old Username:** `{before.name}`\n"
                                          f"**New Username:** `{after.name}`\n",
                              colour=self.bot.constants.embed,
                              timestamp=datetime.utcnow())
                embed.set_author(name=f"Username Change")
                embed.set_footer(text=f"User ID: {after.id}")

                await webhook.execute(embed=embed, username=self.bot.user.name)

        if before.discriminator != after.discriminator:
            to_send = []
            for guild in self.bot.guilds:

                to_log_or_not_to_log = await self.bot.cxn.fetchrow("""
                SELECT name_updates FROM logging WHERE server_id = $1
                """, guild.id)
                if to_log_or_not_to_log[0] is not True: return

                for member in guild.members:
                    if member.id != before.id:
                        continue
                    to_send.append(guild.id)
            if to_send:
                for i in to_send:
                    webhook_id = await self.bot.cxn.fetchrow("SELECT logging_webhook_id FROM logging WHERE server_id = $1", i) or None
                    if webhook_id is None or "None" in str(webhook_id):
                        continue

                    webhook_id = int(webhook_id[0])
                    webhook = await self.bot.fetch_webhook(webhook_id)
                embed = discord.Embed(
                              description=f"**User:** {after.mention} **Name:** `{after}`\n"
                                          f"**Old Discriminator:** `{before.discriminator}`\n"
                                          f"**New Discriminator:** `{after.discriminator}`\n",
                              colour=self.bot.constants.embed,
                              timestamp=datetime.utcnow())
                embed.set_author(name=f"Discriminator Change")
                embed.set_footer(text=f"User ID: {after.id}")

                await webhook.execute(embed=embed, username=self.bot.user.name)

        if before.avatar_url != after.avatar_url:
            to_send = []
            for guild in self.bot.guilds:

                to_log_or_not_to_log = await self.bot.cxn.fetchrow("""
                SELECT avatar_changes FROM logging WHERE server_id = $1
                """, guild.id)
                if to_log_or_not_to_log[0] is not True: return

                for member in guild.members:
                    if member.id != before.id:
                        continue
                    to_send.append(guild.id)
            if to_send:
                for i in to_send:
                    webhook_id = await self.bot.cxn.fetchrow("SELECT logging_webhook_id FROM logging WHERE server_id = $1", i) or None
                    if webhook_id is None or "None" in str(webhook_id):
                        webhook = False
                        continue
                    webhook = True
                    webhook_id = int(webhook_id[0])
                    webhook = await self.bot.fetch_webhook(webhook_id)
                if webhook is True:
                    embed = discord.Embed(
                                  description=f"**User:** {after.mention} **Name:** `{after}`\n"
                                              "New image below, old image to the right.",
                                  colour=self.bot.constants.embed,
                                  timestamp=datetime.utcnow())

                    embed.set_thumbnail(url=before.avatar_url)
                    embed.set_image(url=after.avatar_url)
                    embed.set_author(name=f"Avatar Change")
                    embed.set_footer(text=f"User ID: {after.id}")
                    await webhook.execute(embed=embed, username=self.bot.user.name)
    '''

    @commands.Cog.listener()
    async def on_member_unban(self, guild, user):
        if not self.bot.bot_ready:
            return

        if user.bot:
            return

        if not await self.check(snowflake=guild.id, event="bans"):
            return

        webhook = await self.get_webhook(guild=guild)
        if webhook is None:
            return

        embed = discord.Embed(
            description=f"**User:** {user.mention} **Name:** `{user}`\n",
            colour=self.bot.constants.embed,
            timestamp=datetime.utcnow(),
        )
        embed.set_author(name=f"User Unbanned")
        embed.set_footer(text=f"User ID: {user.id}")
        await webhook.execute(embed=embed, username=self.bot.user.name)

    @commands.Cog.listener()
    async def on_member_ban(self, guild, user):
        if not self.bot.bot_ready:
            return

        if user.bot:
            return

        if not await self.check(snowflake=guild.id, event="bans"):
            return

        webhook = await self.get_webhook(guild=guild)
        if webhook is None:
            return

        embed = discord.Embed(
            description=f"**User:** {user.mention} **Name:** `{user}`\n",
            colour=self.bot.constants.embed,
            timestamp=datetime.utcnow(),
        )
        embed.set_author(name=f"User Banned")
        embed.set_footer(text=f"User ID: {user.id}")
        await webhook.execute(embed=embed, username=self.bot.user.name)

    @commands.Cog.listener()
    async def on_member_join(self, member):
        if not self.bot.bot_ready:
            return

        if not await self.check(snowflake=member.guild.id, event="joins"):
            return

        webhook = await self.get_webhook(guild=member.guild)
        if webhook is None:
            return

        embed = discord.Embed(
            description=f"**User:** {member.mention} **Name:** `{member}`\n",
            colour=self.bot.constants.embed,
            timestamp=datetime.utcnow(),
        )
        embed.set_author(name=f"User Joined")
        embed.set_footer(text=f"User ID: {member.id}")
        await webhook.execute(embed=embed, username=self.bot.user.name)

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        if not self.bot.bot_ready:
            return

        if not await self.check(snowflake=member.guild.id, event="leaves"):
            return

        webhook = await self.get_webhook(guild=member.guild)
        if webhook is None:
            return

        embed = discord.Embed(
            description=f"**User:** {member.mention} **Name:** `{member}`\n",
            colour=self.bot.constants.embed,
            timestamp=datetime.utcnow(),
        )
        embed.set_author(name=f"User Left")
        embed.set_footer(text=f"User ID: {member.id}")
        await webhook.execute(embed=embed, username=self.bot.user.name)

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        if not self.bot.bot_ready:
            return

        if after.bot:
            return

        webhook = await self.get_webhook(guild=after.guild)
        if webhook is None:
            return

        if before.display_name != after.display_name:

            if not await self.check(snowflake=after.guild.id, event="name_updates"):
                return

            embed = discord.Embed(
                description=f"**User:** {after.mention} **Name:** `{after}`\n"
                f"**Old Nickname:** `{before.display_name}`\n"
                f"**New Nickname:** `{after.display_name}`\n",
                colour=self.bot.constants.embed,
                timestamp=datetime.utcnow(),
            )
            embed.set_author(name=f"Nickname Change")
            embed.set_footer(text=f"User ID: {after.id}")

            await webhook.execute(embed=embed, username=self.bot.user.name)

        elif before.roles != after.roles:

            if not await self.check(snowflake=after.guild.id, event="role_changes"):
                return

            embed = discord.Embed(
                description=f"**User:** {after.mention} **Name:** `{after}`\n"
                f"**Old Roles:** {', '.join([r.mention for r in before.roles if r != after.guild.default_role])}\n"
                f"**New Roles:** {', '.join([r.mention for r in after.roles if r != after.guild.default_role])}\n",
                colour=self.bot.constants.embed,
                timestamp=datetime.utcnow(),
            )
            embed.set_author(name=f"Role Updates")
            embed.set_footer(text=f"User ID: {after.id}")

            await webhook.execute(embed=embed, username=self.bot.user.name)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if not self.bot.bot_ready:
            return

        if member.bot:
            return

        if not await self.check(snowflake=member.guild.id, event="voice_state_updates"):
            return

        webhook = await self.get_webhook(guild=member.guild)
        if webhook is None:
            return

        if not before.channel:

            embed = discord.Embed(
                description=f"**User:** {member.mention} **Name:** `{member}`\n",
                colour=self.bot.constants.embed,
                timestamp=datetime.utcnow(),
            )
            embed.set_author(name=f"Member Joined {after.channel.name}")
            embed.set_footer(text=f"User ID: {member.id}")

            await webhook.execute(embed=embed, username=self.bot.user.name)

        if before.channel and not after.channel:

            embed = discord.Embed(
                description=f"**User:** {member.mention} **Name:** `{member}`\n",
                colour=self.bot.constants.embed,
                timestamp=datetime.utcnow(),
            )
            embed.set_author(name=f"Membed Left Channel {before.channel.name}")
            embed.set_footer(text=f"User ID: {member.id}")

            await webhook.execute(embed=embed, username=self.bot.user.name)

        if before.channel and after.channel:
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

                await webhook.execute(embed=embed, username=self.bot.user.name)
            else:
                if member.voice.self_stream:
                    embed = discord.Embed(
                        description=f"**User:** {member.mention} **Name:** `{member}`\n"
                        f"**Channel:** {after.channel.mention} **ID:** `{after.channel.id}`\n",
                        colour=self.bot.constants.embed,
                        timestamp=datetime.utcnow(),
                    )
                    embed.set_author(name=f"User Started Streaming")
                    embed.set_footer(text=f"User ID: {member.id}")

                    await webhook.execute(embed=embed, username=self.bot.user.name)

                    self.current_streamers.append(member.id)

                elif member.voice.self_mute:
                    embed = discord.Embed(
                        description=f"**User:** {member.mention} **Name:** `{member}`\n"
                        f"**Channel:** {after.channel.mention} **ID:** `{after.channel.id}`\n",
                        colour=self.bot.constants.embed,
                        timestamp=datetime.utcnow(),
                    )
                    embed.set_author(name=f"User Muted")
                    embed.set_footer(text=f"User ID: {member.id}")

                    await webhook.execute(embed=embed, username=self.bot.user.name)

                elif member.voice.self_deaf:
                    embed = discord.Embed(
                        description=f"**User:** {member.mention} **Name:** `{member}`\n"
                        f"**Channel:** {after.channel.mention} **ID:** `{after.channel.id}`\n",
                        colour=self.bot.constants.embed,
                        timestamp=datetime.utcnow(),
                    )
                    embed.set_author(name=f"User Deafened")
                    embed.set_footer(text=f"User ID: {member.id}")

                    await webhook.execute(embed=embed, username=self.bot.user.name)

                else:
                    for streamer in self.current_streamers:
                        if member.id == streamer:
                            if not member.voice.self_stream:
                                embed = discord.Embed(
                                    description=f"**User:** {member.mention} **Name:** `{member}`\n"
                                    f"**Channel:** {after.channel.mention} **ID:** `{after.channel.id}`\n",
                                    colour=self.bot.constants.embed,
                                    timestamp=datetime.utcnow(),
                                )
                                embed.set_author(name=f"User Stopped Streaming")
                                embed.set_footer(text=f"User ID: {member.id}")

                                await webhook.execute(
                                    embed=embed, username=self.bot.user.name
                                )
                                self.current_streamers.remove(member.id)
                            break

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        if not self.bot.bot_ready:
            return

        if not after.guild:
            return

        if after.author.bot:
            return

        if not await self.check(snowflake=after.guild.id, event="message_edits"):
            return

        webhook = await self.get_webhook(guild=after.guild)
        if webhook is None:
            return

        embed = discord.Embed(
            description=f"**Author:**  {after.author.mention}, **ID:** `{after.author.id}`\n"
            f"**Channel:** {after.channel.mention} **ID:** `{after.channel.id}`\n"
            f"**Server:** `{after.guild.name}` **ID:** `{after.guild.id},`\n\n"
            f"**__Old Message Content__**\n ```fix\n{before.clean_content}```\n"
            f"**__New Message Content__**\n ```fix\n{after.clean_content}```\n"
            f"**[Jump to message](https://discord.com/channels/{after.guild.id}/{after.channel.id}/{after.id})**",
            color=self.bot.constants.embed,
            timestamp=datetime.utcnow(),
        )
        embed.set_author(
            name="Message Edited",
            icon_url="https://media.discordapp.net/attachments/506838906872922145/603643138854354944/messageupdate.png",
        )
        embed.set_footer(text=f"Message ID: {after.id}")
        await webhook.execute(embed=embed, username=self.bot.user.name)

    @commands.Cog.listener()
    async def on_message_delete(self, message):
        if not self.bot.bot_ready:
            return

        if not message.guild:
            return

        if message.author.bot:
            return

        if not await self.check(snowflake=message.guild.id, event="message_edits"):
            return

        webhook = await self.get_webhook(guild=message.guild)
        if webhook is None:
            return

        if message.content.startswith("```"):
            content = f"**__Message Content__**\n {message.clean_content}"
        else:
            content = f"**__Message Content__**\n ```fix\n{message.clean_content}```"

        embed = discord.Embed(
            description=f"**Author:**  {message.author.mention}, **ID:** `{message.author.id}`\n"
            f"**Channel:** {message.channel.mention} **ID:** `{message.channel.id}`\n"
            f"**Server:** `{message.guild.name}` **ID:** `{message.guild.id},`\n\n"
            f"{content}",
            color=self.bot.constants.embed,
            timestamp=datetime.utcnow(),
        )
        embed.set_author(
            name="Message Deleted",
            icon_url="https://media.discordapp.net/attachments/506838906872922145/603642595419357190/messagedelete.png",
        )
        embed.set_footer(text=f"Message ID: {message.id}")
        await webhook.execute(embed=embed, username=self.bot.user.name)

    @commands.Cog.listener()
    async def on_bulk_message_delete(self, messages):
        if not self.bot.bot_ready:
            return

        if not messages[0].guild:
            return
        if not await self.check(snowflake=messages[0].guild.id, event="message_edits"):
            return

        webhook = await self.get_webhook(guild=messages[0].guild)
        if webhook is None:
            return

        allmessages = ""

        for message in messages:
            allmessages += f"Content: {message.content}          Author: {message.author}          ID: {message.id}\n\n"

        embed = discord.Embed(
            description=f"**Channel:** {message.channel.mention} **ID:** `{message.channel.id}`\n"
            f"**Server:** `{message.guild.name}` **ID:** `{message.guild.id},`\n\n",
            color=self.bot.constants.embed,
            timestamp=datetime.utcnow(),
        )
        embed.set_author(
            name="Bulk Message Delete",
            icon_url="https://media.discordapp.net/attachments/506838906872922145/603642595419357190/messagedelete.png",
        )

        await webhook.execute(embed=embed, username=self.bot.user.name)

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

        await webhook.execute(
            file=discord.File(
                data,
                filename=f"'Bulk-Deleted-Messages-{datetime.now().__format__('%m-%d-%Y')}.txt",
            )
        )

    ##############
    ## Commands ##
    ##############

    async def do_logging(self, ctx, channel):
        bytes_avatar = await self.get(str(ctx.guild.me.avatar_url), res_method="read")
        print(bytes_avatar)
        webhook = await channel.create_webhook(
            name=self.bot.user.name + "-logger",
            avatar=bytes_avatar,
            reason="Webhook created for server logging.",
        )
        await self.bot.cxn.execute(
            "UPDATE logging SET logging_webhook_id = $1 WHERE server_id = $2",
            str(webhook.id),
            ctx.guild.id,
        )
        await self.bot.cxn.execute(
            "UPDATE logging SET logchannel = $1 WHERE server_id = $2",
            channel.id,
            ctx.guild.id,
        )
        self.bot.server_settings[ctx.guild.id]["logging"]["logchannel"] = channel.id
        self.bot.server_settings[ctx.guild.id]["logging"]["webhook_id"] = webhook.id
        await ctx.send(
            f"{self.emote_dict['success']} Set channel {channel.mention} as this server's logging channel."
        )
        await webhook.execute(
            content="Hello! I'm going to be logging your server's events in this channel from now on. "
            f"Use `{ctx.prefix}log <option>` to set the specific events you want documented here. "
            "By default, all events will be logged."
        )

    @commands.command(
        brief="Set your server's logging channel.",
        aliases=["logserver", "setlogchannel"],
    )
    @commands.guild_only()
    @permissions.bot_has_permissions(manage_webhooks=True)
    @permissions.has_permissions(manage_guild=True)
    async def logchannel(self, ctx, channel: discord.TextChannel = None):
        if channel is None:
            channel = ctx.channel

        webhook_id = self.bot.server_settings[ctx.guild.id]["logging"]["webhook_id"]
        logchannel = self.bot.server_settings[ctx.guild.id]["logging"]["logchannel"]
        if webhook_id is None or logchannel is None:
            return await self.do_logging(ctx, channel)

        try:
            self.bot.get_channel(logchannel)
        except BaseException:
            return await self.do_logging(ctx, channel)
        server_webhook_list = await ctx.guild.webhooks()

        for webhook in server_webhook_list:
            if str(webhook.id) == str(webhook_id):
                return await ctx.send(
                    f"{self.emote_dict['error']} Logging is already set up on this server"
                )

        await self.do_logging(ctx, channel)

    @commands.command(
        brief="Remove your server's logging channel.", aliases=["unlogserver"]
    )
    @commands.guild_only()
    @permissions.has_permissions(manage_guild=True)
    async def unlogchannel(self, ctx):
        server_webhook_list = await ctx.guild.webhooks()
        found = []
        for webhook in server_webhook_list:
            if str(webhook.id) == str(
                self.bot.server_settings[ctx.guild.id]["logging"]["webhook_id"]
            ):
                found.append(webhook.name)
        if found:
            await webhook.delete(reason=f"Logging webhook deleted by {ctx.author}.")
            await self.bot.cxn.execute(
                "UPDATE logging SET logging_webhook_id = NULL WHERE server_id = $1",
                ctx.guild.id,
            )
            await self.bot.cxn.execute(
                "UPDATE logging SET logchannel = NULL WHERE server_id = $1",
                ctx.guild.id,
            )
            await ctx.send(
                f"{self.emote_dict['success']} Logging is now disabled on this server"
            )
            return
        else:
            return await ctx.send(
                f"{self.emote_dict['error']} Logging is not enabled on this server."
            )

    @commands.group(
        brief="Customize your server's logging by enabling specific logging events"
    )
    @commands.guild_only()
    @permissions.has_permissions(manage_guild=True)
    async def log(self, ctx):
        """
        Usage:      -log <option>
        Example:    -log deletes
        Permission: Manage Server
        Output:     Enables a specific logging event
        Options:
            deletes
            edits
            roles
            names
            voice
            avatars
            bans
            channels
            leaves
            joins

        Notes:
            After your server's log channel has been setup,
            all actions are enabled by default.
        """
        if ctx.invoked_subcommand is None:
            help_command = self.bot.get_command("help")
            await help_command(ctx, invokercommand="log", pm=False)

    @log.command(
        name="deletes",
        brief="Log all message deletions",
        aliases=[
            "deletions",
            "messages",
            "message",
            "deleted_messages",
            "message_delete",
            "message_deletes",
            "delete_messages",
        ],
    )
    async def _deletes(self, ctx):
        logchan = (
            await self.bot.cxn.fetchrow(
                """
        SELECT logchannel FROM logging WHERE server_id = $1
        """,
                ctx.guild.id,
            )
            or None
        )
        if logchan is None or logchan[0] is None:
            return await ctx.send(
                f"{self.emote_dict['failed']} Logging not setup on this server. Use `{ctx.prefix}logserver` to setup a logging channel."
            )

        logchan = ctx.guild.get_channel(int(logchan[0]))

        await self.bot.cxn.execute(
            """
        UPDATE logging SET message_deletion = $1 WHERE server_id = $2
        """,
            True,
            ctx.guild.id,
        )
        await ctx.send(
            f"{self.emote_dict['success']} Message deletions will now be logged in {logchan.mention}"
        )

    @log.command(
        name="edits",
        brief="Log all message edits",
        aliases=[
            "edit",
            "message_update",
            "message_updates",
            "message_edits",
            "message_edit",
            "changes",
        ],
    )
    async def _edits(self, ctx):
        logchan = (
            await self.bot.cxn.fetchrow(
                """
        SELECT logchannel FROM logging WHERE server_id = $1
        """,
                ctx.guild.id,
            )
            or None
        )
        if logchan is None or logchan[0] is None:
            return await ctx.send(
                f"{self.emote_dict['failed']} Logging not setup on this server. Use `{ctx.prefix}logchannel` to setup a logging channel."
            )

        logchan = ctx.guild.get_channel(int(logchan[0]))

        await self.bot.cxn.execute(
            """
        UPDATE logging SET message_edit = $1 WHERE server_id = $2
        """,
            True,
            ctx.guild.id,
        )
        await ctx.send(
            f"{self.emote_dict['success']} Message edits will now be logged in {logchan.mention}"
        )

    @log.command(
        name="roles",
        brief="Log all role changes",
        aliases=[
            "role",
            "role_edits",
            "role_updates",
            "role_update",
            "role_changes",
            "role_change",
        ],
    )
    async def _roles(self, ctx):
        logchan = (
            await self.bot.cxn.fetchrow(
                """
        SELECT logchannel FROM logging WHERE server_id = $1
        """,
                ctx.guild.id,
            )
            or None
        )
        if logchan is None or logchan[0] is None:
            return await ctx.send(
                f"{self.emote_dict['failed']} Logging not setup on this server. Use `{ctx.prefix}logchannel` to setup a logging channel."
            )

        logchan = ctx.guild.get_channel(int(logchan[0]))

        await self.bot.cxn.execute(
            """
        UPDATE logging SET role_changes = $1 WHERE server_id = $2
        """,
            True,
            ctx.guild.id,
        )
        await ctx.send(
            f"{self.emote_dict['success']} Role changes will now be logged in {logchan.mention}"
        )

    @log.command(
        name="names",
        brief="Log all role changes",
        aliases=[
            "name",
            "name_changes",
            "nicknames",
            "nicks",
            "nickname_changes",
            "nick_changes",
        ],
    )
    async def _names(self, ctx):
        logchan = (
            await self.bot.cxn.fetchrow(
                """
        SELECT logchannel FROM logging WHERE server_id = $1
        """,
                ctx.guild.id,
            )
            or None
        )
        if logchan is None or logchan[0] is None:
            return await ctx.send(
                f"{self.emote_dict['failed']} Logging not setup on this server. Use `{ctx.prefix}logchannel` to setup a logging channel."
            )

        logchan = ctx.guild.get_channel(int(logchan[0]))

        await self.bot.cxn.execute(
            """
        UPDATE logging SET name_updates = $1 WHERE server_id = $2
        """,
            True,
            ctx.guild.id,
        )
        await ctx.send(
            f"{self.emote_dict['success']} Name changes will now be logged in {logchan.mention}"
        )

    @log.command(
        name="voice",
        brief="Log all member movements",
        aliases=["voice_updates", "movements", "voice_changes", "member_movement"],
    )
    async def _voice(self, ctx):
        logchan = (
            await self.bot.cxn.fetchrow(
                """
        SELECT logchannel FROM logging WHERE server_id = $1
        """,
                ctx.guild.id,
            )
            or None
        )
        if logchan is None or logchan[0] is None:
            return await ctx.send(
                f"{self.emote_dict['failed']} Logging not setup on this server. Use `{ctx.prefix}logchannel` to setup a logging channel."
            )

        logchan = ctx.guild.get_channel(int(logchan[0]))

        await self.bot.cxn.execute(
            """
        UPDATE logging SET voice_state_updates = $1 WHERE server_id = $2
        """,
            True,
            ctx.guild.id,
        )
        await ctx.send(
            f"{self.emote_dict['success']} Voice state updates will now be logged in {logchan.mention}"
        )

    @log.command(
        name="avatars",
        brief="Log all avatar changes",
        aliases=["avatar", "pfps", "profilepics", "avatar_changes"],
    )
    async def _avatars(self, ctx):
        logchan = (
            await self.bot.cxn.fetchrow(
                """
        SELECT logchannel FROM logging WHERE server_id = $1
        """,
                ctx.guild.id,
            )
            or None
        )
        if logchan is None or logchan[0] is None:
            return await ctx.send(
                f"{self.emote_dict['failed']} Logging not setup on this server. Use `{ctx.prefix}logchannel` to setup a logging channel."
            )

        logchan = ctx.guild.get_channel(int(logchan[0]))

        await self.bot.cxn.execute(
            """
        UPDATE logging SET avatar_changes = $1 WHERE server_id = $2
        """,
            True,
            ctx.guild.id,
        )
        await ctx.send(
            f"{self.emote_dict['success']} Avatar changes will now be logged in {logchan.mention}"
        )

    @log.command(
        name="bans", brief="Log all server bans", aliases=["ban", "server_bans"]
    )
    async def _bans(self, ctx):
        logchan = (
            await self.bot.cxn.fetchrow(
                """
        SELECT logchannel FROM logging WHERE server_id = $1
        """,
                ctx.guild.id,
            )
            or None
        )
        if logchan is None or logchan[0] is None:
            return await ctx.send(
                f"{self.emote_dict['failed']} Logging not setup on this server. Use `{ctx.prefix}logchannel` to setup a logging channel."
            )

        logchan = ctx.guild.get_channel(int(logchan[0]))

        await self.bot.cxn.execute(
            """
        UPDATE logging SET bans = $1 WHERE server_id = $2
        """,
            True,
            ctx.guild.id,
        )
        await ctx.send(
            f"{self.emote_dict['success']} Server bans will now be logged in {logchan.mention}"
        )

    @log.command(
        name="channels",
        brief="Log all server bans",
        aliases=["chan", "channel_updates", "channel_edits", "channel_changes"],
    )
    async def _channels(self, ctx):
        logchan = (
            await self.bot.cxn.fetchrow(
                """
        SELECT logchannel FROM logging WHERE server_id = $1
        """,
                ctx.guild.id,
            )
            or None
        )
        if logchan is None or logchan[0] is None:
            return await ctx.send(
                f"{self.emote_dict['failed']} Logging not setup on this server. Use `{ctx.prefix}logchannel` to setup a logging channel."
            )

        logchan = ctx.guild.get_channel(int(logchan[0]))

        await self.bot.cxn.execute(
            """
        UPDATE logging SET bans = $1 WHERE server_id = $2
        """,
            True,
            ctx.guild.id,
        )
        await ctx.send(
            f"{self.emote_dict['success']} Channel updates will now be logged in {logchan.mention}"
        )

    @log.command(name="leaves", brief="Log all server bans", aliases=["leave", "left"])
    async def _leaves(self, ctx):
        logchan = (
            await self.bot.cxn.fetchrow(
                """
        SELECT logchannel FROM logging WHERE server_id = $1
        """,
                ctx.guild.id,
            )
            or None
        )
        if logchan is None or logchan[0] is None:
            return await ctx.send(
                f"{self.emote_dict['failed']} Logging not setup on this server. Use `{ctx.prefix}logchannel` to setup a logging channel."
            )

        logchan = ctx.guild.get_channel(int(logchan[0]))

        await self.bot.cxn.execute(
            """
        UPDATE logging SET leaves = $1 WHERE server_id = $2
        """,
            True,
            ctx.guild.id,
        )
        await ctx.send(
            f"{self.emote_dict['success']} Member leave will now be logged in {logchan.mention}"
        )

    @log.command(
        name="joins",
        brief="Log all server bans",
        aliases=["join", "joined", "member_join"],
    )
    async def _joins(self, ctx):
        logchan = (
            await self.bot.cxn.fetchrow(
                """
        SELECT logchannel FROM logging WHERE server_id = $1
        """,
                ctx.guild.id,
            )
            or None
        )
        if logchan is None or logchan[0] is None:
            return await ctx.send(
                f"{self.emote_dict['failed']} Logging not setup on this server. Use `{ctx.prefix}logchannel` to setup a logging channel."
            )

        logchan = ctx.guild.get_channel(int(logchan[0]))

        await self.bot.cxn.execute(
            """
        UPDATE logging SET joins = $1 WHERE server_id = $2
        """,
            True,
            ctx.guild.id,
        )
        await ctx.send(
            f"{self.emote_dict['success']} Membed join will now be logged in {logchan.mention}"
        )

    @commands.group(
        brief="Customize your server's logging by disabling specific logging events"
    )
    @commands.guild_only()
    @permissions.has_permissions(manage_guild=True)
    async def unlog(self, ctx):
        """
        Usage:      -unlog <option>
        Example:    -unlog deletes
        Permission: Manage Server
        Output:     Disables a specific logging event
        Options:
            deletes
            edits
            roles
            names
            voice
            avatars
            bans
            channels
            leaves
            joins

        Notes:
            After your server's log channel has been setup,
            all actions are enabled by default.
        """
        if ctx.invoked_subcommand is None:
            help_command = self.bot.get_command("help")
            await help_command(ctx, invokercommand="unlog")

    @unlog.command(
        name="deletes",
        brief="Log all message deletions",
        aliases=[
            "deletions",
            "messages",
            "message",
            "deleted_messages",
            "message_delete",
            "message_deletes",
            "delete_messages",
        ],
    )
    async def deletes_(self, ctx):
        logchan = (
            await self.bot.cxn.fetchrow(
                """
        SELECT logchannel FROM logging WHERE server_id = $1
        """,
                ctx.guild.id,
            )
            or None
        )
        if logchan is None or logchan[0] is None:
            return await ctx.send(
                f"{self.emote_dict['failed']} Logging not setup on this server. Use `{ctx.prefix}logserver` to setup a logging channel."
            )

        logchan = ctx.guild.get_channel(int(logchan[0]))

        await self.bot.cxn.execute(
            """
        UPDATE logging SET message_deletion = $1 WHERE server_id = $2
        """,
            False,
            ctx.guild.id,
        )
        await ctx.send(
            f"{self.emote_dict['success']} Message deletions will now be logged in {logchan.mention}"
        )

    @unlog.command(
        name="edits",
        brief="Log all message edits",
        aliases=[
            "edit",
            "message_update",
            "message_updates",
            "message_edits",
            "message_edit",
            "changes",
        ],
    )
    async def edits_(self, ctx):
        logchan = (
            await self.bot.cxn.fetchrow(
                """
        SELECT logchannel FROM logging WHERE server_id = $1
        """,
                ctx.guild.id,
            )
            or None
        )
        if logchan is None or logchan[0] is None:
            return await ctx.send(
                f"{self.emote_dict['failed']} Logging not setup on this server. Use `{ctx.prefix}logchannel` to setup a logging channel."
            )

        logchan = ctx.guild.get_channel(int(logchan[0]))

        await self.bot.cxn.execute(
            """
        UPDATE logging SET message_edits = $1 WHERE server_id = $2
        """,
            False,
            ctx.guild.id,
        )
        await ctx.send(
            f"{self.emote_dict['success']} Message edits will now be logged in {logchan.mention}"
        )

    @unlog.command(
        name="roles",
        brief="Log all role changes",
        aliases=[
            "role",
            "role_edits",
            "role_updates",
            "role_update",
            "role_changes",
            "role_change",
        ],
    )
    async def roles_(self, ctx):
        logchan = (
            await self.bot.cxn.fetchrow(
                """
        SELECT logchannel FROM logging WHERE server_id = $1
        """,
                ctx.guild.id,
            )
            or None
        )
        if logchan is None or logchan[0] is None:
            return await ctx.send(
                f"{self.emote_dict['failed']} Logging not setup on this server. Use `{ctx.prefix}logchannel` to setup a logging channel."
            )

        logchan = ctx.guild.get_channel(int(logchan[0]))

        await self.bot.cxn.execute(
            """
        UPDATE logging SET role_changes = $1 WHERE server_id = $2
        """,
            False,
            ctx.guild.id,
        )
        await ctx.send(
            f"{self.emote_dict['success']} Role changes will now be logged in {logchan.mention}"
        )

    @unlog.command(
        name="names",
        brief="Log all role changes",
        aliases=[
            "name",
            "name_changes",
            "nicknames",
            "nicks",
            "nickname_changes",
            "nick_changes",
        ],
    )
    async def names_(self, ctx):
        logchan = (
            await self.bot.cxn.fetchrow(
                """
        SELECT logchannel FROM logging WHERE server_id = $1
        """,
                ctx.guild.id,
            )
            or None
        )
        if logchan is None or logchan[0] is None:
            return await ctx.send(
                f"{self.emote_dict['failed']} Logging not setup on this server. Use `{ctx.prefix}logchannel` to setup a logging channel."
            )

        logchan = ctx.guild.get_channel(int(logchan[0]))

        await self.bot.cxn.execute(
            """
        UPDATE logging SET name_updates = $1 WHERE server_id = $2
        """,
            False,
            ctx.guild.id,
        )
        await ctx.send(
            f"{self.emote_dict['success']} Name changes will now be logged in {logchan.mention}"
        )

    @unlog.command(
        name="voice",
        brief="Log all member movements",
        aliases=["movement", "voice_state", "voice_changes", "member_movement"],
    )
    async def voice_(self, ctx):
        logchan = (
            await self.bot.cxn.fetchrow(
                """
        SELECT logchannel FROM logging WHERE server_id = $1
        """,
                ctx.guild.id,
            )
            or None
        )
        if logchan is None or logchan[0] is None:
            return await ctx.send(
                f"{self.emote_dict['failed']} Logging not setup on this server. Use `{ctx.prefix}logchannel` to setup a logging channel."
            )

        logchan = ctx.guild.get_channel(int(logchan[0]))

        await self.bot.cxn.execute(
            """
        UPDATE logging SET voice_state_updates = $1 WHERE server_id = $2
        """,
            False,
            ctx.guild.id,
        )
        await ctx.send(
            f"{self.emote_dict['success']} Voice state updates will no longer be logged in {logchan.mention}"
        )

    @unlog.command(
        name="avatar",
        brief="Unlog all avatar changes",
        aliases=[
            "avatars",
            "avatar_changes",
            "pfps",
            "profilepics",
            "pfp_changes",
            "profilepic_changes",
            "avatar_updates",
        ],
    )
    async def avatar_(self, ctx):
        logchan = (
            await self.bot.cxn.fetchrow(
                """
        SELECT logchannel FROM logging WHERE server_id = $1
        """,
                ctx.guild.id,
            )
            or None
        )
        if logchan is None or logchan[0] is None:
            return await ctx.send(
                f"{self.emote_dict['failed']} Logging not setup on this server. Use `{ctx.prefix}logchannel` to setup a logging channel."
            )

        logchan = ctx.guild.get_channel(int(logchan[0]))

        await self.bot.cxn.execute(
            """
        UPDATE logging SET avatar_changes = $1 WHERE server_id = $2
        """,
            False,
            ctx.guild.id,
        )
        await ctx.send(
            f"{self.emote_dict['success']} Avatar changes will no longer be logged in {logchan.mention}"
        )

    @unlog.command(
        name="bans",
        brief="Unlog all server bans",
        aliases=["banned", "member_remove", "banning", "banish"],
    )
    async def bans_(self, ctx):
        logchan = (
            await self.bot.cxn.fetchrow(
                """
        SELECT logchannel FROM logging WHERE server_id = $1
        """,
                ctx.guild.id,
            )
            or None
        )
        if logchan is None or logchan[0] is None:
            return await ctx.send(
                f"{self.emote_dict['failed']} Logging not setup on this server. Use `{ctx.prefix}logchannel` to setup a logging channel."
            )

        logchan = ctx.guild.get_channel(int(logchan[0]))

        await self.bot.cxn.execute(
            """
        UPDATE logging SET bans = $1 WHERE server_id = $2
        """,
            False,
            ctx.guild.id,
        )
        await ctx.send(
            f"{self.emote_dict['success']} Server bans will now be logged in {logchan.mention}"
        )

    @unlog.command(
        name="channels",
        brief="Unlog all channel updates",
        aliases=["channel", "channel_updates", "channel_changes"],
    )
    async def channels_(self, ctx):
        logchan = (
            await self.bot.cxn.fetchrow(
                """
        SELECT logchannel FROM logging WHERE server_id = $1
        """,
                ctx.guild.id,
            )
            or None
        )
        if logchan is None or logchan[0] is None:
            return await ctx.send(
                f"{self.emote_dict['failed']} Logging not setup on this server. Use `{ctx.prefix}logchannel` to setup a logging channel."
            )

        logchan = ctx.guild.get_channel(int(logchan[0]))

        await self.bot.cxn.execute(
            """
        UPDATE logging SET channel_updates = $1 WHERE server_id = $2
        """,
            False,
            ctx.guild.id,
        )
        await ctx.send(
            f"{self.emote_dict['success']} Server bans will no longer be logged in {logchan.mention}"
        )

    @unlog.command(
        name="leaves",
        brief="Unlog all server leaves",
        aliases=["leave", "left", "member_leave", "memver_leaves"],
    )
    async def leaves_(self, ctx):
        logchan = (
            await self.bot.cxn.fetchrow(
                """
        SELECT logchannel FROM logging WHERE server_id = $1
        """,
                ctx.guild.id,
            )
            or None
        )
        if logchan is None or logchan[0] is None:
            return await ctx.send(
                f"{self.emote_dict['failed']} Logging not setup on this server. Use `{ctx.prefix}logchannel` to setup a logging channel."
            )

        logchan = ctx.guild.get_channel(int(logchan[0]))

        await self.bot.cxn.execute(
            """
        UPDATE logging SET leaves = $1 WHERE server_id = $2
        """,
            False,
            ctx.guild.id,
        )
        await ctx.send(
            f"{self.emote_dict['success']} Server leaves will no longer be logged in {logchan.mention}"
        )

    @unlog.command(
        name="joins",
        brief="Unlog all server joins",
        aliases=["join", "joined", "member_join", "membed_joins", "membed_add"],
    )
    async def joins_(self, ctx):
        logchan = (
            await self.bot.cxn.fetchrow(
                """
        SELECT logchannel FROM logging WHERE server_id = $1
        """,
                ctx.guild.id,
            )
            or None
        )
        if logchan is None or logchan[0] is None:
            return await ctx.send(
                f"{self.emote_dict['failed']} Logging not setup on this server. Use `{ctx.prefix}logchannel` to setup a logging channel."
            )

        logchan = ctx.guild.get_channel(int(logchan[0]))

        await self.bot.cxn.execute(
            """
        UPDATE logging SET joins = $1 WHERE server_id = $1
        """,
            False,
            ctx.guild.id,
        )
        await ctx.send(
            f"{self.emote_dict['success']} Server joins will no longer be logged in {logchan.mention}"
        )
