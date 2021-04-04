import io
import os
import re
import sys
import time
import codecs
import pprint
from discord.ext.tasks import loop
import psutil
import struct
import asyncio
import inspect
import discord
import platform
import datetime
import subprocess

from collections import Counter
from discord.ext import commands, menus
from platform import python_version
from psutil import Process, virtual_memory
from discord import __version__ as discord_version

from utilities import permissions, utils, converters, pagination, speedtest

   
def setup(bot):
    bot.add_cog(General(bot))


class General(commands.Cog):
    """
    Module for all information on users, bots etc.
    """
    def __init__(self, bot):
        self.bot = bot
        self.emote_dict = bot.emote_dict
        self.process = psutil.Process(os.getpid())
        self.startTime = int(time.time())

    async def total_global_commands(self):
        query = '''SELECT COUNT(*) as c FROM commands'''
        value = await self.bot.cxn.fetchrow(query)
        return int(value[0])

    async def total_global_messages(self):
        query = '''SELECT COUNT(*) as c FROM messages'''
        value = await self.bot.cxn.fetchrow(query)
        return int(value[0])


    @commands.command(aliases=['info'], brief="Display information about the bot.")
    async def about(self, ctx):
        """
        Usage:  -about
        Alias:  -info
        Output: Version Information, Bot Statistics
        """
        total_members = sum(1 for x in self.bot.get_all_members())
        voice_channels = []
        text_channels = []
        for guild in self.bot.guilds:
            voice_channels.extend(guild.voice_channels)
            text_channels.extend(guild.text_channels)

        text = len(text_channels)
        voice = len(voice_channels)

        ramUsage = self.process.memory_full_info().rss / 1024**2
        avgmembers = round(len(self.bot.users) / len(self.bot.guilds))
        currentTime = int(time.time())
        proc = Process()
        with proc.oneshot():
            #This could be used, but I thought most people are not interested in stuff like CPU Time
            #cpu_time = datetime.timedelta(seconds=(cpu := proc.cpu_times()).system + cpu.user)
            mem_total = virtual_memory().total / (1024**2)
            mem_of_total = proc.memory_percent()
            mem_usage = mem_total * (mem_of_total / 100)


        embed = discord.Embed(colour=self.bot.constants.embed)
        embed.set_thumbnail(url=ctx.bot.user.avatar_url)
        embed.add_field(name="Last boot", value=utils.timeago(datetime.datetime.utcnow() - self.bot.uptime), inline=True)
        embed.add_field(
            name=f"Developer{'' if len(self.bot.constants.owners) == 1 else 's'}",
            value=',\n '.join([str(self.bot.get_user(x)) for x in self.bot.constants.owners]),
            inline=True)
        embed.add_field(name="Python Version", value=f"{python_version()}", inline=True)
        embed.add_field(name="Library", value="Discord.py", inline=True)
        embed.add_field(name="API Version", value=f"{discord_version}", inline=True)
        embed.add_field(name="Command Count", value=len([x.name for x in self.bot.commands if not x.hidden]), inline=True)
        embed.add_field(name="Server Count", value=f"{len(ctx.bot.guilds):,}", inline=True)
        embed.add_field(name="Channel Count", value=f"""{self.emote_dict['textchannel']} {text:,}        {self.emote_dict['voicechannel']} {voice:,}""", inline=True)
        embed.add_field(name="Member Count", value=f"{total_members:,}", inline=True)
        embed.add_field(name="Commands Run", value=f"{await self.total_global_commands():,}", inline=True)
        embed.add_field(name="Messages Seen", value=f"{await self.total_global_messages():,}", inline=True)
        #Below are cached commands. Above are stored in the asyncpg database
        #embed.add_field(name="Commands Run", value=sum(self.bot.command_stats.values()), inline=True)
        embed.add_field(name="RAM", value=f"{ramUsage:.2f} MB", inline=True)
        #embed.add_field(name="CPU", value=f"{cpu_time} MB", inline=True)

        await ctx.send(content=f"About **{ctx.bot.user}** | **{self.bot.constants.version}**", embed=embed)


    @commands.command(aliases=["mobile"], brief = "Show which discord platform a user is on.")
    @commands.guild_only()
    async def platform(self, ctx, members:commands.Greedy[discord.Member]):
        """
        Usage:  -mobile <member> [member] [member]...
        Alias:  -platform
        Output: Shows whether a user is on desktop or mobile.
        Notes:  Cannot determine platform when users are offline.
        """
        if not len(members):
            return await ctx.send(f"Usage: `{ctx.prefix}mobile <member> [member] [member]...`")
        mobilestatus = []
        notmobilestatus = []
        web_status = []
        offline = []
        for member in members:
            print(member.is_on_mobile())
            print(member.web_status)
            try:
                mobile = member.is_on_mobile()
            except Exception as e:
                await ctx.send(f"{self.emote_dict['failed']} Somthing went wrong: {e}")

            if mobile is True:
                mobilestatus.append(member)
            elif mobile is False and str(member.status) == "offline":
                offline.append(member)
            elif mobile is False and str(member.web_status) != "offline":
                web_status.append(member)
            else:
                notmobilestatus.append(member)
        if notmobilestatus:
            notmobile = []
            for member in notmobilestatus: 
                users = []
                people = await self.bot.fetch_user(int(member.id))
                users.append(people)
                for user in users:
                    username = f"{user.name}#{user.discriminator}"
                    notmobile += [username]
            await ctx.send(f"{self.emote_dict['desktop']} User{'' if len(notmobile) == 1 else 's'} `{', '.join(notmobile)}` {'is' if len(notmobile) == 1 else 'are'} on discord desktop.")
        if mobilestatus:
            mobile = []
            for member in mobilestatus: 
                users = []
                people = await self.bot.fetch_user(int(member.id))
                users.append(people)
                for user in users:
                    username = f"{user.name}#{user.discriminator}"
                    mobile += [username]
            await ctx.send(f"{self.emote_dict['mobile']} User{'' if len(mobile) == 1 else 's'} `{', '.join(mobile)}` {'is' if len(mobile) == 1 else 'are'} on discord mobile.")
        if web_status:
            mobile = []
            for member in web_status: 
                users = []
                people = await self.bot.fetch_user(int(member.id))
                users.append(people)
                for user in users:
                    username = f"{user.name}#{user.discriminator}"
                    mobile += [username]
            await ctx.send(f"{self.emote_dict['web']} User{'' if len(mobile) == 1 else 's'} `{', '.join(mobile)}` {'is' if len(mobile) == 1 else 'are'} on discord web.")
        if offline:
            mobile = []
            for member in offline: 
                users = []
                people = await self.bot.fetch_user(int(member.id))
                users.append(people)
                for user in users:
                    username = f"{user.name}#{user.discriminator}"
                    mobile += [username]
            await ctx.send(f"{self.emote_dict['offline']} User{'' if len(mobile) == 1 else 's'} `{', '.join(mobile)}` {'is' if len(mobile) == 1 else 'are'} offline")


    async def do_avatar(self, ctx, user, url):
        embed = discord.Embed(title=f"**{user.display_name}'s avatar.**", description=f'Links to `{user}\'s` avatar:  '
                                                                                      f'[webp]({(str(url))}) | '
                                                                                      f'[png]({(str(url).replace("webp", "png"))}) | ' 
                                                                                      f'[jpeg]({(str(url).replace("webp", "jpg"))})  ', 
                                                                          color=self.bot.constants.embed)
        embed.set_image(url=url)
        await ctx.send(embed=embed)


    @commands.command(brief="Display a user's avatar in an embed.", aliases=['av', 'pfp'])
    async def avatar(self, ctx, *, user: converters.DiscordUser=None):
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
        except AttributeError: return await ctx.send(f"{self.emote_dict['failed']} User `{user}` does not exist.")
        await self.do_avatar(ctx, user, url=user.avatar_url)


    @commands.command(brief="Show a user's default avatar.", aliases=['dav', 'dpfp', 'davatar'])
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
        except AttributeError: return await ctx.send(f"{self.emote_dict['failed']} User `{user}` does not exist.")
        await self.do_avatar(ctx, user, user.default_avatar_url)

    # command mostly from Alex Flipnote's discord_bot.py bot
    # I'll rewrite his "prettyresults" method to use a paginator later.
    # https://github.com/AlexFlipnote/discord_bot.py

    @commands.group(brief="Find any user using a search (Command Group).",aliases=['search'])
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


    @find.command(name="playing", aliases=['status'])
    async def find_playing(self, ctx, *, search: str):
        loop = []
        for i in ctx.guild.members:
            if i.activities and (not i.bot):
                for g in i.activities:
                    if g.name and (search.lower() in g.name.lower()):
                        loop.append(f"{i} | {type(g).__name__}: {g.name} ({i.id})")

        await utils.prettyResults(ctx, "playing", f"Found **{len(loop)}** on your search for **{search}**", loop)


    @find.command(name="username", aliases=["name"])
    async def find_name(self, ctx, *, search: str):
        loop = [f"{i} ({i.id})" for i in ctx.guild.members if search.lower() in i.name.lower() and not i.bot]
        await utils.prettyResults(ctx, "name", f"Found **{len(loop)}** on your search for **{search}**", loop)


    @find.command(name="nickname", aliases=["nick"])
    async def find_nickname(self, ctx, *, search: str):
        loop = [f"{i.nick} | {i} ({i.id})" for i in ctx.guild.members if i.nick if (search.lower() in i.nick.lower()) and not i.bot]
        await utils.prettyResults(ctx, "name", f"Found **{len(loop)}** on your search for **{search}**", loop)


    @find.command(name="id")
    async def find_id(self, ctx, *, search: int):
        loop = [f"{i} | {i} ({i.id})" for i in ctx.guild.members if (str(search) in str(i.id)) and not i.bot]
        await utils.prettyResults(ctx, "name", f"Found **{len(loop)}** on your search for **{search}**", loop)


    @find.command(name="discrim", aliases=["discriminator"])
    async def find_discrim(self, ctx, *, search: str):
        if not len(search) == 4 or not re.compile("^[0-9]*$").search(search):
            return await ctx.send("You must provide exactly 4 digits")

        loop = [f"{i} ({i.id})" for i in ctx.guild.members if search == i.discriminator]
        await utils.prettyResults(ctx, "discriminator", f"Found **{len(loop)}** on your search for **{search}**", loop)

    @find.command(name="duplicates", aliases=['dups'])
    async def find_duplicates(self, ctx):
        """Show members with identical names.
        """
        name_list = []
        for member in ctx.guild.members:
            name_list.append(member.display_name.lower())

        name_list = Counter(name_list)
        name_list = name_list.most_common()

        loop = []
        for name_tuple in name_list:
            if name_tuple[1] > 1:
                loop.append(f"Duplicates: [{str(name_tuple[1]).zfill(2)}] {name_tuple[0]}")


        await utils.prettyResults(ctx, "name", f"Found **{len(loop)}** on your search for duplicates", loop)


    def _is_hard_to_mention(self, name):
        """Determine if a name is hard to mention."""
        codecs.register_error('newreplace', lambda x: (
            b" " * (x.end - x.start), x.end))

        encoderes, chars = codecs.getwriter('ascii').encode(name, 'newreplace')

        return re.search(br'[^ ][^ ]+', encoderes) is None
    
    @find.command(name="weird", aliases=['hardmention'])
    async def findhardmention(self, ctx):
        """List members with difficult to mention usernames."""
        loop = [
            member for member
            in ctx.message.guild.members if self._is_hard_to_mention(member.name)
        ]
        print(loop)
        await utils.prettyResults(ctx, "name", f"Found **{len(loop)}** on your search for weird names.", loop)


    @commands.command(brief="Display information on a passed user.", aliases=["whois","ui","profile"])
    @commands.guild_only()
    async def userinfo(self, ctx, member: discord.Member = None):
        """
        Usage:    -userinfo <member>
        Aliases:  -profile, -ui, -whois
        Examples: -userinfo NGC0000, -userinfo 810377376269205546
        Output:   Roles, permissions, and general stats on a user.
        Notes:    If user is not in the server, use -user <user id>.
        """

        if member is None:
            member = ctx.message.author

        if member is None:
            member = ctx.author


        joinedList = []
        for mem in ctx.message.guild.members:
            joinedList.append({ 'ID' : mem.id, 'Joined' : mem.joined_at })
        
        # sort the users by join date
        joinedList = sorted(joinedList, key=lambda x:x["Joined"].timestamp() if x["Joined"] != None else -1)

        check_item = { "ID" : member.id, "Joined" : member.joined_at }

        position = joinedList.index(check_item) + 1
        
        msg = "{:,}".format(position)

        query = '''SELECT COUNT(*) FROM commands WHERE author_id = $1 AND server_id = $2'''
        command_count = await self.bot.cxn.fetchrow(query, member.id, ctx.guild.id) or None
        if command_count is None:
            command_count = 0

        query = '''SELECT COUNT(*) FROM messages WHERE author_id = $1 AND server_id = $2'''
        messages = await self.bot.cxn.fetchrow(query, member.id, ctx.guild.id) or None
        if messages is None:
            messages = 0

        status_dict = {
            'online'  : f"{self.emote_dict['online']} Online",
            'offline' : f"{self.emote_dict['offline']} Offline",
            'dnd'     : f"{self.emote_dict['dnd']} Do Not Disturb", 
            'idle'    : f"{self.emote_dict['idle']} Idle"
            }
        embed = discord.Embed(color=self.bot.constants.embed)
        embed.set_author(name=f"{member}", icon_url=member.avatar_url)
        embed.set_thumbnail(url=member.avatar_url)
        embed.set_footer(text=f"User ID: {member.id} | Created on {member.created_at.__format__('%m/%d/%Y')}")
        embed.add_field(name="Nickname", value=f"{self.emote_dict['owner'] if member.id == ctx.guild.owner.id else self.emote_dict['bot'] if member.bot else ''} {member.display_name}")
        embed.add_field(name="Messages", value=f"{self.emote_dict['messages']}  {messages[0]}")
        embed.add_field(name="Commands", value=f"{self.emote_dict['commands']}  {command_count[0]}")
        embed.add_field(name="Status", value=f"{status_dict[str(member.status)]}")
        embed.add_field(name="Highest Role", value=f"{self.emote_dict['role']} {'@everyone' if member.top_role.name == '@everyone' else member.top_role.mention}")
        embed.add_field(name="Join Position", value=f"{self.emote_dict['invite']} #{msg}")
        #perm_list = [Perm[0] for Perm in member.guild_permissions if Perm[1]]
        #if len(member.roles) > 1:
        #    role_list = member.roles[::-1]
        #    role_list.remove(member.roles[0])
        #    embed.add_field(name=f"Roles: [{len(role_list)}]", value =" ".join([role.mention for role in role_list]), inline=False)
        #else:
        #    embed.add_field(name=f"Roles: [0]", value ="** **", inline=False)
        #embed.add_field(name="Permissions:", value=", ".join(perm_list).replace("_", " ").replace("guild", "server").title().replace("Tts", "TTS"), inline=False)
        await ctx.send(embed=embed)


    @commands.command(brief="Show server information.", aliases=["si","serverstats","ss","server"])
    @commands.guild_only()
    async def serverinfo(self, ctx): 
        """
        Usage:    -serverinfo
        Aliases:  -server, -serverstats, si, ss
        Examples: -serverinfo, -ss
        Output:   General stats on the server.
        """
        server = ctx.message.guild
        online = 0
        for i in server.members:
            if str(i.status) == 'online' or str(i.status) == 'idle' or str(i.status) == 'dnd':
                online += 1
        all_users = []
        for user in server.members:
            all_users.append('{}#{}'.format(user.name, user.discriminator))
        all_users.sort()
        all = '\n'.join(all_users)
        total_text_channels = len(server.text_channels)
        total_voice_channels = len(server.voice_channels)
        total_channels = total_text_channels  + total_voice_channels 
        role_count = len(server.roles)
        emoji_count = len(server.emojis)
        bots = []
        for member in ctx.guild.members:
            if member.bot:
                bots.append(member)
        if str(server.region) == "us-west":
            region = "🇺🇸 US West"
        elif str(server.region) == "us-east":
            region = "🇺🇸 US East"
        elif str(server.region) == "us-central":
            region = "🇺🇸 US Central"
        elif str(server.region) == "us-south":
            region = "🇺🇸 US South"
        elif str(server.region) == "hongkong":
            region = "🇭🇰 Hong Kong"
        elif str(server.region) == "southafrica":
            region = "🇿🇦 South Africa"
        elif str(server.region) == "sydney":
            region = "🇦🇺 Sydney"
        elif str(server.region) == "russia":
            region = "🇷🇺 Russia"
        elif str(server.region) == "europe":
            region = "🇪🇺 Europe"
        elif str(server.region) == "brazil":
            region = "🇧🇷 Brazil"
        elif str(server.region) == "brazil":
            region = "🇸🇬 Singapore"
        elif str(server.region) == "india":
            region = "🇮🇳 India"
        else:
            region = str(server.region).title()

        em = discord.Embed(color = self.bot.constants.embed)
        em.set_thumbnail(url=server.icon_url)
        em.set_author(name=server.name, icon_url=server.icon_url)
        em.set_footer(text=f"Server ID: {server.id} | Created on {server.created_at.__format__('%m/%d/%Y')}")
        em.add_field(name="Owner", value=f"<:owner:810678076497068032> {server.owner}", inline=True)
        em.add_field(name="Total Members", value=f"<:members:810677596453863444> {server.member_count}", inline=True)
        em.add_field(name="Online Members", value=f"<:online:810650040838258711> {online}", inline=True)
        em.add_field(name="Role Count", value=f"<:announce:807097933916405760> {str(role_count)}", inline=True)
        em.add_field(name="Region", value=region, inline=True)
        em.add_field(name="Emoji Count", value=f"<:emoji:810678717482532874> {len(server.emojis)}", inline=True)
        em.add_field(name="Categories", value=f"<:categories:810671569440473119> {len(server.categories)}", inline=True)
        em.add_field(name="Text Channels", value=f"<:textchannel:810659118045331517> {total_text_channels}", inline=True)
        em.add_field(name="Voice Channels", value=f"<:voicechannel:810659257296879684> {total_voice_channels}", inline=True)
        await ctx.send(embed=em)


    @commands.command(brief="Send a bugreport to the bot creator.", aliases=['reportbug','reportissue',"issuereport"])
    @commands.cooldown(2, 60, commands.BucketType.user)
    async def bugreport(self, ctx, *, bug:str):
        """
        Usage:    -bugreport <report>
        Aliases:  -issuereport, -reportbug, -reportissue
        Examples: -bugreport Hello! I found a bug with NGC0000
        Output:   Confirmation that your bug report has been sent.
        Notes:    
            Do not hesitate to use this command, 
            but please be very specific when describing the bug so
            that the developer may easily see the issue and 
            correct it as soon as possible.
        """

        owner = discord.utils.get(self.bot.get_all_members(), id=708584008065351681)
        author = ctx.message.author
        if ctx.guild:
            server = ctx.message.guild
            source = "server **{}** ({})".format(server.name, server.id)
        else:
            source = "a direct message"
        sender = "**{0}** ({0.id}) sent you a bug report from {1}:\n\n".format(author, source)
        message = sender + bug
        try:
            await owner.send(message)
        except discord.errors.InvalidArgument:
            await ctx.send("I cannot send your bug report, I'm unable to find my owner.")
        except discord.errors.HTTPException:
            await ctx.send("Your bug report is too long.")
        except:
            await ctx.send("I'm unable to deliver your bug report. Sorry.")
        else:
            await ctx.send("Your bug report has been sent.")


    @commands.command(brief="Send a suggestion to the bot creator.", aliases=["suggestion"])
    @commands.cooldown(2, 60, commands.BucketType.user)
    async def suggest(self, ctx, *, suggestion : str):
        """
        Usage:    -suggest <report>
        Aliases:  -suggestion
        Examples: -suggest Hello! You should add this feature...
        Output:   Confirmation that your suggestion has been sent.
        Notes:    
            Do not hesitate to use this command, 
            your feedback is valued immensly. 
            However, please be detailed and concise.
        """
        owner = discord.utils.get(self.bot.get_all_members(), id=708584008065351681)
        author = ctx.author
        if ctx.guild:
            server = ctx.guild
            source = "server **{}** ({})".format(server.name, server.id)
        else:
            source = "a direct message"
        sender = "**{}** ({}) sent you a suggestion from {}:\n\n".format(author, author.id, source)
        message = sender + suggestion
        try:
            await owner.send(message)
        except discord.errors.InvalidArgument:
            await ctx.send("I cannot send your message")
        except discord.errors.HTTPException:
            await ctx.send("Your message is too long.")
        except Exception as e:
            await ctx.send("I failed to send your message.")
            print(e)
        else:
            await ctx.send("Your message has been sent.")


    @commands.command(brief="Show the bot's uptime.", aliases=['runningtime'])
    async def uptime(self, ctx):
        """
        Usage:  -uptime
        Alias:  -runningtime
        Output: Time since last reboot.
        """
        await ctx.send(f"{self.bot.emote_dict['stopwatch']} I've been running for `{utils.time_between(self.bot.starttime, int(time.time()))}`")


    @commands.command(brief="Show the server mods.", aliases=['moderators'])
    @commands.guild_only()
    async def mods(self, ctx):
        """
        Usage: -mods
        Alias: -moderators
        Output: All the server moderators and their respective status
        """
        message = ""
        all_status = {
            "online": {"users": [], "emoji": "<:online:810650040838258711>"},
            "idle": {"users": [], "emoji": "<:idle:810650560146833429>"},
            "dnd": {"users": [], "emoji": "<:dnd:810650845007708200>"},
            "offline": {"users": [], "emoji": "<:offline:810650959859810384>"}
        }

        for user in ctx.guild.members:
            user_perm = ctx.channel.permissions_for(user)
            if user_perm.kick_members or user_perm.ban_members:
                if not user.bot:
                    all_status[str(user.status)]["users"].append(f"{user}")

        for g in all_status:
            if all_status[g]["users"]:
                message += f"{all_status[g]['emoji']} `{', '.join(all_status[g]['users'])}`\n"

        await ctx.send(f"Mods in **{ctx.guild.name}:**\n\n{message}")


    @commands.command(brief="Show the server admins.", aliases=['administrators'])
    @commands.guild_only()
    async def admins(self, ctx):
        """
        Usage: -admins
        Alias: -administrators
        Output: All the server admins and their respective status
        """
        message = ""
        all_status = {
            "online": {"users": [], "emoji": "<:online:810650040838258711>"},
            "idle": {"users": [], "emoji": "<:idle:810650560146833429>"},
            "dnd": {"users": [], "emoji": "<:dnd:810650845007708200>"},
            "offline": {"users": [], "emoji": "<:offline:810650959859810384>"}
        }

        for user in ctx.guild.members:
            user_perm = ctx.channel.permissions_for(user)
            if user_perm.administrator:
                if not user.bot:
                    all_status[str(user.status)]["users"].append(f"{user}")

        for g in all_status:
            if all_status[g]["users"]:
                message += f"{all_status[g]['emoji']} `{', '.join(all_status[g]['users'])}`\n"

        await ctx.send(f"Admins in **{ctx.guild.name}:**\n\n{message}")


    @commands.command(brief="Test the bot's response time.", 
                      aliases=['latency', 'speedtest', 'network', 'speed', 'download', 'upload'])        
    async def ping(self, ctx):
        """
        Usage: -ping
        Aliases: -latency, speedtest, network
        Output: Bot speed statistics.
        """
        async with ctx.channel.typing():
            start = time.time()
            message = await ctx.send(f'{self.bot.emote_dict["loading"]} **Calculating Speed...**')
            end = time.time()

            if ctx.invoked_with in ["speedtest", "network","speed", "download", "upload"]:

                st = speedtest.Speedtest()
                st.get_best_server()
                d = await self.bot.loop.run_in_executor(None, st.download)
                u = await self.bot.loop.run_in_executor(None, st.upload)

            db_start = time.time()
            await self.bot.cxn.fetch("SELECT 1;")
            elapsed = time.time() - db_start

            p = str(round((end-start)*1000, 2))
            q = str(round(self.bot.latency*1000, 2))
            if ctx.invoked_with in ["speedtest", "network","speed", "download", "upload"]:
                r = str(round(st.results.ping, 2))
                s = str(round(d/1024/1024, 2))
                t = str(round(u/1024/1024, 2))
            v = str(round((elapsed)*1000, 2))
            
            formatter = []
            formatter.append(p)
            formatter.append(q)
            if ctx.invoked_with in ["speedtest", "network","speed", "download", "upload"]:
                formatter.append(r)
                formatter.append(s)
                formatter.append(t)
            formatter.append(v)
            width = max(len(a) for a in formatter)

            msg = '**Results:**\n'
            msg += '```yaml\n'
            msg += ' Latency: {} ms\n'.format(q.ljust(width, " "))
            if ctx.invoked_with in ["speedtest", "network","speed", "download", "upload"]:
                msg += ' Network: {} ms\n'.format(r.ljust(width, " "))
            msg += 'Response: {} ms\n'.format(p.ljust(width, " "))
            msg += 'Database: {} ms\n'.format(v.ljust(width, " "))
            if ctx.invoked_with in ["speedtest", "network","speed", "download", "upload"]:
                msg += 'Download: {} Mb/s\n'.format(s.ljust(width, " "))
                msg += '  Upload: {} Mb/s\n'.format(t.ljust(width, " "))
            msg += '```'
        await message.edit(content=msg)
        

    @commands.command(brief="Get info about the bot's host environment.")
    async def hostinfo(self, ctx):
        message = await ctx.channel.send(f'{self.bot.emote_dict["loading"]} **Collecting Information...**')

        with self.process.oneshot():
            process = self.process.name
        swap = psutil.swap_memory()
        
        processName   = self.process.name()
        pid           = self.process.ppid()
        swapUsage     = "{0:.1f}".format(((swap[1] / 1024) /1024 ) /1024)
        swapTotal     = "{0:.1f}".format(((swap[0] / 1024) /1024 ) /1024)
        swapPerc      = swap[3]
        cpuCores      = psutil.cpu_count(logical=False)
        cpuThread     = psutil.cpu_count()
        cpuUsage      = psutil.cpu_percent(interval=1)
        memStats      = psutil.virtual_memory()
        memPerc       = memStats.percent
        memUsed       = memStats.used
        memTotal      = memStats.total
        memUsedGB     = "{0:.1f}".format(((memUsed / 1024) / 1024) / 1024)
        memTotalGB    = "{0:.1f}".format(((memTotal/1024)/1024)/1024)
        currentOS     = platform.platform()
        system        = platform.system()
        release       = platform.release()
        version       = platform.version()
        processor     = platform.processor()
        botOwner      = await self.bot.fetch_user(self.bot.constants.owners[0])
        botName       = ctx.guild.me
        currentTime   = int(time.time())
        timeString    = utils.time_between(self.bot.starttime, currentTime)
        pythonMajor   = sys.version_info.major
        pythonMinor   = sys.version_info.minor
        pythonMicro   = sys.version_info.micro
        pythonRelease = sys.version_info.releaselevel
        pyBit         = struct.calcsize("P") * 8
        process       = subprocess.Popen(['git', 'rev-parse', '--short', 'HEAD'], shell=False, stdout=subprocess.PIPE)
        git_head_hash = process.communicate()[0].strip()

        threadString = 'thread'
        if not cpuThread == 1:
            threadString += 's'

        msg = '***{}\'s*** ***Home:***\n'.format(botName)
        msg += '```fix\n'
        msg += 'OS       : {}\n'.format(currentOS)
        msg += 'Owner    : {}\n'.format(botOwner)
        msg += 'Client   : {}\n'.format(botName)
        msg += 'Commit   : {}\n'.format(git_head_hash.decode("utf-8"))
        msg += 'Uptime   : {}\n'.format(timeString)
        msg += 'Process  : {}\n'.format(processName)
        msg += 'PID      : {}\n'.format(pid)
        msg += 'Hostname : {}\n'.format(platform.node())
        msg += 'Language : Python {}.{}.{} {} ({} bit)\n'.format(pythonMajor, pythonMinor, pythonMicro, pythonRelease, pyBit)
        msg += 'Processor: {}\n'.format(processor)
        msg += 'System   : {}\n'.format(system)
        msg += 'Release  : {}\n'.format(release)
        msg += 'CPU Core : {} Threads\n\n'.format(cpuCores)
        msg += utils.center('{}% of {} {}'.format(cpuUsage, cpuThread, threadString), 'CPU') + '\n'
        msg += utils.makeBar(int(round(cpuUsage))) + "\n\n"
        msg += utils.center('{} ({}%) of {}GB used'.format(memUsedGB, memPerc, memTotalGB), 'RAM') + '\n'
        msg += utils.makeBar(int(round(memPerc))) + "\n\n"
        msg += utils.center('{} ({}%) of {}GB used'.format(swapUsage, swapPerc, swapTotal), 'Swap') + '\n'
        msg += utils.makeBar(int(round(swapPerc))) + "\n"
        #msg += 'Processor Version: {}\n\n'.format(version)
        msg += "```"

        await message.edit(content=msg)

    @commands.command(brief="Get info on any discord user.", aliases=['lookup', 'rawuser'])
    async def user(self, ctx, *, user: converters.DiscordUser = None):
        """
        Usage:   -user <user>
        Alias:   -lookup
        Example: -user 810377376269205546
        Output:  General information on any discord user.
        Notes:
            Accepts nickname, ID, mention, username, and username+discrim
            Neither you nor the bot must share a server with the user.
        """
        async with ctx.channel.typing():
            if user is None:
                return await ctx.send(f"Usage: `-user <user>`")

            sid = int(user.id)
            timestamp = ((sid >> 22) + 1420070400000) / 1000
            cdate = datetime.datetime.utcfromtimestamp(timestamp)
            fdate = cdate.strftime('%A, %B %d, %Y at %H:%M:%S')

            try:
                member = self.bot.get_member(sid)
                user = member
            except:
                pass

            # em = discord.Embed(description=f"{user}'s information.", color=self.bot.constants.embed)
            # em.set_author(name=user, icon_url=user.avatar_url)
            # em.set_thumbnail(url=user.avatar_url)
            # em.add_field(name="Mention", value=user.mention)
            # em.add_field(name="Name", value=user.name)
            # em.add_field(name="ID", value=user.id)
            # em.add_field(name="Discriminator", value=user.discriminator)
            # em.add_field(name="Default Avatar", value=user.default_avatar)
            # em.add_field(name="Registered On", value=fdate)
            # await ctx.send(embed=em)

            tracking = self.bot.get_cog("Tracker")

            title_str = f"Information on **{user}**"
            msg = ""
            msg += f"Username      : {user}\n"
            if ctx.guild:
                if isinstance(user, discord.Member) and user.nick:
                    msg += f"Nickname      : {user.nick}\n"
            msg += f"ID            : {user.id}\n"
            if tracking is not None:
                names = (await tracking.user_data(ctx, user))['usernames']
                if names != str(user):
                    msg += f"Usernames     : {names}\n"
                # avatars = (await tracking.user_data(ctx, user))['avatars']
                # msg += f"Avatars       : {avatars}\n"
                if ctx.guild:
                    if isinstance(user, discord.Member):
                        nicknames = (await tracking.user_data(ctx, user))['nicknames']
                        if nicknames:
                            if nicknames != user.nick:
                                msg += f"Nicknames     : {nicknames}\n"
            msg += f"Common Servers: {sum(g.get_member(user.id) is not None for g in ctx.bot.guilds)}\n"
            unix = user.created_at.timestamp()
            msg += f"Created       : {utils.time_between(int(unix), int(time.time()))} ago\n"
            if ctx.guild:
                if isinstance(user, discord.Member):
                    unix = user.joined_at.timestamp()
                    msg += f"Joined        : {utils.time_between(int(unix), int(time.time()))} ago\n"
            if tracking is not None:
                last_observed = await tracking.last_observed(user)
                if last_observed['last_seen'] is not None:
                    msg += f"Last seen     : {last_observed['last_seen']} ago\n"
                if last_observed['last_spoke'] is not None:
                    msg += f"Last spoke    : {last_observed['last_spoke']} ago\n"
                if ctx.guild:
                    if isinstance(user, discord.Member):
                        if last_observed['server_last_spoke'] is not None:
                            msg += f"Spoke here    : {last_observed['server_last_spoke']} ago\n"
            if ctx.guild:
                if isinstance(user, discord.Member) and user.activities:
                    msg += "Status        : {}\n".format('\n'.join(self.activity_string(a) for a in user.activities))
            if ctx.guild:
                if isinstance(user, discord.Member):
                    msg += f"Roles         : {', '.join([r.name for r in sorted(user.roles, key=lambda r: -r.position) if r.name != '@everyone'])}\n"
            if ctx.guild:
                if isinstance(user, discord.Member):
                    perm_list = [Perm[0] for Perm in user.guild_permissions if Perm[1]]
                    msg += f'Permissions   : {", ".join(perm_list).replace("_", " ").replace("guild", "server").title().replace("Tts", "TTS")}'

            await ctx.send(title_str)
            t = pagination.MainMenu(pagination.TextPageSource(msg, prefix="```yaml\n", suffix="```"))
            try:
                await t.start(ctx)
            except menus.MenuError as e:
                await ctx.send(e)


    @commands.command(name="status", brief="Show a member's status")
    async def status_(self, ctx, *, member: discord.Member = None):
        """
        Usage: -status <member>
        """
        if member is None:
            member = ctx.author
        status = '\n'.join(self.activity_string(a) for a in member.activities)
        if status == "":
            return await ctx.send(f"**{member.display_name}** has no current status.")
        msg = f"**{member.display_name}'s** Status: {status}\n"
        await ctx.send(msg)


    def activity_string(self, activity):
        if isinstance(activity, (discord.Game, discord.Streaming)):
            return str(activity)
        elif isinstance(activity, discord.Activity):
            ret = activity.name
            if activity.details:
                ret += " ({})".format(activity.details)
            if activity.state:
                ret += " - {}".format(activity.state)
            return ret
        elif isinstance(activity, discord.Spotify):
            elapsed = datetime.utcnow() - activity.start
            return "{}: {} by {} from {} [{}/{}]".format(
                activity.name,
                activity.title or "Unknown Song",
                activity.artist or "Unknown Artist",
                activity.album or "Unknown Album",
                self.format_timedelta(elapsed),
                self.format_timedelta(activity.duration)
                )
        else:
            return str(activity)

    def format_timedelta(self, td):
        ts = td.total_seconds()
        return "{:02d}:{:06.3f}".format(
            int(ts//60),
            ts % 60)

    @commands.command(brief="Show info on a discord snowflake.", aliases=['id'])
    async def snowflake(self, ctx, *, sid = None):
        """
        Usage: -snowflake <id>
        Alias: -id
        Example: -snowflake 810377376269205546
        Output: Date and time of the snowflake's creation
        """
        if not sid.isdigit(): 
            return await ctx.send(f'Usage: {ctx.prefix}snowflake <id>')

        sid = int(sid)
        timestamp = ((sid >> 22) + 1420070400000) / 1000 # python uses seconds not milliseconds
        cdate = datetime.datetime.utcfromtimestamp(timestamp)
        msg = "Snowflake created {}".format(cdate.strftime('%A, %B %d, %Y at %H:%M:%S UTC'))
        return await ctx.send(msg)


    @commands.command(brief="Show some info on the bot's developer.", aliases=['boss'])
    async def botowner(self, ctx):
        """
        Usage:  -botowner
        Alias:  -boss
        Output: Try it and see
        """
        owner = discord.utils.get(self.bot.get_all_members(), id=708584008065351681)
        if owner is not None:
            embed = discord.Embed(
                description=
                "Hello All! My name is Hecate, and I love to make discord bots. "
                "If you want to get to know me, are too a bot lover, or simply are looking for an active fun-loving server to join, "
                "here's a link to my discord server, where I'm most active. <https://discord.gg/947ramn>\n"
                "NGC0000 is a bot named after our galaxy, the Milky Way. I made NGC0000 specifically for server moderation. "
                "'She' is meant to offer every imaginable feature to server owners and administrators "
                "so that they may manage their server efficiently, and without need for multiple bots. "
                "Her commands are fast, efficient, and offer every opportunity for custom and fair punishments. "
                f"Her help command shows extensive usage examples and explanations of all {len([x.name for x in self.bot.commands if not x.hidden])} commands, " 
                "but if you need further assistance, have questions, or are simply looking for a great community to join, "
                "look no further and join the [support server](https://discord.gg/947ramn).",
                color=self.bot.constants.embed
            )
            embed.set_author(
                name=owner, icon_url=owner.avatar_url
            )
            await ctx.send(embed=embed)
        else:
            await ctx.send("I don't know who my owner is ¯\_(ツ)_/¯.")


    @commands.command(brief="Display the source code.", aliases=['sourcecode'])
    async def source(self, ctx, *, command: str = None):
        """
        Usage: -source [command]
        Alias: -sourcecode
        Notes:
            If no command is specified, shows full repository
        """
        source_url = 'https://github.com/Hecate946/NGC0000'
        branch = 'main'
        if command is None:
            return await ctx.send(source_url)

        else:
            obj = self.bot.get_command(command.replace('.', ' '))
            if obj is None:
                return await ctx.send(f'{self.bot.emote_dict["failed"]} Command `{command}` does not exist.')

            src = obj.callback.__code__
            module = obj.callback.__module__
            filename = src.co_filename

        lines, firstlineno = inspect.getsourcelines(src)
        if not module.startswith('discord'):
            # not a built-in command
            location = os.path.relpath(filename).replace('\\', '/')
        else:
            location = module.replace('.', '/') + '.py'
            source_url = 'https://github.com/Hecate946/NGC0000'
            branch = 'main'

        final_url = f'<{source_url}/blob/{branch}/{location}#L{firstlineno}-L{firstlineno + len(lines) - 1}>'
        msg = f"**__My source {'' if command is None else f'for {command}'} is located at:__**\n\n{final_url}"
        await ctx.send(msg)

    @commands.command(name="permissions",brief="Show a user's permissions.")
    @commands.guild_only()
    async def _permissions(self, ctx, member: discord.Member = None, channel: discord.TextChannel = None):
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
        avatar = member.avatar_url_as(static_format='png')
        e.set_author(name=str(member), url=avatar)
        allowed, denied = [], []
        for name, value in permissions:
            name = name.replace('_', ' ').replace('guild', 'server').title()
            if value:
                allowed.append(name)
            else:
                denied.append(name)

        e.add_field(name='Allowed', value='\n'.join(allowed))
        e.add_field(name='Denied', value='\n'.join(denied))
        await ctx.send(embed=e)


    @commands.command(brief="Lists the server's channels in an embed.", aliases=['channels'])
    @commands.guild_only()
    @commands.bot_has_guild_permissions(embed_links=True)
    @commands.cooldown(1, 20, commands.BucketType.guild)
    @permissions.has_permissions(manage_messages=True)
    async def listchannels(self, ctx, guild:int = None):
        """
        Usage:      -listchannels
        Alias:      -channels
        Output:     Embed of all server channels
        Permission: Manage Messages
        """
        if guild is None:
            guild = ctx.guild.id
        guild = self.bot.get_guild(guild)
        channel_categories = {}

        for chn in sorted(guild.channels, key=lambda c: c.position):
            if isinstance(chn, discord.CategoryChannel) and chn.id not in channel_categories:
                channel_categories[chn.id] = []
            else:
                category = chn.category_id
                if category not in channel_categories:
                    channel_categories[category] = []

                channel_categories[category].append(chn)

        description = None

        def make_category(channels):
            val = ''
            for chn in sorted(channels, key=lambda c: isinstance(c, discord.VoiceChannel)):
                if isinstance(chn, discord.VoiceChannel):
                    val += '\\🔊 '
                else:
                    val += '# '

                val += f'{chn.name}\n'

            return val

        if None in channel_categories:
            description = make_category(channel_categories.pop(None))

        paginator = pagination.Paginator(title='Channels', description=description)

        for category_id in sorted(channel_categories.keys(), key=lambda k: ctx.guild.get_channel(k).position):
            category = ctx.guild.get_channel(category_id)

            val = make_category(channel_categories[category_id])

            paginator.add_field(name=category.name.upper(), value=val, inline=False)

        paginator.finalize()

        for page in paginator.pages:
            await ctx.send(embed=page)

    @commands.command(brief="Shows the raw content of a message")
    async def raw(self, ctx, *, message: discord.Message):
        """
        Usage: -raw [message id]
        Output: Raw message content
        """

        raw_data = await self.bot.http.get_message(message.channel.id, message.id)

        if message.content:
            content = message.content
            for e in message.content:
                emoji_unicode = e.encode('unicode-escape').decode('ASCII')
                content = content.replace(e, emoji_unicode)
            return await ctx.send('```\n' + 'Raw Content\n===========\n\n' + content + '\n```')

        transformer = pprint.pformat
        desc = ""
        for field_name in ('embeds', 'attachments'):
            data = raw_data[field_name]

            if not data:
                continue

            total = len(data)
            for current, item in enumerate(data, start=1):
                title = f'Raw {field_name} ({current}/{total})'
                desc += f"{title}\n\n{transformer(item)}\n"
        p = pagination.MainMenu(pagination.TextPageSource(desc, prefix="```"))

        try:
            await p.start(ctx)
        except menus.MenuError as e:
            await ctx.send(str(e))


    @commands.command(brief="Snipe?", aliases=['retrieve'])
    @commands.guild_only()
    async def snipe(self, ctx, *, member: discord.Member = None):

        if member is None:
            query = """SELECT author_id, message_id, content, timestamp FROM messages WHERE channel_id = $1 AND deleted = True ORDER BY unix DESC;"""
            result = await self.bot.cxn.fetchrow(query, ctx.channel.id) or None
        else:
            query = """SELECT author_id, message_id, content, timestamp FROM messages WHERE channel_id = $1 AND author_id = $2 AND deleted = True ORDER BY unix DESC;"""
            result = await self.bot.cxn.fetchrow(query, ctx.channel.id, member.id) or None

        if result is None:
            return await ctx.send(f"{self.emote_dict['error']} There is nothing to snipe.")

        author = result[0]
        message_id = result[1]
        content = result[2]
        timestamp = result[3]

        author = await self.bot.fetch_user(author)

        if str(content).startswith("```"):
            content = f"**__Message Content__**\n {str(content)}"
        else:
            content = f"**__Message Content__**\n ```fix\n{str(content)}```"

        embed = discord.Embed(description=f"**Author:**  {author.mention}, **ID:** `{author.id}`\n"
                                          f"**Channel:** {ctx.channel.mention} **ID:** `{ctx.channel.id}`\n"
                                          f"**Server:** `{ctx.guild.name}` **ID:** `{ctx.guild.id},`\n\n"
                                          f"**Sent at:** `{timestamp}`\n\n"
                                          f"{content}"
        , color=self.bot.constants.embed, timestamp=datetime.datetime.utcnow())
        embed.set_author(name="Deleted Message Retrieved", icon_url="https://media.discordapp.net/attachments/506838906872922145/603642595419357190/messagedelete.png")
        embed.set_footer(text=f"Message ID: {message_id}")
        await ctx.send(embed=embed)


    @commands.command(description="Invite me to your server!", aliases=['bi', 'invite'])
    async def botinvite(self, ctx):
        """ Invite me to your server """
        await ctx.send(f"**{ctx.author.name}**, use this URL to invite me\n<https://discord.com/api/oauth2/authorize?client_id=810377376269205546&permissions=4294967287&scope=applications.commands%20bot>")