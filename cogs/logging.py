import random
import discord
import requests
import io

from discord.ext import commands
from datetime import datetime
from collections import OrderedDict

from utilities import permissions, default
from lib.bot import bot
from lib.db import asyncdb as db


def setup(bot):
    bot.add_cog(Logging(bot))


class Logging(commands.Cog):

    """
    Log your server events
    """

    def __init__(self, bot):
        self.bot = bot

        self.current_streamers = list()

      #####################
     ## Event Listeners ##
    #####################

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel):
        webhook_id = await db.record("SELECT LoggerWebhookID FROM guilds WHERE GuildID = ?", channel.guild.id) or (None)
        if webhook_id is None or "None" in str(webhook_id): 
            return

        to_log_or_not_to_log = await db.record("""
        SELECT channel_updates FROM logging WHERE server = ?
        """, channel.guild.id)
        if to_log_or_not_to_log[0] != 1: return 

        webhook_id = int(str(webhook_id).strip("(),'"))
        webhook = await self.bot.fetch_webhook(webhook_id)
        if channel.guild.id != webhook.guild.id: return

        embed = discord.Embed(description=
                                          f"**Channel:** {channel.mention} **Name:** `{channel.name}`\n"
                                          f"**Server:** `{channel.guild.name}` **ID:** `{channel.guild.id},`\n\n"
        , color=default.config()["embed_color"], timestamp=datetime.utcnow())
        embed.set_author(name="Channel Created", icon_url="https://cdn.discordapp.com/emojis/810659118045331517.png?v=1")
        embed.set_footer(text=f"Channel ID: {channel.id}")
        await webhook.execute(embed=embed, username=self.bot.user.name)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        webhook_id = await db.record("SELECT LoggerWebhookID FROM guilds WHERE GuildID = ?", channel.guild.id) or (None)
        if webhook_id is None or "None" in str(webhook_id): 
            return

        to_log_or_not_to_log = await db.record("""
        SELECT channel_updates FROM logging WHERE server = ?
        """, channel.guild.id)
        if to_log_or_not_to_log[0] != 1: return 

        webhook_id = int(str(webhook_id).strip("(),'"))
        webhook = await self.bot.fetch_webhook(webhook_id)
        if channel.guild.id != webhook.guild.id: return

        embed = discord.Embed(description=
                                          f"**Channel:** {channel.mention} **Name:** `{channel.name}`\n"
                                          f"**Server:** `{channel.guild.name}` **ID:** `{channel.guild.id},`\n\n"
        , color=default.config()["embed_color"], timestamp=datetime.utcnow())
        embed.set_author(name="Channel Deleted", icon_url="https://cdn.discordapp.com/emojis/810659118045331517.png?v=1")
        embed.set_footer(text=f"Channel ID: {channel.id}")
        await webhook.execute(embed=embed, username=self.bot.user.name)

    @commands.Cog.listener()
    async def on_guild_channel_update(self, before, after):
        webhook_id = await db.record("SELECT LoggerWebhookID FROM guilds WHERE GuildID = ?", after.guild.id) or (None)
        if webhook_id is None or "None" in str(webhook_id): 
            return

        to_log_or_not_to_log = await db.record("""
        SELECT channel_updates FROM logging WHERE server = ?
        """, before.guild.id)
        if to_log_or_not_to_log[0] != 1: return 

        webhook_id = int(str(webhook_id).strip("(),'"))
        webhook = await self.bot.fetch_webhook(webhook_id)
        if after.guild.id != webhook.guild.id: return

        if before.name != after.name:
            embed = discord.Embed(
                          description=f"**Channel:** {after.mention} **Name:** `{after}`\n"
                                      f"**Old Name:** `{before.name}`\n"
                                      f"**New Name:** `{after.name}`\n",
                          colour=default.config()["embed_color"],
                          timestamp=datetime.utcnow())
            embed.set_author(name=f"Channel Update")
            embed.set_footer(text=f"Channel ID: {after.id}")
            await webhook.execute(embed=embed, username=self.bot.user.name)

        elif before.category != after.category:
            embed = discord.Embed(
                          description=f"**Channel:** {after.mention} **Name:** `{after}`\n"
                                      f"**Old Category:** `{before.category}`\n"
                                      f"**New Category:** `{after.category}`\n",
                          colour=default.config()["embed_color"],
                          timestamp=datetime.utcnow())
            embed.set_author(name=f"Channel Update")
            embed.set_footer(text=f"Channel ID: {after.id}")
            await webhook.execute(embed=embed, username=self.bot.user.name)

        elif before.topic != after.topic:
            embed = discord.Embed(
                          description=f"**Channel:** {after.mention} **Name:** `{after}`\n"
                                      f"**Old Topic:** `{before.topic}`\n"
                                      f"**New Topic:** `{after.topic}`\n",
                          colour=default.config()["embed_color"],
                          timestamp=datetime.utcnow())
            embed.set_author(name=f"Channel Update")
            embed.set_footer(text=f"Channel ID: {after.id}")
            await webhook.execute(embed=embed, username=self.bot.user.name)

        elif before.changed_roles != after.changed_roles:
            old_overwrites = str([r.mention for r in before.changed_roles if r != after.guild.default_role]).replace("'","").replace("[","").replace("]","")
            new_overwrites = str([r.mention for r in after.changed_roles if r != after.guild.default_role]).replace("'","").replace("[","").replace("]","")
            embed = discord.Embed(
                          description=f"**Channel:** {after.mention} **Name:** `{after}`\n"
                                      f"**Old Role Overwrites:** {old_overwrites}\n"
                                      f"**New Role Overwrites:** {new_overwrites}\n",
                          colour=default.config()["embed_color"],
                          timestamp=datetime.utcnow())
            embed.set_author(name=f"Channel Update")
            embed.set_footer(text=f"Channel ID: {after.id}")
            await webhook.execute(embed=embed, username=self.bot.user.name)


    @commands.Cog.listener()
    async def on_user_update(self, before, after):
        # TODO Fix up this listener. Possibly remove altogether.
        """
        if before.name != after.name:
            to_send = []
            for guild in self.bot.guilds:

                to_log_or_not_to_log = await db.record("
                SELECT name_updates FROM logging WHERE server = ?
                ", guild.id)
                if to_log_or_not_to_log[0] != 1: return 

                for member in guild.members:
                    if member.id != before.id:
                        continue
                    to_send.append(guild.id)
            if to_send:
                for i in to_send:
                    webhook_id = await db.record("SELECT LoggerWebhookID FROM guilds WHERE GuildID = ?", i) or (None)
                    if webhook_id is None or "None" in str(webhook_id): 
                        continue
                    webhook_id = int(str(webhook_id).strip("(),'"))
                    webhook = await self.bot.fetch_webhook(webhook_id)
                embed = discord.Embed(
                              description=f"**User:** {after.mention} **Name:** `{after}`\n"
                                          f"**Old Username:** `{before.name}`\n"
                                          f"**New Username:** `{after.name}`\n",
                              colour=default.config()["embed_color"],
                              timestamp=datetime.utcnow())
                embed.set_author(name=f"Username Change")
                embed.set_footer(text=f"User ID: {after.id}")

                await webhook.execute(embed=embed, username=self.bot.user.name)

        if before.discriminator != after.discriminator:
            to_send = []
            for guild in self.bot.guilds:

                to_log_or_not_to_log = await db.record("
                SELECT name_updates FROM logging WHERE server = ?
                ", guild.id)
                if to_log_or_not_to_log[0] != 1: return 

                for member in guild.members:
                    if member.id != before.id: 
                        continue
                    to_send.append(guild.id)
            if to_send:
                for i in to_send:
                    webhook_id = await db.record("SELECT LoggerWebhookID FROM guilds WHERE GuildID = ?", i) or (None)
                    if webhook_id is None or "None" in str(webhook_id): 
                        continue

                    webhook_id = int(str(webhook_id).strip("(),'"))
                    webhook = await self.bot.fetch_webhook(webhook_id)
                embed = discord.Embed(
                              description=f"**User:** {after.mention} **Name:** `{after}`\n"
                                          f"**Old Discriminator:** `{before.discriminator}`\n"
                                          f"**New Discriminator:** `{after.discriminator}`\n",
                              colour=default.config()["embed_color"],
                              timestamp=datetime.utcnow())
                embed.set_author(name=f"Discriminator Change")
                embed.set_footer(text=f"User ID: {after.id}")

            await webhook.execute(embed=embed, username=self.bot.user.name)
        
        if before.avatar_url != after.avatar_url:
            to_send = []
            send = []
            for guild in self.bot.guilds:
                for member in guild.members:
                    if member.id == before.id: 
                        to_send.append(guild.id)
                        break
                    break
                
            

                to_log_or_not_to_log = await db.record("
                SELECT avatar_changes FROM logging WHERE server = ?
                ", guild.id)
                if to_log_or_not_to_log[0] == 1:
                    send.append(guild.id) 

            if to_send and send:
                for i in to_send:
                    webhook_id = await db.record("SELECT LoggerWebhookID FROM guilds WHERE GuildID = ?", i) or (None)
                    if webhook_id is None or "None" in str(webhook_id): 
                        continue
                    webhook_id = int(str(webhook_id).strip("(),'"))
                    webhook = await self.bot.fetch_webhook(webhook_id)
                embed = discord.Embed(
                              description=f"**User:** {after.mention} **Name:** `{after}`\n"
                                          "New image below, old image to the right.",
                              colour=default.config()["embed_color"],
                              timestamp=datetime.utcnow())
    
                embed.set_thumbnail(url=before.avatar_url)
                embed.set_image(url=after.avatar_url)
                embed.set_author(name=f"Avatar Change")
                embed.set_footer(text=f"User ID: {after.id}")
                await webhook.execute(embed=embed, username=self.bot.user.name)
        """

    @commands.Cog.listener()
    async def on_member_unban(self, member):
        webhook_id = await db.record("SELECT LoggerWebhookID FROM guilds WHERE GuildID = ?", member.guild.id) or (None)
        if webhook_id is None or "None" in str(webhook_id): 
            return

        to_log_or_not_to_log = await db.record("""
        SELECT bans FROM logging WHERE server = ?
        """, member.guild.id)
        if to_log_or_not_to_log[0] != 1: return 

        webhook_id = int(str(webhook_id).strip("(),'"))
        webhook = await self.bot.fetch_webhook(webhook_id)
        if member.guild.id != webhook.guild.id: return

        embed = discord.Embed(
                      description=f"**User:** {member.mention} **Name:** `{member}`\n",
                      colour=default.config()["embed_color"],
                      timestamp=datetime.utcnow())
        embed.set_author(name=f"User Unbanned")
        embed.set_footer(text=f"User ID: {member.id}")
        await webhook.execute(embed=embed, username=self.bot.user.name)


    @commands.Cog.listener()
    async def on_member_ban(self, member):
        webhook_id = await db.record("SELECT LoggerWebhookID FROM guilds WHERE GuildID = ?", member.guild.id) or (None)
        if webhook_id is None or "None" in str(webhook_id): 
            return

        to_log_or_not_to_log = await db.record("""
        SELECT bans FROM logging WHERE server = ?
        """, member.guild.id)
        if to_log_or_not_to_log[0] != 1: return 

        webhook_id = int(str(webhook_id).strip("(),'"))
        webhook = await self.bot.fetch_webhook(webhook_id)
        if member.guild.id != webhook.guild.id: return

        embed = discord.Embed(
                      description=f"**User:** {member.mention} **Name:** `{member}`\n",
                      colour=default.config()["embed_color"],
                      timestamp=datetime.utcnow())
        embed.set_author(name=f"User Banned")
        embed.set_footer(text=f"User ID: {member.id}")
        await webhook.execute(embed=embed, username=self.bot.user.name)

    @commands.Cog.listener()
    async def on_member_join(self, member):
        webhook_id = await db.record("SELECT LoggerWebhookID FROM guilds WHERE GuildID = ?", member.guild.id) or (None)
        if webhook_id is None or "None" in str(webhook_id): 
            return

        to_log_or_not_to_log = await db.record("""
        SELECT joins FROM logging WHERE server = ?
        """, member.guild.id)
        if to_log_or_not_to_log[0] != 1: return 

        webhook_id = int(str(webhook_id).strip("(),'"))
        webhook = await self.bot.fetch_webhook(webhook_id)
        if member.guild.id != webhook.guild.id: return

        embed = discord.Embed(
                      description=f"**User:** {member.mention} **Name:** `{member}`\n",
                      colour=default.config()["embed_color"],
                      timestamp=datetime.utcnow())
        embed.set_author(name=f"User Joined")
        embed.set_footer(text=f"User ID: {member.id}")
        await webhook.execute(embed=embed, username=self.bot.user.name)


    @commands.Cog.listener()
    async def on_member_remove(self, member):
        webhook_id = await db.record("SELECT LoggerWebhookID FROM guilds WHERE GuildID = ?", member.guild.id) or (None)
        if webhook_id is None or "None" in str(webhook_id): 
            return

        to_log_or_not_to_log = await db.record("""
        SELECT leaves FROM logging WHERE server = ?
        """, member.guild.id)
        if to_log_or_not_to_log[0] != 1: return 

        webhook_id = int(str(webhook_id).strip("(),'"))
        webhook = await self.bot.fetch_webhook(webhook_id)
        if member.guild.id != webhook.guild.id: return

        embed = discord.Embed(
                      description=f"**User:** {member.mention} **Name:** `{member}`\n",
                      colour=default.config()["embed_color"],
                      timestamp=datetime.utcnow())
        embed.set_author(name=f"User Left")
        embed.set_footer(text=f"User ID: {member.id}")
        await webhook.execute(embed=embed, username=self.bot.user.name)


    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        if before is None:
            return
        webhook_id = await db.record("SELECT LoggerWebhookID FROM guilds WHERE GuildID = ?", after.guild.id) or (None)
        if webhook_id is None or "None" in str(webhook_id): 
            return
        webhook_id = int(str(webhook_id).strip("(),'"))
        webhook = await self.bot.fetch_webhook(webhook_id)
        if after.guild.id != webhook.guild.id: return

        if before.display_name != after.display_name:

            to_log_or_not_to_log = await db.record("""
            SELECT name_updates FROM logging WHERE server = ?
            """, before.guild.id)
            if to_log_or_not_to_log[0] != 1: return 

            embed = discord.Embed(
                          description=f"**User:** {after.mention} **Name:** `{after}`\n"
                                      f"**Old Nickname:** `{before.display_name}`\n"
                                      f"**New Nickname:** `{after.display_name}`\n",
                          colour=default.config()["embed_color"],
                          timestamp=datetime.utcnow())
            embed.set_author(name=f"Nickname Change")
            embed.set_footer(text=f"User ID: {after.id}")

            await webhook.execute(embed=embed, username=self.bot.user.name)

            name_list = await db.record('''SELECT nicknames
                              FROM users
                              WHERE (server=? AND id=?)''',
                           str(before.guild.id), before.id)

            name_list = name_list[0].split(',')
            name_list = list(OrderedDict.fromkeys(name_list))

            if after.display_name not in name_list:
                name_list.append(after.display_name)
            else:

                old_index = name_list.index(after.display_name)
                name_list.pop(old_index)
                name_list.append(after.display_name)
            new_names = ','.join(name_list)
            await db.execute('''UPDATE users
                              SET nicknames=?
                              WHERE (id=? AND server=?)''',
                           new_names, before.id, before.guild.id)

        elif before.roles != after.roles:

            to_log_or_not_to_log = await db.record("""
            SELECT role_changes FROM logging WHERE server = ?
            """, before.guild.id)
            if to_log_or_not_to_log[0] != 1: return 
            
            embed = discord.Embed(
                          description=f"**User:** {after.mention} **Name:** `{after}`\n"
                                      f"**Old Roles:** {', '.join([r.mention for r in before.roles if r != after.guild.default_role])}\n"
                                      f"**New Roles:** {', '.join([r.mention for r in after.roles if r != after.guild.default_role])}\n",
                          colour=default.config()["embed_color"],
                          timestamp=datetime.utcnow())
            embed.set_author(name=f"Role Updates")
            embed.set_footer(text=f"User ID: {after.id}")

            await webhook.execute(embed=embed, username=self.bot.user.name)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if before is None:
            return
        webhook_id = await db.record("SELECT LoggerWebhookID FROM guilds WHERE GuildID = ?", member.guild.id) or (None)
        if webhook_id is None or "None" in str(webhook_id): 
            return
        to_log_or_not_to_log = await db.record("""
        SELECT voice_state_updates FROM logging WHERE server = ?
        """, member.guild.id)
        if to_log_or_not_to_log[0] != 1: return 

        webhook_id = int(str(webhook_id).strip("(),'"))
        webhook = await self.bot.fetch_webhook(webhook_id)
        if member.guild.id != webhook.guild.id: return

        if not before.channel:

            embed = discord.Embed(
                          description=f"**User:** {member.mention} **Name:** `{member}`\n",
                          colour=default.config()["embed_color"],
                          timestamp=datetime.utcnow())
            embed.set_author(name=f"Member Joined {after.channel.name}")
            embed.set_footer(text=f"User ID: {member.id}")

            await webhook.execute(embed=embed, username=self.bot.user.name)

        if before.channel and not after.channel:
            
            embed = discord.Embed(
                          description=f"**User:** {member.mention} **Name:** `{member}`\n",
                          colour=default.config()["embed_color"],
                          timestamp=datetime.utcnow())
            embed.set_author(name=f"Membed Left Channel {before.channel.name}")
            embed.set_footer(text=f"User ID: {member.id}")

            await webhook.execute(embed=embed, username=self.bot.user.name)

        if before.channel and after.channel:
            if before.channel.id != after.channel.id:
                embed = discord.Embed(
                              description=f"**User:** {member.mention} **Name:** `{member}`\n"
                                          f"**Old Channel:** {before.channel.mention} **ID:** `{before.channel.id}`\n"
                                          f"**New Channel:** {after.channel.mention} **ID:** `{after.channel.id}`\n",
                              colour=default.config()["embed_color"],
                              timestamp=datetime.utcnow())
                embed.set_author(name=f"User Switched Voice Channels")
                embed.set_footer(text=f"User ID: {member.id}")
                
                await webhook.execute(embed=embed, username=self.bot.user.name)
            else:
                if member.voice.self_stream:
                    embed = discord.Embed(
                                  description=f"**User:** {member.mention} **Name:** `{member}`\n"
                                              f"**Channel:** {after.channel.mention} **ID:** `{after.channel.id}`\n",
                                  colour=default.config()["embed_color"],
                                  timestamp=datetime.utcnow())
                    embed.set_author(name=f"User Started Streaming")
                    embed.set_footer(text=f"User ID: {member.id}")

                    await webhook.execute(embed=embed, username=self.bot.user.name)

                    self.current_streamers.append(member.id)

                elif member.voice.self_mute:
                    embed = discord.Embed(
                                  description=f"**User:** {member.mention} **Name:** `{member}`\n"
                                              f"**Channel:** {after.channel.mention} **ID:** `{after.channel.id}`\n",
                                  colour=default.config()["embed_color"],
                                  timestamp=datetime.utcnow())
                    embed.set_author(name=f"User Muted")
                    embed.set_footer(text=f"User ID: {member.id}")

                    await webhook.execute(embed=embed, username=self.bot.user.name)

                elif member.voice.self_deaf:
                    embed = discord.Embed(
                                  description=f"**User:** {member.mention} **Name:** `{member}`\n"
                                              f"**Channel:** {after.channel.mention} **ID:** `{after.channel.id}`\n",
                                  colour=default.config()["embed_color"],
                                  timestamp=datetime.utcnow())
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
                                              colour=default.config()["embed_color"],
                                              timestamp=datetime.utcnow())
                                embed.set_author(name=f"User Stopped Streaming")
                                embed.set_footer(text=f"User ID: {member.id}")

                                await webhook.execute(embed=embed, username=self.bot.user.name)
                                self.current_streamers.remove(member.id)
                            break


    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        if before.author.bot: return
        webhook_id = await db.record("SELECT LoggerWebhookID FROM guilds WHERE GuildID = ?", after.guild.id) or (None)
        if webhook_id is None or "None" in str(webhook_id): 
            return

        to_log_or_not_to_log = await db.record("""
        SELECT message_edits FROM logging WHERE server = ?
        """, before.guild.id)
        if to_log_or_not_to_log[0] != 1: return 

        webhook_id = int(str(webhook_id).strip("(),'"))
        webhook = await self.bot.fetch_webhook(webhook_id)
        if after.guild.id != webhook.guild.id: return

        embed = discord.Embed(description=f"**Author:**  {after.author.mention}, **ID:** `{after.author.id}`\n"
                                          f"**Channel:** {after.channel.mention} **ID:** `{after.channel.id}`\n"
                                          f"**Server:** `{after.guild.name}` **ID:** `{after.guild.id},`\n\n"
                                          f"**__Old Message Content__**\n ```fix\n{before.content}```\n"
                                          f"**__New Message Content__**\n ```fix\n{after.content}```\n"
                                          f"**[Jump to message](https://discord.com/channels/{after.guild.id}/{after.channel.id}/{after.id})**"
        , color=default.config()["embed_color"], timestamp=datetime.utcnow())
        embed.set_author(name="Message Edited", icon_url="https://media.discordapp.net/attachments/506838906872922145/603643138854354944/messageupdate.png")
        embed.set_footer(text=f"Message ID: {after.id}")
        await webhook.execute(embed=embed, username=self.bot.user.name)


    @commands.Cog.listener()
    async def on_message_delete(self, message):

        if not message.guild: return
        await db.execute("""
        INSERT OR REPLACE INTO snipe VALUES (?, ?, ?, ?, ?, ?)
        """, message.channel.id, message.guild.id, message.author.id, message.id, str(message.content), message.created_at.strftime('%Y-%m-%d %H:%M:%S'))

        webhook_id = await db.record("SELECT LoggerWebhookID FROM guilds WHERE GuildID = ?", message.guild.id) or (None)
        if webhook_id is None or "None" in str(webhook_id): return

        to_log_or_not_to_log = await db.record("""
        SELECT message_deletions FROM logging WHERE server = ?
        """, message.guild.id)
        if to_log_or_not_to_log[0] != 1: return 

        webhook_id = int(str(webhook_id).strip("(),'"))
        webhook = await self.bot.fetch_webhook(webhook_id)
        if message.guild.id != webhook.guild.id: return

        if message.content.startswith("```"):
            content = f"**__Message Content__**\n {message.content}"
        else:
            content = f"**__Message Content__**\n ```fix\n{message.content}```"

        embed = discord.Embed(description=f"**Author:**  {message.author.mention}, **ID:** `{message.author.id}`\n"
                                          f"**Channel:** {message.channel.mention} **ID:** `{message.channel.id}`\n"
                                          f"**Server:** `{message.guild.name}` **ID:** `{message.guild.id},`\n\n"
                                          f"{content}"
        , color=default.config()["embed_color"], timestamp=datetime.utcnow())
        embed.set_author(name="Message Deleted", icon_url="https://media.discordapp.net/attachments/506838906872922145/603642595419357190/messagedelete.png")
        embed.set_footer(text=f"Message ID: {message.id}")
        await webhook.execute(embed=embed, username=self.bot.user.name)

    
    @commands.Cog.listener()
    async def on_bulk_message_delete(self, messages):
        guild_obj = random.choice(messages).guild
        webhook_id = await db.record("SELECT LoggerWebhookID FROM guilds WHERE GuildID = ?", guild_obj.id) or (None)
        if webhook_id is None or "None" in str(webhook_id): 
            return

        to_log_or_not_to_log = await db.record("""
        SELECT message_deletions FROM logging WHERE server = ?
        """, messages[0].guild.id)
        if to_log_or_not_to_log[0] != 1: return 

        webhook_id = int(str(webhook_id).strip("(),'"))
        webhook = await self.bot.fetch_webhook(webhook_id)
        if guild_obj.id != webhook.guild.id: return

        allmessages = ""

        for message in messages:
            allmessages += f"Content: {message.content}          Author: {message.author}          ID: {message.id}\n\n"

        embed = discord.Embed(
        description=
                    f"**Channel:** {message.channel.mention} **ID:** `{message.channel.id}`\n"
                    f"**Server:** `{message.guild.name}` **ID:** `{message.guild.id},`\n\n",
        color=default.config()["embed_color"], 
        timestamp=datetime.utcnow())
        embed.set_author(name="Bulk Message Delete", icon_url="https://media.discordapp.net/attachments/506838906872922145/603642595419357190/messagedelete.png")

        await webhook.execute(embed=embed, username=self.bot.user.name)

        counter = 0
        msg = ''
        for message in messages:
            counter += 1
            msg += message.content + "\n"
            msg += '----Sent-By: ' + message.author.name + '#' + message.author.discriminator + "\n"
            msg += '---------At: ' + message.created_at.strftime("%Y-%m-%d %H.%M") + "\n"
            if message.edited_at:
                msg += '--Edited-At: ' + message.edited_at.strftime("%Y-%m-%d %H.%M") + "\n"
            msg += '\n'

        data = io.BytesIO(msg[:-2].encode("utf-8"))

        await webhook.execute(file=discord.File(data, filename=f"'Bulk-Deleted-Messages-{datetime.now().__format__('%m-%d-%Y')}.txt"))

      ##############
     ## Commands ##
    ##############

    @commands.command(brief="Snipe a deleted message.", aliases=['retrieve'])
    @commands.guild_only()
    async def snipe(self, ctx):

        author, message_id, content, timestamp = await db.record("""
        SELECT author, message_id, content, timestamp FROM snipe WHERE channel = ? 
        """, ctx.channel.id) or (None, None, None, None)
        if "None" in str(author): return await ctx.send(f":warning: There is nothing to snipe.")

        author = await self.bot.fetch_user(author)
        content = str(content).strip("(),'")
        timestamp = str(timestamp).strip("(),'")

        if str(content).startswith("```"):
            content = f"**__Message Content__**\n {str(content)}"
        else:
            content = f"**__Message Content__**\n ```fix\n{str(content)}```"

        embed = discord.Embed(description=f"**Author:**  {author.mention}, **ID:** `{author.id}`\n"
                                          f"**Channel:** {ctx.channel.mention} **ID:** `{ctx.channel.id}`\n"
                                          f"**Server:** `{ctx.guild.name}` **ID:** `{ctx.guild.id},`\n\n"
                                          f"**Sent at:** `{timestamp}`\n\n"
                                          f"{content}"
        , color=default.config()["embed_color"], timestamp=datetime.utcnow())
        embed.set_author(name="Deleted Message Retrieved", icon_url="https://media.discordapp.net/attachments/506838906872922145/603642595419357190/messagedelete.png")
        embed.set_footer(text=f"Message ID: {message_id}")
        await ctx.send(embed=embed)


    @commands.command(pass_context=True, aliases=['dumpmessages','messagedump'], brief="Logs a passed number of messages from the given channel - 25 by default.")
    @commands.guild_only()
    @permissions.has_permissions(manage_server=True)
    async def logmessages(self, ctx, messages : int = 25, *, chan : discord.TextChannel = None):
        """
        Usage:      -logmessages [message amount] [channel]
        Aliases:    -messagedump, dumpmessages
        Permission: Manage Server
        Output: 
                    Logs a passed number of messages from the given channel 
                    - 25 by default.
        """

        timeStamp = datetime.today().strftime("%Y-%m-%d %H.%M")
        logFile = 'Logs-{}.txt'.format(timeStamp)

        if not chan:
            chan = ctx

        mess = await ctx.send('Saving logs to **{}**...'.format(logFile))

        # Use logs_from instead of purge
        counter = 0
        msg = ''
        async for message in chan.history(limit=messages):
            counter += 1
            msg += message.content + "\n"
            msg += '----Sent-By: ' + message.author.name + '#' + message.author.discriminator + "\n"
            msg += '---------At: ' + message.created_at.strftime("%Y-%m-%d %H.%M") + "\n"
            if message.edited_at:
                msg += '--Edited-At: ' + message.edited_at.strftime("%Y-%m-%d %H.%M") + "\n"
            msg += '\n'

        data = io.BytesIO(msg[:-2].encode("utf-8"))
        
        await mess.edit(content='Uploading `{}`...'.format(logFile))
        await ctx.author.send(file=discord.File(data, filename=logFile))
        await mess.edit(content='<:ballot_box_with_check:805871188462010398> Uploaded `{}`.'.format(logFile))



    @commands.command(brief="Set your server's log channel.",aliases=['logserver'])
    @commands.guild_only()
    @permissions.has_permissions(manage_guild=True)
    async def logchannel(self, ctx, channel: discord.TextChannel = None):

        if channel is None:
            channel = ctx.channel
        server_webhook_list = await ctx.guild.webhooks()
        for webhook in server_webhook_list:
            if webhook.name == str(self.bot.user.id):
                return await ctx.send(":warning: Logging is already set up on this server")

        response = requests.get(ctx.guild.me.avatar_url)
        avatar = response.content
        webhook = await channel.create_webhook(name=self.bot.user.id, avatar=avatar, reason="Webhook created for server logging.")
        await db.execute("UPDATE guilds SET LoggerWebhookID = ? WHERE GuildID = ?", webhook.id, ctx.guild.id)
        await db.execute("UPDATE logging SET logchannel = ? WHERE server = ?", channel.id, ctx.guild.id)
        await ctx.send(f"<:ballot_box_with_check:805871188462010398> Set channel {channel.mention} as this server's logging channel.")
        await webhook.execute(content="Hello! I'm going to be logging your server's events in this channel from now on. "
                                      f"Use `{ctx.prefix}log <option>` to set the specific events you want documented here. "
                                      "By default, all events will be logged.",
                              username=self.bot.user.name)


    @commands.command(brief="Remove your server's log channel.",aliases=['unlogserver'])
    @commands.guild_only()
    @permissions.has_permissions(manage_guild=True)
    async def unlogchannel(self, ctx):
        server_webhook_list = await ctx.guild.webhooks()
        found = []
        for webhook in server_webhook_list:
            if webhook.name == str(self.bot.user.id):
                found.append(webhook.name)
        if found:
            await webhook.delete(reason=f"Logging webhook deleted by {ctx.author}.")
            await db.execute("UPDATE guilds SET LoggerWebhookID = NULL WHERE GuildID = ?", ctx.guild.id)
            await db.execute("UPDATE logging SET logchannel = NULL WHERE server = ?", ctx.guild.id)
            await ctx.send("<:ballot_box_with_check:805871188462010398> Logging is now disabled on this server")
            return
        else:
            return await ctx.send(f":warning: Logging is not enabled on this server.")

    @commands.group(brief="Customize your server's logging by enabling specific logging events")
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


    @log.command(name="deletes", brief="Log all message deletions", aliases=['deletions','messages','message','deleted_messages','message_delete','message_deletes','delete_messages'])
    async def _deletes(self, ctx):
        logchan = await db.record("""
        SELECT logchannel FROM logging WHERE server = ?
        """, str(ctx.guild.id)) or None
        if logchan is None or logchan[0] is None: 
            return await ctx.send(f"<:fail:812062765028081674> Logging not setup on this server. Use `{ctx.prefix}logserver` to setup a logging channel.")

        logchan = ctx.guild.get_channel(int(logchan[0]))

        await db.execute("""
        UPDATE logging SET message_deletion = ? WHERE server = ?
        """, True, ctx.guild.id)
        await ctx.send(f"<:ballot_box_with_check:805871188462010398> Message deletions will now be logged in {logchan.mention}")


    @log.command(name="edits", brief="Log all message edits", aliases=['edit','message_update','message_updates','message_edits','message_edit','changes'])
    async def _edits(self, ctx):
        logchan = await db.record("""
        SELECT logchannel FROM logging WHERE server = ?
        """, str(ctx.guild.id)) or None
        if logchan is None or logchan[0] is None: 
            return await ctx.send(f"<:fail:812062765028081674> Logging not setup on this server. Use `{ctx.prefix}logchannel` to setup a logging channel.")

        logchan = ctx.guild.get_channel(int(logchan[0]))

        await db.execute("""
        UPDATE logging SET message_edit = ? WHERE server = ?
        """, True, ctx.guild.id)
        await ctx.send(f"<:ballot_box_with_check:805871188462010398> Message edits will now be logged in {logchan.mention}")


    @log.command(name="roles", brief="Log all role changes", aliases=['role','role_edits','role_updates','role_update','role_changes','role_change'])
    async def _roles(self, ctx):
        logchan = await db.record("""
        SELECT logchannel FROM logging WHERE server = ?
        """, str(ctx.guild.id)) or None
        if logchan is None or logchan[0] is None: 
            return await ctx.send(f"<:fail:812062765028081674> Logging not setup on this server. Use `{ctx.prefix}logchannel` to setup a logging channel.")

        logchan = ctx.guild.get_channel(int(logchan[0]))

        await db.execute("""
        UPDATE logging SET role_changes = ? WHERE server = ?
        """, True, ctx.guild.id)
        await ctx.send(f"<:ballot_box_with_check:805871188462010398> Role changes will now be logged in {logchan.mention}")


    @log.command(name="names", brief="Log all role changes", aliases=['name','name_changes','nicknames','nicks','nickname_changes','nick_changes'])
    async def _names(self, ctx):
        logchan = await db.record("""
        SELECT logchannel FROM logging WHERE server = ?
        """, str(ctx.guild.id)) or None
        if logchan is None or logchan[0] is None: 
            return await ctx.send(f"<:fail:812062765028081674> Logging not setup on this server. Use `{ctx.prefix}logchannel` to setup a logging channel.")

        logchan = ctx.guild.get_channel(int(logchan[0]))

        await db.execute("""
        UPDATE logging SET name_updates = ? WHERE server = ?
        """, True, ctx.guild.id)
        await ctx.send(f"<:ballot_box_with_check:805871188462010398> Name changes will now be logged in {logchan.mention}")


    @log.command(name="voice", brief="Log all member movements", aliases=['voice_updates','movements','voice_changes','member_movement'])
    async def _voice(self, ctx):
        logchan = await db.record("""
        SELECT logchannel FROM logging WHERE server = ?
        """, str(ctx.guild.id)) or None
        if logchan is None or logchan[0] is None: 
            return await ctx.send(f"<:fail:812062765028081674> Logging not setup on this server. Use `{ctx.prefix}logchannel` to setup a logging channel.")

        logchan = ctx.guild.get_channel(int(logchan[0]))

        await db.execute("""
        UPDATE logging SET voice_state_updates = ? WHERE server = ?
        """, True, ctx.guild.id)
        await ctx.send(f"<:ballot_box_with_check:805871188462010398> Voice state updates will now be logged in {logchan.mention}")


    @log.command(name="avatars", brief="Log all avatar changes", aliases=['avatar','pfps','profilepics','avatar_changes'])
    async def _avatars(self, ctx):
        logchan = await db.record("""
        SELECT logchannel FROM logging WHERE server = ?
        """, str(ctx.guild.id)) or None
        if logchan is None or logchan[0] is None: 
            return await ctx.send(f"<:fail:812062765028081674> Logging not setup on this server. Use `{ctx.prefix}logchannel` to setup a logging channel.")

        logchan = ctx.guild.get_channel(int(logchan[0]))

        await db.execute("""
        UPDATE logging SET avatar_changes = ? WHERE server = ?
        """, True, ctx.guild.id)
        await ctx.send(f"<:ballot_box_with_check:805871188462010398> Avatar changes will now be logged in {logchan.mention}")


    @log.command(name="bans", brief="Log all server bans", aliases=['ban','server_bans'])
    async def _bans(self, ctx):
        logchan = await db.record("""
        SELECT logchannel FROM logging WHERE server = ?
        """, str(ctx.guild.id)) or None
        if logchan is None or logchan[0] is None: 
            return await ctx.send(f"<:fail:812062765028081674> Logging not setup on this server. Use `{ctx.prefix}logchannel` to setup a logging channel.")

        logchan = ctx.guild.get_channel(int(logchan[0]))

        await db.execute("""
        UPDATE logging SET bans = ? WHERE server = ?
        """, True, ctx.guild.id)
        await ctx.send(f"<:ballot_box_with_check:805871188462010398> Server bans will now be logged in {logchan.mention}")


    @log.command(name="channels", brief="Log all server bans", aliases=['chan','channel_updates','channel_edits','channel_changes'])
    async def _channels(self, ctx):
        logchan = await db.record("""
        SELECT logchannel FROM logging WHERE server = ?
        """, str(ctx.guild.id)) or None
        if logchan is None or logchan[0] is None: 
            return await ctx.send(f"<:fail:812062765028081674> Logging not setup on this server. Use `{ctx.prefix}logchannel` to setup a logging channel.")

        logchan = ctx.guild.get_channel(int(logchan[0]))

        await db.execute("""
        UPDATE logging SET bans = ? WHERE server = ?
        """, True, ctx.guild.id)
        await ctx.send(f"<:ballot_box_with_check:805871188462010398> Channel updates will now be logged in {logchan.mention}")


    @log.command(name="leaves", brief="Log all server bans", aliases=['leave','left'])
    async def _leaves(self, ctx):
        logchan = await db.record("""
        SELECT logchannel FROM logging WHERE server = ?
        """, str(ctx.guild.id)) or None
        if logchan is None or logchan[0] is None: 
            return await ctx.send(f"<:fail:812062765028081674> Logging not setup on this server. Use `{ctx.prefix}logchannel` to setup a logging channel.")

        logchan = ctx.guild.get_channel(int(logchan[0]))

        await db.execute("""
        UPDATE logging SET leaves = ? WHERE server = ?
        """, True, ctx.guild.id)
        await ctx.send(f"<:ballot_box_with_check:805871188462010398> Member leave will now be logged in {logchan.mention}")


    @log.command(name="joins", brief="Log all server bans", aliases=['join','joined','member_join'])
    async def _joins(self, ctx):
        logchan = await db.record("""
        SELECT logchannel FROM logging WHERE server = ?
        """, str(ctx.guild.id)) or None
        if logchan is None or logchan[0] is None: 
            return await ctx.send(f"<:fail:812062765028081674> Logging not setup on this server. Use `{ctx.prefix}logchannel` to setup a logging channel.")

        logchan = ctx.guild.get_channel(int(logchan[0]))

        await db.execute("""
        UPDATE logging SET joins = ? WHERE server = ?
        """, True, ctx.guild.id)
        await ctx.send(f"<:ballot_box_with_check:805871188462010398> Membed join will now be logged in {logchan.mention}")


    @commands.group(brief="Customize your server's logging by disabling specific logging events")
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


    @unlog.command(name="deletes", brief="Log all message deletions", aliases=['deletions','messages','message','deleted_messages','message_delete','message_deletes','delete_messages'])
    async def deletes_(self, ctx):
        logchan = await db.record("""
        SELECT logchannel FROM logging WHERE server = ?
        """, str(ctx.guild.id)) or None
        if logchan is None or logchan[0] is None: 
            return await ctx.send(f"<:fail:812062765028081674> Logging not setup on this server. Use `{ctx.prefix}logserver` to setup a logging channel.")

        logchan = ctx.guild.get_channel(int(logchan[0]))

        await db.execute("""
        UPDATE logging SET message_deletion = ? WHERE server = ?
        """, False, ctx.guild.id)
        await ctx.send(f"<:ballot_box_with_check:805871188462010398> Message deletions will now be logged in {logchan.mention}")


    @unlog.command(name="edits", brief="Log all message edits", aliases=['edit','message_update','message_updates','message_edits','message_edit','changes'])
    async def edits_(self, ctx):
        logchan = await db.record("""
        SELECT logchannel FROM logging WHERE server = ?
        """, str(ctx.guild.id)) or None
        if logchan is None or logchan[0] is None: 
            return await ctx.send(f"<:fail:812062765028081674> Logging not setup on this server. Use `{ctx.prefix}logchannel` to setup a logging channel.")

        logchan = ctx.guild.get_channel(int(logchan[0]))

        await db.execute("""
        UPDATE logging SET message_edit = ? WHERE server = ?
        """, False, ctx.guild.id)
        await ctx.send(f"<:ballot_box_with_check:805871188462010398> Message edits will now be logged in {logchan.mention}")


    @unlog.command(name="roles", brief="Log all role changes", aliases=['role','role_edits','role_updates','role_update','role_changes','role_change'])
    async def roles_(self, ctx):
        logchan = await db.record("""
        SELECT logchannel FROM logging WHERE server = ?
        """, str(ctx.guild.id)) or None
        if logchan is None or logchan[0] is None: 
            return await ctx.send(f"<:fail:812062765028081674> Logging not setup on this server. Use `{ctx.prefix}logchannel` to setup a logging channel.")

        logchan = ctx.guild.get_channel(int(logchan[0]))

        await db.execute("""
        UPDATE logging SET role_changes = ? WHERE server = ?
        """, False, ctx.guild.id)
        await ctx.send(f"<:ballot_box_with_check:805871188462010398> Role changes will now be logged in {logchan.mention}")


    @unlog.command(name="names", brief="Log all role changes", aliases=['name','name_changes','nicknames','nicks','nickname_changes','nick_changes'])
    async def names_(self, ctx):
        logchan = await db.record("""
        SELECT logchannel FROM logging WHERE server = ?
        """, str(ctx.guild.id)) or None
        if logchan is None or logchan[0] is None: 
            return await ctx.send(f"<:fail:812062765028081674> Logging not setup on this server. Use `{ctx.prefix}logchannel` to setup a logging channel.")

        logchan = ctx.guild.get_channel(int(logchan[0]))

        await db.execute("""
        UPDATE logging SET name_updates = ? WHERE server = ?
        """, False, ctx.guild.id)
        await ctx.send(f"<:ballot_box_with_check:805871188462010398> Name changes will now be logged in {logchan.mention}")


    @unlog.command(name="voice", brief="Log all member movements", aliases=['movement','voice_state','voice_changes','member_movement'])
    async def voice_(self, ctx):
        logchan = await db.record("""
        SELECT logchannel FROM logging WHERE server = ?
        """, str(ctx.guild.id)) or None
        if logchan is None or logchan[0] is None: 
            return await ctx.send(f"<:fail:812062765028081674> Logging not setup on this server. Use `{ctx.prefix}logchannel` to setup a logging channel.")

        logchan = ctx.guild.get_channel(int(logchan[0]))

        await db.execute("""
        UPDATE logging SET voice_state_updates = ? WHERE server = ?
        """, False, ctx.guild.id)
        await ctx.send(f"<:ballot_box_with_check:805871188462010398> Voice state updates will no longer be logged in {logchan.mention}")


    @unlog.command(name="avatar", brief="Unlog all avatar changes", aliases=['avatars','avatar_changes','pfps','profilepics','pfp_changes','profilepic_changes','avatar_updates'])
    async def avatar_(self, ctx):
        logchan = await db.record("""
        SELECT logchannel FROM logging WHERE server = ?
        """, str(ctx.guild.id)) or None
        if logchan is None or logchan[0] is None: 
            return await ctx.send(f"<:fail:812062765028081674> Logging not setup on this server. Use `{ctx.prefix}logchannel` to setup a logging channel.")

        logchan = ctx.guild.get_channel(int(logchan[0]))

        await db.execute("""
        UPDATE logging SET avatar_changes = ? WHERE server = ?
        """, False, ctx.guild.id)
        await ctx.send(f"<:ballot_box_with_check:805871188462010398> Avatar changes will no longer be logged in {logchan.mention}")


    @unlog.command(name="bans", brief="Unlog all server bans", aliases=['banned','member_remove','banning','banish'])
    async def bans_(self, ctx):
        logchan = await db.record("""
        SELECT logchannel FROM logging WHERE server = ?
        """, str(ctx.guild.id)) or None
        if logchan is None or logchan[0] is None: 
            return await ctx.send(f"<:fail:812062765028081674> Logging not setup on this server. Use `{ctx.prefix}logchannel` to setup a logging channel.")

        logchan = ctx.guild.get_channel(int(logchan[0]))

        await db.execute("""
        UPDATE logging SET bans = ? WHERE server = ?
        """, False, ctx.guild.id)
        await ctx.send(f"<:ballot_box_with_check:805871188462010398> Server bans will now be logged in {logchan.mention}")


    @unlog.command(name="channels", brief="Unlog all channel updates", aliases=['channel','channel_updates','channel_changes'])
    async def channels_(self, ctx):
        logchan = await db.record("""
        SELECT logchannel FROM logging WHERE server = ?
        """, str(ctx.guild.id)) or None
        if logchan is None or logchan[0] is None: 
            return await ctx.send(f"<:fail:812062765028081674> Logging not setup on this server. Use `{ctx.prefix}logchannel` to setup a logging channel.")

        logchan = ctx.guild.get_channel(int(logchan[0]))

        await db.execute("""
        UPDATE logging SET channel_updates = ? WHERE server = ?
        """, False, ctx.guild.id)
        await ctx.send(f"<:ballot_box_with_check:805871188462010398> Server bans will no longer be logged in {logchan.mention}")


    @unlog.command(name="leaves", brief="Unlog all server leaves", aliases=['leave','left','member_leave','memver_leaves'])
    async def leaves_(self, ctx):
        logchan = await db.record("""
        SELECT logchannel FROM logging WHERE server = ?
        """, str(ctx.guild.id)) or None
        if logchan is None or logchan[0] is None: 
            return await ctx.send(f"<:fail:812062765028081674> Logging not setup on this server. Use `{ctx.prefix}logchannel` to setup a logging channel.")

        logchan = ctx.guild.get_channel(int(logchan[0]))

        await db.execute("""
        UPDATE logging SET leaves = ? WHERE server = ?
        """, False, ctx.guild.id)
        await ctx.send(f"<:ballot_box_with_check:805871188462010398> Server leaves will no longer be logged in {logchan.mention}")


    @unlog.command(name="joins", brief="Unlog all server joins", aliases=['join','joined','member_join','membed_joins','membed_add'])
    async def joins_(self, ctx):
        logchan = await db.record("""
        SELECT logchannel FROM logging WHERE server = ?
        """, str(ctx.guild.id)) or None
        if logchan is None or logchan[0] is None: 
            return await ctx.send(f"<:fail:812062765028081674> Logging not setup on this server. Use `{ctx.prefix}logchannel` to setup a logging channel.")

        logchan = ctx.guild.get_channel(int(logchan[0]))

        await db.execute("""
        UPDATE logging SET joins = ? WHERE server = ?
        """, False, ctx.guild.id)
        await ctx.send(f"<:ballot_box_with_check:805871188462010398> Server joins will no longer be logged in {logchan.mention}")