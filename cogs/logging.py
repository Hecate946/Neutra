import io
import re
import discord

from datetime import datetime
from discord.ext import commands
from utilities import humantime
from utilities import utils
from utilities import checks
from utilities import converters
from utilities import decorators

CREATED_MESSAGE = "https://cdn.discordapp.com/attachments/846597178918436885/846841649542725632/messagecreate.png"
UPDATED_MESSAGE = "https://cdn.discordapp.com/attachments/846597178918436885/846841668639653939/messageupdate.png"
DELETED_MESSAGE = "https://cdn.discordapp.com/attachments/846597178918436885/846841722994163722/messagedelete.png"


def setup(bot):
    bot.add_cog(Logging(bot))


class Logging(commands.Cog):
    """
    Log all server events.
    """

    def __init__(self, bot):
        self.bot = bot
        self.current_streamers = list()

    # Helper function to truncate oversized strings.
    def truncate(self, string, max_chars):
        return (string[:max_chars - 3] + "...") if len(string) > max_chars else string

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

    async def get_webhook(self, guild):
        # This gets the logging webhook for a guild if they have logging setup
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
    @decorators.wait_until_ready()
    async def on_message(self, message):
        if message.author.bot:
            return
        if not message.guild:
            return
        webhook = await self.get_webhook(guild=message.guild)
        if webhook is None:
            return
        if not self.bot.server_settings[message.guild.id]["logging"]["discord_invites"]:
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
        await webhook.send(embed=embed)

    @commands.Cog.listener()
    async def on_guild_update(self, before, after):
        webhook = await self.get_webhook(guild=after)

        if webhook is None:
            return
        if not self.bot.server_settings[after.id]["logging"]["server_updates"]:
            return

        audit = [
            entry
            async for entry in after.audit_logs(
                action=discord.AuditLogAction.guild_update
            )
        ][0]
        if not before.name == after.name:
            embed = discord.Embed(
                description=f"**Author:**  `{audit.user.name}#{audit.user.discriminator}`\n\n"
                f"**___Previous Name___**: ```fix\n{before.name}```"
                f"**___Current Name___**: ```fix\n{after.name}```",
                color=self.bot.constants.embed,
            )

            embed.set_author(
                name="Server Name Edited",
                icon_url=UPDATED_MESSAGE,
            )

            return await webhook.send(embed=embed)
        embed = discord.Embed(
            description=f"**Author:**  `{audit.user.name}#{audit.user.discriminator}`\n"
            "**New Image below**",
            color=self.bot.constants.embed,
        )

        embed.set_author(
            name="Server Icon Edited",
            icon_url=UPDATED_MESSAGE,
        )

        embed.set_image(url=after.icon_url)
        return await webhook.send(embed=embed)

    @commands.Cog.listener()
    async def on_guild_emojis_update(self, guild, before, after):
        webhook = await self.get_webhook(guild=guild)
        if webhook is None:
            return

        if not self.bot.server_settings[guild.id]["logging"]["emojis"]:
            return

        new = True if len(after) > len(before) else False
        emoji = after[-1] if new else None

        if not new:
            for emoji in before:
                if emoji not in after:
                    old_emoji = emoji
                    new = False

        embed = discord.Embed(
            color=self.bot.constants.embed,
            timestamp=datetime.utcnow(),
            footer={"text": emoji.id},
        )

        if new:
            embed.description = (
                f"**Emoji: <:{emoji.name}:{emoji.id}>\nName: `{emoji.name}`**\n",
            )
        else:
            embed.description = f"**Name: `{emoji.name}`**\n"

        embed.set_author(
            name=f"Emoji {'created' if new else 'deleted'}.",
            icon_url=f"{CREATED_MESSAGE if new else DELETED_MESSAGE}",
        )

        await webhook.send(embed=embed)

    @commands.Cog.listener()
    @decorators.wait_until_ready()
    async def on_guild_channel_create(self, channel):
        if not await self.check(snowflake=channel.guild.id, event="channel_updates"):
            return

        webhook = await self.get_webhook(guild=channel.guild)
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
        await webhook.send(embed=embed)

    @commands.Cog.listener()
    @decorators.wait_until_ready()
    async def on_guild_channel_delete(self, channel):
        if not await self.check(snowflake=channel.guild.id, event="channel_updates"):
            return

        webhook = await self.get_webhook(guild=channel.guild)
        if webhook is None:
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
        await webhook.send(embed=embed)

    @commands.Cog.listener()
    @decorators.wait_until_ready()
    async def on_guild_channel_update(self, before, after):
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
            await webhook.send(embed=embed)

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
            await webhook.send(embed=embed)

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
                await webhook.send(embed=embed)

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
        #     await webhook.send(embed=embed)

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
                await webhook.send(embed=embed)

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
                await webhook.send(embed=embed)

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
            await webhook.send(embed=embed)

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
        await webhook.send(embed=embed)

    @commands.Cog.listener()
    @decorators.wait_until_ready()
    async def on_member_join(self, member):
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
        await webhook.send(embed=embed)

    @commands.Cog.listener()
    @decorators.wait_until_ready()
    async def on_member_remove(self, member):
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
        await webhook.send(embed=embed)

    @commands.Cog.listener()
    @decorators.wait_until_ready()
    @decorators.event_check(lambda s, b, a: not a.bot)
    async def on_member_update(self, before, after):
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

            await webhook.send(embed=embed)

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

            await webhook.send(embed=embed)

    @commands.Cog.listener()
    @decorators.wait_until_ready()
    @decorators.event_check(lambda s, b, a: not a.bot)
    async def on_user_update(self, before, after):
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

                    await webhook.send(embed=embed)

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

                    await webhook.send(embed=embed)

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
                    await webhook.send(embed=embed)

    @commands.Cog.listener()
    @decorators.wait_until_ready()
    @decorators.event_check(lambda s, m, b, a: not m.bot)
    async def on_voice_state_update(self, member, before, after):
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

            await webhook.send(embed=embed)

        if before.channel and not after.channel:

            embed = discord.Embed(
                description=f"**User:** {member.mention} **Name:** `{member}`\n**Channel:** {before.channel.mention} ID: `{before.channel.id}`\n",
                colour=self.bot.constants.embed,
                timestamp=datetime.utcnow(),
            )
            embed.set_author(name=f"User Left Voice Channel")
            embed.set_footer(text=f"User ID: {member.id}")

            await webhook.send(embed=embed)

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

                await webhook.send(embed=embed)
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

                    await webhook.send(embed=embed)

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

                    await webhook.send(embed=embed)

                elif member.voice.self_deaf:
                    embed = discord.Embed(
                        description=f"**User:** {member.mention} **Name:** `{member}`\n"
                        f"**Channel:** {after.channel.mention} **ID:** `{after.channel.id}`\n",
                        colour=self.bot.constants.embed,
                        timestamp=datetime.utcnow(),
                    )
                    embed.set_author(name=f"User Deafened")
                    embed.set_footer(text=f"User ID: {member.id}")

                    await webhook.send(embed=embed)

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

                                await webhook.send(embed=embed)
                                self.current_streamers.remove(member.id)
                            break

    @commands.Cog.listener()
    @decorators.wait_until_ready()
    @decorators.event_check(lambda s, b, a: a.guild and not a.author.bot)
    async def on_message_edit(self, before, after):
        if before.content == after.content:
            return  # giphy, tenor, and imgur links trigger this but they shouldn't be logged

        if not await self.check(snowflake=after.guild.id, event="message_edits"):
            return

        webhook = await self.get_webhook(guild=after.guild)
        if not webhook:
            return

        if before.content == "":
            bcontent = "```fix\nNo Content```" + "**\n**"
        elif before.content.startswith("```"):
            bcontent = self.truncate(before.clean_content, 1000) + "**\n**"
        else:
            bcontent = f"```fix\n{self.truncate(before.clean_content, 1000)}```" + "**\n**"

        if after.content == "":
            acontent = "```fix\nNo Content```"
        elif after.content.startswith("```"):
            acontent = self.truncate(after.clean_content, 1000)
        else:
            acontent = f"```fix\n{self.truncate(after.clean_content, 1000)}```"

        jump_url = f"**[Jump to message](https://discord.com/channels/{after.guild.id}/{after.channel.id}/{after.id})**"
        embed = discord.Embed(
            description=f"**Author:**  {after.author.mention}, **ID:** `{after.author.id}`\n"
            f"**Channel:** {after.channel.mention} **ID:** `{after.channel.id}`\n"
            f"**Server:** `{after.guild.name}` **ID:** `{after.guild.id}`\n **\n**",
            color=self.bot.constants.embed,
            timestamp=datetime.utcnow(),
        )
        embed.add_field(name="__**Old Message Content**__", value=bcontent, inline=False)
        embed.add_field(name="__**New Message Content**__", value=acontent, inline=False)
        embed.add_field(name="** **", value=jump_url)
        embed.set_author(
            name="Message Edited",
            icon_url=UPDATED_MESSAGE,
        )
        embed.set_footer(text=f"Message ID: {after.id}")
        await webhook.send(embed=embed)

    @commands.Cog.listener()
    @decorators.wait_until_ready()
    @decorators.event_check(lambda s, m: m.guild and not m.author.bot)
    async def on_message_delete(self, message):
        if not await self.check(snowflake=message.guild.id, event="message_deletions"):
            return

        webhook = await self.get_webhook(guild=message.guild)
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
        await webhook.send(embed=embed)

    @commands.Cog.listener()
    @decorators.wait_until_ready()
    @decorators.event_check(lambda s, m: m[0].guild is not None)
    async def on_bulk_message_delete(self, messages):
        if not await self.check(messages[0].guild.id, event="message_deletions"):
            return

        webhook = await self.get_webhook(guild=messages[0].guild)
        if not webhook:
            return

        allmessages = ""
        spaces = ' ' * 10
        for message in messages:
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

        await webhook.send(embed=embed)

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

        await webhook.send(
            file=discord.File(
                data,
                filename=f"'Bulk-Deleted-Messages-{datetime.now().__format__('%m-%d-%Y')}.txt",
            )
        )

    ##############
    ## Commands ##
    ##############

    async def do_logging(self, ctx, channel):
        bytes_avatar = await self.bot.get(
            str(ctx.guild.me.avatar_url), res_method="read"
        )
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
        await ctx.send_or_reply(
            f"{self.bot.emote_dict['success']} Set channel {channel.mention} as this server's logging channel."
        )
        await webhook.send(
            content="Hello! I'm going to be logging your server's events in this channel from now on. "
            f"Use `{ctx.prefix}log <option>` to set the specific events you want documented here. "
            "By default, all events will be logged."
        )

    @decorators.command(
        brief="Set your server's logging channel.",
        aliases=["logserver", "setlogchannel"],
    )
    @commands.guild_only()
    @checks.bot_has_perms(manage_webhooks=True)
    @checks.has_perms(manage_guild=True)
    async def logchannel(self, ctx, channel: discord.TextChannel = None):
        """
        Usage: {0}logchannel [channel]
        Aliases: {0}logserver, {0}setlogchannel
        Output: Sets up a logging channel for the server
        Notes:
            Use {0}log [event] and {0}unlog [event] to enable/disable
            specific logging events that are sent to the logchannel
        """
        if channel is None:
            channel = (
                ctx.channel
            )  # no arguments sets current channel to logging channel

        webhook_id = self.bot.server_settings[ctx.guild.id]["logging"]["webhook_id"]
        logchannel = self.bot.server_settings[ctx.guild.id]["logging"]["logchannel"]

        try:
            self.bot.get_channel(logchannel)
        except:
            return await self.do_logging(ctx, channel)
        server_webhook_list = await ctx.guild.webhooks()

        for webhook in server_webhook_list:
            if str(webhook.id) == str(webhook_id):  # if current log channel exists
                if (
                    self.bot.get_channel(logchannel) == channel
                ):  # if log channel is same as current log channel
                    return await ctx.send_or_reply(
                        f"{self.bot.emote_dict['failed']} This is already the logging channel."
                    )

                await self.unlogchannel(ctx, write=False)  # unlogs current channel
                return await self.logchannel(
                    ctx, channel
                )  # does it again but with no existing log channel

        return await self.do_logging(ctx, channel)

    @decorators.command(brief="Remove the logging channel.", aliases=["unlogserver"])
    @commands.guild_only()
    @checks.bot_has_perms(manage_webhooks=True)
    @checks.has_perms(manage_guild=True)
    async def unlogchannel(self, ctx, write=True):
        """
        Usage: {0}unlogchannel
        Alias: {0}unlogserver
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
        if write:
            return await ctx.send_or_reply(
                content=f"{self.bot.emote_dict['success' if found else 'warn']} Logging is {'now disabled' if found else 'not enabled'} on this server."
            )

    @decorators.command(
        brief="Enable specific logging events.",
        implemented="2021-03-17 07:09:57.666073",
        updated="2021-04-09 17:56:27.841985",
        writer=782479134436753428,
    )
    @commands.guild_only()
    @checks.bot_has_perms(embed_links=True)
    @checks.has_perms(manage_guild=True)
    async def log(self, ctx, *, log_arg=None):
        """
        Usage:      {0}log <option>
        Example:    {0}log deletes
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
            server
            invites
            emojis
        Notes:
            After your server's log channel has been setup,
            all actions are enabled by default.
            Use 'all' as an option to enable all options.
            Using no arguments gets a list of what is currently logged.
        """
        if log_arg is not None:
            return await self.log_or_unlog(ctx, log_arg)  # logs the argument passed

        if self.bot.server_settings[ctx.guild.id]["logging"]["logchannel"] is None:
            return await ctx.send_or_reply(
                f"There is no logging channel setup. Use `{ctx.prefix}logchannel <channel name>` to set up a logging channel."
            )
        log_types = (
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
            "discord_invites",
            "server_updates",
            "emojis",
        )
        embed = discord.Embed(title="Logging Settings", color=self.bot.constants.embed)
        embed.description = "\n".join(
            [
                f"{self.bot.emote_dict['pass'] if log_bool else self.bot.emote_dict['fail']} {log_type.capitalize()}"
                for log_type, log_bool in {
                    key: self.bot.server_settings[ctx.guild.id]["logging"][key]
                    for key in log_types
                }.items()
            ]
        ).replace("_", " ")
        embed.add_field(
            name=f"Logging Channel",
            value=f"{self.bot.get_channel(self.bot.server_settings[ctx.guild.id]['logging']['logchannel']).mention}",
        )
        await ctx.send_or_reply(embed=embed)

    @decorators.command(brief="Disable specific logging events.")
    @commands.guild_only()
    @checks.bot_has_perms(embed_links=True)
    @checks.has_perms(manage_guild=True)
    async def unlog(self, ctx, *, log_arg):
        """
        Usage:      {0}unlog <option>
        Example:    {0}unlog deletes
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
            Use 'all' as an option to disable all options.
        """
        await self.log_or_unlog(ctx, log_arg, False)

    async def log_or_unlog(self, ctx, log_arg, log_bool=True):
        async with ctx.channel.typing():
            # aliases in lists (constants)
            deletes = [
                "message_deletions",
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
                "message_edits",
                "edits",
                "edit",
                "message_update",
                "message_updates",
                "message_edit",
                "changes",
            ]
            roles = [
                "role_changes",
                "roles",
                "role",
                "role_edits",
                "role_updates",
                "role_update",
                "role_change",
            ]
            names = [
                "name_updates",
                "names",
                "name",
                "name_changes",
                "nicknames",
                "nicks",
                "nickname_changes",
                "nick_changes",
            ]
            voice = [
                "voice_state_updates",
                "voice",
                "voice_updates",
                "movements",
                "voice_changes",
                "member_movement",
            ]
            avatars = [
                "avatar_changes",
                "avatars",
                "avatar",
                "pfps",
                "profilepics",
            ]
            moderation = [
                "bans",
                "moderation",
                "ban",
                "server_bans",
                "mod",
                "mod_actions",
                "actions",
            ]
            channels = [
                "channel_updates",
                "channels",
                "chan",
                "channel_edits",
                "channel_changes",
                "channel",
                "channel updates",
            ]
            leaves = ["leaves", "leave", "left"]
            joins = ["joins", "join", "joined", "member_join"]
            invites = [
                "discord_invites",
                "invites",
                "invite",
                "discord invites",
                "invite link",
                "invite links",
            ]
            server = [
                "server_updates",
                "server updates",
                "server",
                "servers",
                "server update",
            ]
            emojis = ["emojis", "emotes", "emoji"]
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
                invites,
                server,
                emojis,
                all_option,
            ]
            # finding type of log from argument using aliases
            try:
                type_of_log = [
                    log_type[0] for log_type in types_of_logs if log_arg in log_type
                ][0]
            except IndexError:
                await ctx.send_or_reply(
                    f"{self.bot.emote_dict['failed']} `{log_arg.capitalize()}` is not a valid logging option. Use `{ctx.prefix}log help` for more info."
                )
                return
            if type_of_log == "all":
                list_of_log_types = [
                    aliases[0] for aliases in types_of_logs if aliases[0] != "all"
                ]
                # first check if all logging is already enabled/disabled
                log_dict = self.bot.server_settings[ctx.guild.id]["logging"]
                current_list = [log_dict[item] for item in list_of_log_types]
                if all([item == log_bool for item in current_list]):
                    return await ctx.send_or_reply(
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
                return await ctx.send_or_reply(
                    f"{self.bot.emote_dict['success']} All logging events have been {'enabled' if log_bool else 'disabled'}."
                )

            # converts data to the names in psql so the db can be updated

            # get logging channel
            query = """
                    SELECT logchannel
                    FROM logging
                    WHERE server_id = $1;
                    """
            logchan = await self.bot.cxn.fetchval(query, ctx.guild.id) or None
            if logchan is None:
                # no existing logging channel
                return await ctx.send_or_reply(
                    f"{self.bot.emote_dict['failed']} Logging not setup on this server. "
                    f"Use `{ctx.prefix}logserver` to setup a logging channel."
                )
            logchan = ctx.guild.get_channel(int(logchan))
            # update db
            if (
                self.bot.server_settings[ctx.guild.id]["logging"][type_of_log]
                is log_bool
            ):
                return await ctx.send_or_reply(
                    f"{self.bot.emote_dict['success']} {type_of_log.replace('_', ' ').capitalize()} {'is' if type_of_log[-1] != 's' else 'are'} already {'enabled' if log_bool else 'disabled'}."
                )

            query = f"""
                    UPDATE logging
                    SET {type_of_log} = $1
                    WHERE server_id = $2;
                    """
            await self.bot.cxn.execute(query, log_bool, ctx.guild.id)
            self.bot.server_settings[ctx.guild.id]["logging"][type_of_log] = log_bool
            await ctx.send_or_reply(
                f"{self.bot.emote_dict['success']} {type_of_log.replace('_', ' ').capitalize()} will {'now be' if log_bool else 'no longer be'} logged in {logchan.mention}"
            )

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
            return await ctx.fail(f"There are no edits to snipe.")

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
