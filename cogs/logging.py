import io
import re
import discord

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

    #############################
    ## Logging Check Functions ##
    #############################

    async def check(self, snowflake, event):  # This checks whether or not to log.
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

    async def get_webhook(
        self, guild
    ):  # This gets the logging webhook for a guild if they have logging setup
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
        # Should never get here but if it does, just return so no logging occurs.
        return

    #####################
    ## Event Listeners ##
    #####################

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
            description=f"**Channel:** `{channel.name}` **ID:** `{channel.id}`\n"
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
            description=f"**Channel:** `{channel.name}` **ID:** `{channel.id}`\n"
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

        elif isinstance(before, discord.TextChannel) and before.topic != after.topic:
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

        # elif before.position != after.position:
        #     embed = discord.Embed(
        #         description=f"**Channel:** {after.mention} **Name:** `{after}`\n"
        #         f"**Old Position:** `{before.position}`\n"
        #         f"**New Position:** `{after.position}`\n",
        #         colour=self.bot.constants.embed,
        #         timestamp=datetime.utcnow(),
        #     )
        #     embed.set_author(name=f"Channel Update")
        #     embed.set_footer(text=f"Channel ID: {after.id}")
        #     await webhook.execute(embed=embed, username=self.bot.user.name)

        elif (
            isinstance(before, discord.TextChannel)
            and before.slowmode_delay != after.slowmode_delay
        ):
            embed = discord.Embed(
                description=f"**Channel:** {after.mention} **Name:** `{after}`\n"
                f"**Old Slowmode:** `{before.slowmode_delay}`\n"
                f"**New Slowmode:** `{after.slowmode_delay}`\n",
                colour=self.bot.constants.embed,
                timestamp=datetime.utcnow(),
            )
            embed.set_author(name=f"Channel Update")
            embed.set_footer(text=f"Channel ID: {after.id}")
            await webhook.execute(embed=embed, username=self.bot.user.name)

        elif (
            isinstance(before, discord.VoiceChannel)
            and before.user_limit != after.user_limit
        ):
            embed = discord.Embed(
                description=f"**Channel:** {after.mention} **Name:** `{after}`\n"
                f"**Old User Limit:** `{before.user_limit}`\n"
                f"**New User Limit:** `{after.user_limit}`\n",
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

    # Create our custom event listener for all moderation actions
    @commands.Cog.listener()
    async def on_mod_action(self, ctx, targets):
        webhook = await self.get_webhook(guild=ctx.guild)
        if webhook is None:
            return

        if not await self.check(snowflake=ctx.guild.id, event="bans"):
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
            if "@everyone" not in [x.name for x in before.roles]:
                print("New Member")
                return

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
    async def on_user_update(self, before, after):
        if not self.bot.bot_ready:
            return

        if after.bot:
            return

        users_guilds = []
        for guild in self.bot.guilds:
            mem_obj = guild.get_member(after.id)
            if mem_obj is not None:
                users_guilds.append(guild)

        for guild in users_guilds:
            webhook = await self.get_webhook(guild=guild)
            if webhook is None:
                continue

            if before.name != after.name:
                if await self.check(snowflake=guild.id, event="name_updates"):

                    embed = discord.Embed(
                        description=f"**User:** {after.mention} **Name:** `{after}`\n"
                        f"**Old Username:** `{before.name}`\n"
                        f"**New Username:** `{after.name}`\n",
                        colour=self.bot.constants.embed,
                        timestamp=datetime.utcnow(),
                    )
                    embed.set_author(name=f"Username Change")
                    embed.set_footer(text=f"User ID: {after.id}")

                    await webhook.execute(embed=embed, username=self.bot.user.name)

            elif before.discriminator != after.discriminator:
                if await self.check(snowflake=guild.id, event="name_updates"):

                    embed = discord.Embed(
                        description=f"**User:** {after.mention} **Name:** `{after}`\n"
                        f"**Old Discriminator:** `{before.discriminator}`\n"
                        f"**New Discriminator:** `{after.discriminator}`\n",
                        colour=self.bot.constants.embed,
                        timestamp=datetime.utcnow(),
                    )
                    embed.set_author(name=f"Discriminator Change")
                    embed.set_footer(text=f"User ID: {after.id}")

                    await webhook.execute(embed=embed, username=self.bot.user.name)

            elif before.avatar_url != after.avatar_url:
                if await self.check(snowflake=guild.id, event="avatar_changes"):

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

        if not before.channel and after.channel:

            embed = discord.Embed(
                description=f"**User:** {member.mention} **Name:** `{member}`\n**Channel:** {after.channel.mention} ID: `{after.channel.id}`\n",
                colour=self.bot.constants.embed,
                timestamp=datetime.utcnow(),
            )
            embed.set_author(name=f"User Joined Voice Channel")
            embed.set_footer(text=f"User ID: {member.id}")

            await webhook.execute(embed=embed, username=self.bot.user.name)

        if before.channel and not after.channel:

            embed = discord.Embed(
                description=f"**User:** {member.mention} **Name:** `{member}`\n**Channel:** {before.channel.mention} ID: `{before.channel.id}`\n",
                colour=self.bot.constants.embed,
                timestamp=datetime.utcnow(),
            )
            embed.set_author(name=f"User Left Voice Channel")
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

        if before.content == after.content:
            return  # giphy, tenor, and imgur links trigger this but they shouldn't be logged

        if not await self.check(snowflake=after.guild.id, event="message_edits"):
            return

        webhook = await self.get_webhook(guild=after.guild)
        if webhook is None:
            return

        if before.content == "":
            before_content = f"**__Old Message Content__**\n ```fix\nNo Content```\n"
        elif before.content.startswith("```"):
            before_content = f"**__Old Message Content__**\n {before.clean_content}\n"
        else:
            before_content = (
                f"**__Old Message Content__**\n ```fix\n{before.clean_content}```\n"
            )

        if after.content == "":
            after_content = f"**__New Message Content__**\n ```fix\nNo Content```\n"
        elif after.content.startswith("```"):
            after_content = f"**__New Message Content__**\n {after.clean_content}\n"
        else:
            after_content = (
                f"**__New Message Content__**\n ```fix\n{after.clean_content}```\n"
            )

        embed = discord.Embed(
            description=f"**Author:**  {after.author.mention}, **ID:** `{after.author.id}`\n"
            f"**Channel:** {after.channel.mention} **ID:** `{after.channel.id}`\n"
            f"**Server:** `{after.guild.name}` **ID:** `{after.guild.id},`\n\n"
            f"{before_content}"
            f"{after_content}"
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

        if not await self.check(snowflake=message.guild.id, event="message_deletions"):
            return

        webhook = await self.get_webhook(guild=message.guild)
        if webhook is None:
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
            f"**Server:** `{message.guild.name}` **ID:** `{message.guild.id},`\n\n"
            f"{content}"
            f"{attachments}",
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
        if not await self.check(
            snowflake=messages[0].guild.id, event="message_deletions"
        ):
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
            f"{self.bot.emote_dict['success']} Set channel {channel.mention} as this server's logging channel."
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
    @permissions.has_permissions(manage_guild=True)
    async def logchannel(self, ctx, channel: discord.TextChannel = None):
        """
        Usage: -logchannel [channel]
        Aliases: -logserver, -setlogchannel
        Output: Sets up a logging channel for the server
        Notes:
            Use -log [event] and -unlog [event] to enable/disable
            specific logging events that are sent to the logchannel
        """
        if channel is None:
            channel = ctx.channel

        webhook_id = self.bot.server_settings[ctx.guild.id]["logging"]["webhook_id"]
        logchannel = self.bot.server_settings[ctx.guild.id]["logging"]["logchannel"]
        if webhook_id is None or logchannel is None:
            return await self.do_logging(ctx, channel)

        try:
            self.bot.get_channel(logchannel)
        except:
            return await self.do_logging(ctx, channel)
        server_webhook_list = await ctx.guild.webhooks()

        for webhook in server_webhook_list:
            if str(webhook.id) == str(webhook_id):
                return await ctx.send(
                    f"{self.bot.emote_dict['error']} Logging is already set up on this server"
                )

        await self.do_logging(ctx, channel)

    @commands.command(brief="Remove the logging channel.", aliases=["unlogserver"])
    @commands.guild_only()
    @permissions.has_permissions(manage_guild=True)
    async def unlogchannel(self, ctx):
        """
        Usage: -unlogchannel
        Alias: -unlogserver
        Permission: Manage Server
        Output:
            Removes the server's logging channel
        """
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
                reference=self.bot.rep_ref(ctx),
                content=f"{self.bot.emote_dict['success']} Logging is now disabled on this server",
            )
            return
        else:
            return await ctx.send(
                reference=self.bot.rep_ref(ctx),
                content=f"{self.bot.emote_dict['error']} Logging is not enabled on this server.",
            )

    @commands.command(brief="Enable specific logging events.")
    @commands.guild_only()
    @permissions.has_permissions(manage_guild=True)
    async def log(self, ctx, log_arg):
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
            moderation
            channels
            leaves
            joins
        Notes:
            After your server's log channel has been setup,
            all actions are enabled by default.
            Use 'all' as an option to enable all options.
        """
        await self.log_or_unlog(ctx, log_arg)

    @commands.command(brief="Disable specific logging events.")
    @commands.guild_only()
    @permissions.has_permissions(manage_guild=True)
    async def unlog(self, ctx, log_arg):
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
            moderation
            channels
            leaves
            joins

        Notes:
            After your server's log channel has been setup,
            all actions are enabled by default.
            -----------------------------------------------
            Use 'all' as an option to disable all options.
        """
        await self.log_or_unlog(ctx, log_arg, False)

    async def log_or_unlog(self, ctx, log_arg, log_bool=True):
        async with ctx.channel.typing():
            # aliases in lists (constants)
            deletes = [
                "deletes",
                "deletions",
                "messages",
                "message",
                "deleted_messages",
                "message_delete",
                "message_deletes",
                "delete_messages",
            ]
            edits = [
                "edits",
                "edit",
                "message_update",
                "message_updates",
                "message_edits",
                "message_edit",
                "changes",
            ]
            roles = [
                "roles",
                "role",
                "role_edits",
                "role_updates",
                "role_update",
                "role_changes",
                "role_change",
            ]
            names = [
                "names",
                "name",
                "name_changes",
                "nicknames",
                "nicks",
                "nickname_changes",
                "nick_changes",
            ]
            voice = [
                "voice",
                "voice_updates",
                "movements",
                "voice_changes",
                "member_movement",
            ]
            avatars = ["avatars", "avatar", "pfps", "profilepics", "avatar_changes"]
            moderation = [
                "moderation",
                "ban",
                "server_bans",
                "mod",
                "bans",
                "mod_actions",
                "actions",
            ]
            channels = [
                "channels",
                "chan",
                "channel_updates",
                "channel_edits",
                "channel_changes",
            ]
            leaves = ["leaves", "leave", "left"]
            joins = ["joins", "join", "joined", "member_join"]
            all_option = ["all", "*"]
            types_of_logs = [
                deletes,
                edits,
                roles,
                names,
                voice,
                avatars,
                moderation,
                channels,
                leaves,
                joins,
                all_option,
            ]
            type_of_log = None
            # finding type of log from argument using aliases
            for log_type in types_of_logs:
                if log_arg in log_type:
                    type_of_log = log_type[0]
            if type_of_log is None:
                # invalid logging type
                await ctx.send(
                    f"{self.bot.emote_dict['failed']} `{log_arg.capitalize()}` is not a valid logging option. Use `{ctx.prefix}log help` for more info."
                )
                return
            if type_of_log == "all":
                list_of_log_types = [
                    "message_deletions",
                    "message_edits",
                    "role_changes",
                    "name_updates",
                    "voice_state_updates",
                    "avatar_changes",
                    "bans",
                    "channel_updates",
                    "leaves",
                    "joins",
                ]
                # first check if all logging is already enabled/disabled
                log_dict = self.bot.server_settings[ctx.guild.id]["logging"]
                current_list = [log_dict[item] for item in list_of_log_types]
                if all([item == log_bool for item in current_list]):
                    return await ctx.send(
                        f"{self.bot.emote_dict['success']} All logging events are already {'enabled' if log_bool else 'disabled'}."
                    )

                for i in list_of_log_types:
                    query = f"""
                            UPDATE logging
                            SET {i} = $1
                            WHERE server_id = $2;
                            """
                    await self.bot.cxn.execute(query, log_bool, ctx.guild.id)
                    self.bot.server_settings[ctx.guild.id]["logging"][i] = log_bool
                if log_bool:
                    await ctx.send(
                        f"{self.bot.emote_dict['success']} All logging events have been enabled."
                    )
                elif not log_bool:
                    await ctx.send(
                        f"{self.bot.emote_dict['success']} All logging events have been disabled."
                    )
                return

            # converts data to the names in psql so the db can be updated
            logdict = {
                "deletes": "message_deletions",
                "edits": "message_edits",
                "roles": "role_changes",
                "names": "name_updates",
                "voice": "voice_state_updates",
                "avatars": "avatar_changes",
                "moderation": "bans",
                "channels": "channel_updates",
                "leaves": "leaves",
                "joins": "joins",
            }
            psql_type_of_log = logdict[type_of_log]
            # get logging channel
            query = """
                    SELECT logchannel
                    FROM logging
                    WHERE server_id = $1;
                    """
            logchan = await self.bot.cxn.fetchval(query, ctx.guild.id) or None
            if logchan is None:
                # no existing logging channel
                return await ctx.send(
                    f"{self.bot.emote_dict['failed']} Logging not setup on this server. "
                    f"Use `{ctx.prefix}logserver` to setup a logging channel."
                )
            logchan = ctx.guild.get_channel(int(logchan))
            # update db
            if (
                self.bot.server_settings[ctx.guild.id]["logging"][psql_type_of_log]
                is log_bool
            ):
                if log_bool:
                    await ctx.send(
                        f"{self.bot.emote_dict['success']} {type_of_log.capitalize()} is already enabled."
                    )
                elif not log_bool:
                    await ctx.send(
                        f"{self.bot.emote_dict['success']} {type_of_log.capitalize()} is already disabled."
                    )
                return

            query = f"""
                    UPDATE logging
                    SET {psql_type_of_log} = $1
                    WHERE server_id = $2;
                    """
            await self.bot.cxn.execute(query, log_bool, ctx.guild.id)
            self.bot.server_settings[ctx.guild.id]["logging"][
                psql_type_of_log
            ] = log_bool
            if log_bool:
                await ctx.send(
                    f"{self.bot.emote_dict['success']} {type_of_log.capitalize()} will now be logged in {logchan.mention}"
                )
            else:
                await ctx.send(
                    f"{self.bot.emote_dict['success']} {type_of_log.capitalize()} will no longer be logged in {logchan.mention}"
                )
