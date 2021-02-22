import random
import re
import discord
import requests
import io

from discord.ext import commands
from datetime import datetime
from collections import OrderedDict

from utilities import permissions, default
from lib.db import db


def clean_string(string):
    string = re.sub('@', '@\u200b', string)
    string = re.sub('#', '#\u200b', string)
    return string


def setup(bot):
    bot.add_cog(Logging(bot))


class Logging(commands.Cog):

    """
    Log your server events
    """

    def __init__(self, bot):
        self.bot = bot

      #####################
     ## Event Listeners ##
    #####################

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel):
        webhook_id = db.record("SELECT LoggerWebhookID FROM guilds WHERE GuildID = ?", channel.guild.id) or (None)
        if webhook_id is None or "None" in str(webhook_id): 
            return
        webhook_id = int(str(webhook_id).strip("(),'"))
        webhook = await self.bot.fetch_webhook(webhook_id)
        if channel.guild.id != webhook.guild.id: return

        embed = discord.Embed(description=
                                          f"**Channel:** {channel.mention} **Name:** `{channel.name}`\n"
                                          f"**Server:** `{channel.guild.name}` **ID:** `{channel.guild.id},`\n\n"
        , color=default.config()["embed_color"], timestamp=datetime.utcnow())
        embed.set_author(name="Channel Created", icon_url="https://cdn.discordapp.com/emojis/810659118045331517.png?v=1")
        embed.set_footer(text=f"Channel ID: {channel.id}")
        await webhook.execute(embed=embed)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        webhook_id = db.record("SELECT LoggerWebhookID FROM guilds WHERE GuildID = ?", channel.guild.id) or (None)
        if webhook_id is None or "None" in str(webhook_id): 
            return
        webhook_id = int(str(webhook_id).strip("(),'"))
        webhook = await self.bot.fetch_webhook(webhook_id)
        if channel.guild.id != webhook.guild.id: return

        embed = discord.Embed(description=
                                          f"**Channel:** {channel.mention} **Name:** `{channel.name}`\n"
                                          f"**Server:** `{channel.guild.name}` **ID:** `{channel.guild.id},`\n\n"
        , color=default.config()["embed_color"], timestamp=datetime.utcnow())
        embed.set_author(name="Channel Deleted", icon_url="https://cdn.discordapp.com/emojis/810659118045331517.png?v=1")
        embed.set_footer(text=f"Channel ID: {channel.id}")
        await webhook.execute(embed=embed)

    @commands.Cog.listener()
    async def on_guild_channel_update(self, before, after):
        webhook_id = db.record("SELECT LoggerWebhookID FROM guilds WHERE GuildID = ?", after.guild.id) or (None)
        if webhook_id is None or "None" in str(webhook_id): 
            return
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
            await webhook.execute(embed=embed)

        elif before.category != after.category:
            embed = discord.Embed(
                          description=f"**Channel:** {after.mention} **Name:** `{after}`\n"
                                      f"**Old Category:** `{before.category}`\n"
                                      f"**New Category:** `{after.category}`\n",
                          colour=default.config()["embed_color"],
                          timestamp=datetime.utcnow())
            embed.set_author(name=f"Channel Update")
            embed.set_footer(text=f"Channel ID: {after.id}")
            await webhook.execute(embed=embed)

        elif before.topic != after.topic:
            embed = discord.Embed(
                          description=f"**Channel:** {after.mention} **Name:** `{after}`\n"
                                      f"**Old Topic:** `{before.topic}`\n"
                                      f"**New Topic:** `{after.topic}`\n",
                          colour=default.config()["embed_color"],
                          timestamp=datetime.utcnow())
            embed.set_author(name=f"Channel Update")
            embed.set_footer(text=f"Channel ID: {after.id}")
            await webhook.execute(embed=embed)

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
            await webhook.execute(embed=embed)


    @commands.Cog.listener()
    async def on_user_update(self, before, after):

        if before.name != after.name:
            to_send = []
            for guild in self.bot.guilds:
                for member in guild.members:
                    if member.id != before.id: 
                        continue
                    to_send.append(guild.id)
            if to_send:
                for i in to_send:
                    print(i)
                    webhook_id = db.record("SELECT LoggerWebhookID FROM guilds WHERE GuildID = ?", i) or (None)
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

            await webhook.execute(embed=embed)

        if before.discriminator != after.discriminator:
            to_send = []
            for guild in self.bot.guilds:
                for member in guild.members:
                    if member.id != before.id: 
                        continue
                    to_send.append(guild.id)
            if to_send:
                for i in to_send:
                    print(i)
                    webhook_id = db.record("SELECT LoggerWebhookID FROM guilds WHERE GuildID = ?", i) or (None)
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

            await webhook.execute(embed=embed)

        if before.avatar_url != after.avatar_url:
            to_send = []
            for guild in self.bot.guilds:
                for member in guild.members:
                    if member.id != before.id: 
                        continue
                    to_send.append(guild.id)
            if to_send:
                for i in to_send:
                    webhook_id = db.record("SELECT LoggerWebhookID FROM guilds WHERE GuildID = ?", i) or (None)
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
            await webhook.execute(embed=embed)


    @commands.Cog.listener()
    async def on_member_join(self, member):
        webhook_id = db.record("SELECT LoggerWebhookID FROM guilds WHERE GuildID = ?", member.guild.id) or (None)
        if webhook_id is None or "None" in str(webhook_id): 
            return
        webhook_id = int(str(webhook_id).strip("(),'"))
        webhook = await self.bot.fetch_webhook(webhook_id)
        if member.guild.id != webhook.guild.id: return

        embed = discord.Embed(
                      description=f"**User:** {member.mention} **Name:** `{member}`\n",
                      colour=default.config()["embed_color"],
                      timestamp=datetime.utcnow())
        embed.set_author(name=f"User Joined")
        embed.set_footer(text=f"User ID: {member.id}")
        await webhook.execute(embed=embed)


    @commands.Cog.listener()
    async def on_member_remove(self, member):
        webhook_id = db.record("SELECT LoggerWebhookID FROM guilds WHERE GuildID = ?", member.guild.id) or (None)
        if webhook_id is None or "None" in str(webhook_id): 
            return
        webhook_id = int(str(webhook_id).strip("(),'"))
        webhook = await self.bot.fetch_webhook(webhook_id)
        if member.guild.id != webhook.guild.id: return

        embed = discord.Embed(
                      description=f"**User:** {member.mention} **Name:** `{member}`\n",
                      colour=default.config()["embed_color"],
                      timestamp=datetime.utcnow())
        embed.set_author(name=f"User Left")
        embed.set_footer(text=f"User ID: {member.id}")
        await webhook.execute(embed=embed)


    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        if before is None:
            return
        webhook_id = db.record("SELECT LoggerWebhookID FROM guilds WHERE GuildID = ?", after.guild.id) or (None)
        if webhook_id is None or "None" in str(webhook_id): 
            return
        webhook_id = int(str(webhook_id).strip("(),'"))
        webhook = await self.bot.fetch_webhook(webhook_id)
        if after.guild.id != webhook.guild.id: return

        if before.display_name != after.display_name:
            embed = discord.Embed(
                          description=f"**User:** {after.mention} **Name:** `{after}`\n"
                                      f"**Old Nickname:** `{before.display_name}`\n"
                                      f"**New Nickname:** `{after.display_name}`\n",
                          colour=default.config()["embed_color"],
                          timestamp=datetime.utcnow())
            embed.set_author(name=f"Nickname Change")
            embed.set_footer(text=f"User ID: {after.id}")

            await webhook.execute(embed=embed)

            name_list = db.record('''SELECT nicknames
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
            db.execute('''UPDATE users
                              SET nicknames=?
                              WHERE (id=? AND server=?)''',
                           new_names, before.id, before.guild.id)

        elif before.roles != after.roles:
            embed = discord.Embed(
                          description=f"**User:** {after.mention} **Name:** `{after}`\n"
                                      f"**Old Roles:** {', '.join([r.mention for r in before.roles if r != after.guild.default_role])}\n"
                                      f"**New Roles:** {', '.join([r.mention for r in after.roles if r != after.guild.default_role])}\n",
                          colour=default.config()["embed_color"],
                          timestamp=datetime.utcnow())
            embed.set_author(name=f"Role Updates")
            embed.set_footer(text=f"User ID: {after.id}")

            await webhook.execute(embed=embed)


    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        if before.author.bot: return
        webhook_id = db.record("SELECT LoggerWebhookID FROM guilds WHERE GuildID = ?", after.guild.id) or (None)
        if webhook_id is None or "None" in str(webhook_id): 
            return
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
        await webhook.execute(embed=embed)


    @commands.Cog.listener()
    async def on_message_delete(self, message):

        if not message.guild: return
        db.execute("""
        INSERT OR REPLACE INTO snipe VALUES (?, ?, ?, ?, ?, ?)
        """, message.channel.id, message.guild.id, message.author.id, message.id, str(message.content), message.created_at.strftime('%Y-%m-%d %H:%M:%S'))

        webhook_id = db.record("SELECT LoggerWebhookID FROM guilds WHERE GuildID = ?", message.guild.id) or (None)
        if webhook_id is None or "None" in str(webhook_id): 
            return
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
        await webhook.execute(embed=embed)

    
    @commands.Cog.listener()
    async def on_bulk_message_delete(self, messages):
        guild_obj = random.choice(messages).guild
        webhook_id = db.record("SELECT LoggerWebhookID FROM guilds WHERE GuildID = ?", guild_obj.id) or (None)
        if webhook_id is None or "None" in str(webhook_id): 
            return
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

        await webhook.execute(embed=embed)

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

        author, message_id, content, timestamp = db.record("""
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
    async def log(self, ctx, messages : int = 25, *, chan : discord.TextChannel = None):
        """
        Usage:      -log [message amount] [channel]
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
            if webhook.name == "NGC0000":
                return await ctx.send(":warning: Logging is already set up on this server")

        response = requests.get(ctx.guild.me.avatar_url)
        avatar = response.content
        webhook = await channel.create_webhook(name="NGC0000", avatar=avatar, reason="Webhook created for server logging.")
        db.execute("UPDATE guilds SET LoggerWebhookID = ? WHERE GuildID = ?", webhook.id, ctx.guild.id)
        db.execute("UPDATE guilds SET Log_channel = ? WHERE GuildID = ?", channel.id, ctx.guild.id)
        await ctx.send(f"<:ballot_box_with_check:805871188462010398> Set channel {channel.mention} as this server's logging channel.")
        await webhook.execute("Hello! I'm going to be logging your server's messages and user updates in this channel until you tell me not to. "
        "I'll repost all deleted messages, notify you of nickname updates, role changes, username updates, avatar changes, and more.")


    @commands.command(brief="Remove your server's log channel.",aliases=['unlogserver'])
    @commands.guild_only()
    @permissions.has_permissions(manage_guild=True)
    async def unlogchannel(self, ctx):
        server_webhook_list = await ctx.guild.webhooks()
        found = []
        for webhook in server_webhook_list:
            if webhook.name == "NGC0000":
                found.append(webhook.name)
        if found:
            await webhook.delete(reason=f"Logging webhook deleted by {ctx.author}.")
            db.execute("UPDATE guilds SET LoggerWebhookID = NULL WHERE GuildID = ?", ctx.guild.id)
            await ctx.send("<:ballot_box_with_check:805871188462010398> Logging is now disabled on this server")
            return
        else:
            return await ctx.send(f":warning: Logging is not enabled on this server.")
