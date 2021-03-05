import os
import re
import time
import psutil
import inspect
import discord
import datetime

from discord.ext import commands
from platform import python_version
from psutil import Process, virtual_memory
from discord import __version__ as discord_version

from utilities import permissions, default, converters

   
def setup(bot):
    bot.add_cog(General(bot))


class General(commands.Cog):
    """
    Module for all information on users, bots etc.
    """

    def __init__(self, bot):
        self.bot = bot
        self.cxn = bot.connection
        self.process = psutil.Process(os.getpid())
        self.startTime = int(time.time())
        self.config = default.config()

    async def total_global_commands(self):
        query = '''SELECT COUNT(*) as c FROM commands'''
        value = await self.cxn.fetchrow(query)
        return int(value[0])

    async def total_global_messages(self):
        query = '''SELECT COUNT(*) as c FROM messages'''
        value = await self.cxn.fetchrow(query)
        return int(value[0])


    @commands.command(aliases = ['info'], brief="Display information about the bot.")
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


        embed = discord.Embed(colour=default.config()["embed_color"])
        embed.set_thumbnail(url=ctx.bot.user.avatar_url)
        embed.add_field(name="Last boot", value=default.timeago(datetime.datetime.utcnow() - self.bot.uptime), inline=True)
        embed.add_field(
            name=f"Developer{'' if len(self.config['owners']) == 1 else 's'}",
            value=',\n '.join([str(self.bot.get_user(x)) for x in self.config["owners"]]),
            inline=True)
        embed.add_field(name="Python Version", value=f"{python_version()}", inline=True)
        embed.add_field(name="Library", value="Discord.py", inline=True)
        embed.add_field(name="API Version", value=f"{discord_version}", inline=True)
        embed.add_field(name="Command Count", value=len([x.name for x in self.bot.commands if not x.hidden]), inline=True)
        embed.add_field(name="Server Count", value=f"{len(ctx.bot.guilds)}", inline=True)
        embed.add_field(name="Channel Count", value=f"""<:textchannel:810659118045331517> {text}        <:voicechannel:810659257296879684> {voice}""", inline=True)
        embed.add_field(name="Member Count", value=f"{total_members}", inline=True)
        embed.add_field(name="Commands Run", value=f"{await self.total_global_commands():,}", inline=True)
        embed.add_field(name="Messages Seen", value=f"{await self.total_global_messages():,}", inline=True)
        #Below are cached commands. Above are stored in the asyncpg database
        #embed.add_field(name="Commands Run", value=sum(self.bot.command_stats.values()), inline=True)
        embed.add_field(name="RAM", value=f"{ramUsage:.2f} MB", inline=True)
        #embed.add_field(name="CPU", value=f"{cpu_time} MB", inline=True)

        await ctx.send(content=f"About **{ctx.bot.user}** | **{self.config['version']}**", embed=embed)


    @commands.command(aliases=["platform"], brief = "Show which discord platform a user is on.")
    @commands.guild_only()
    async def mobile(self, ctx, members:commands.Greedy[discord.Member]):
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
                await ctx.send(f'Somthing went wrong: {e}')

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
            await ctx.send(f'<:desktop:817160032391135262> User{"" if len(notmobile) == 1 else "s"} `{", ".join(notmobile)}` {"is" if len(notmobile) == 1 else "are"} on discord desktop.')
        if mobilestatus:
            mobile = []
            for member in mobilestatus: 
                users = []
                people = await self.bot.fetch_user(int(member.id))
                users.append(people)
                for user in users:
                    username = f"{user.name}#{user.discriminator}"
                    mobile += [username]
            await ctx.send(f'<:mobile:817160232248672256> User{"" if len(mobile) == 1 else "s"} `{", ".join(mobile)}` {"is" if len(mobile) == 1 else "are"} on discord mobile.')
        if web_status:
            mobile = []
            for member in web_status: 
                users = []
                people = await self.bot.fetch_user(int(member.id))
                users.append(people)
                for user in users:
                    username = f"{user.name}#{user.discriminator}"
                    mobile += [username]
            await ctx.send(f'<:web:817163202877194301> User{"" if len(mobile) == 1 else "s"} `{", ".join(mobile)}` {"is" if len(mobile) == 1 else "are"} on discord web.')
        if offline:
            mobile = []
            for member in offline: 
                users = []
                people = await self.bot.fetch_user(int(member.id))
                users.append(people)
                for user in users:
                    username = f"{user.name}#{user.discriminator}"
                    mobile += [username]
            await ctx.send(f'<:offline:810650959859810384> User{"" if len(mobile) == 1 else "s"} `{", ".join(mobile)}` {"is" if len(mobile) == 1 else "are"} offline')


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
        except AttributeError: return await ctx.send(f"<:fail:816521503554273320> User `{user}` does not exist.")
        avatar = user.avatar_url
        embed = discord.Embed(title=f"**{user.display_name}'s avatar.**", description=f'Links to `{user}\'s` avatar:  '
                                                                                      f'[webp]({(str(user.avatar_url))}) | '
                                                                                      f'[png]({(str(user.avatar_url).replace("webp", "png"))}) | ' 
                                                                                      f'[jpeg]({(str(user.avatar_url).replace("webp", "jpg"))})  ', 
                                                                          color=default.config()["embed_color"])
        embed.set_image(url=avatar)
        await ctx.send(embed=embed)

    # command mostly from Alex Flipnote's discord_bot.py bot
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

        await default.prettyResults(ctx, "playing", f"Found **{len(loop)}** on your search for **{search}**", loop)


    @find.command(name="username", aliases=["name"])
    async def find_name(self, ctx, *, search: str):
        loop = [f"{i} ({i.id})" for i in ctx.guild.members if search.lower() in i.name.lower() and not i.bot]
        await default.prettyResults(ctx, "name", f"Found **{len(loop)}** on your search for **{search}**", loop)


    @find.command(name="nickname", aliases=["nick"])
    async def find_nickname(self, ctx, *, search: str):
        loop = [f"{i.nick} | {i} ({i.id})" for i in ctx.guild.members if i.nick if (search.lower() in i.nick.lower()) and not i.bot]
        await default.prettyResults(ctx, "name", f"Found **{len(loop)}** on your search for **{search}**", loop)


    @find.command(name="id")
    async def find_id(self, ctx, *, search: int):
        loop = [f"{i} | {i} ({i.id})" for i in ctx.guild.members if (str(search) in str(i.id)) and not i.bot]
        await default.prettyResults(ctx, "name", f"Found **{len(loop)}** on your search for **{search}**", loop)


    @find.command(name="discrim", aliases=["discriminator"])
    async def find_discrim(self, ctx, *, search: str):
        if not len(search) == 4 or not re.compile("^[0-9]*$").search(search):
            return await ctx.send("You must provide exactly 4 digits")

        loop = [f"{i} ({i.id})" for i in ctx.guild.members if search == i.discriminator]
        await default.prettyResults(ctx, "discriminator", f"Found **{len(loop)}** on your search for **{search}**", loop)


    @commands.command(brief="Display information on a passed user.", aliases=["whois","ui"])
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

        total = len(joinedList)
        position = joinedList.index(check_item) + 1
        
        msg = "{:,}".format(position)

        query = '''SELECT commandcount FROM users WHERE id = $1 AND server_id = $2'''
        command_count = await self.cxn.fetchrow(query, member.id, ctx.guild.id)

        query = '''SELECT messagecount FROM users WHERE id = $1 AND server_id = $2'''
        messages = await self.cxn.fetchrow(query, member.id, ctx.guild.id)

        #status_dict = {'online': 'Online', 'offline': 'Offline', 'dnd': 'Do Not Disturb', 'idle': "Idle"}
        status_dict = {
            'online': '<:online:810650040838258711> Online', 
            'offline': '<:offline:810650959859810384> Offline', 
            'dnd': '<:dnd:810650845007708200> Do Not Disturb', 
            'idle': "<:idle:810650560146833429> Idle"
            }
        perm_list = [Perm[0] for Perm in member.guild_permissions if Perm[1]]
        embed = discord.Embed(color=default.config()["embed_color"])
        embed.set_author(name=f"{member}", icon_url=member.avatar_url)
        embed.set_thumbnail(url=member.avatar_url)
        embed.set_footer(text=f"User ID: {member.id} | Created on {member.created_at.__format__('%m/%d/%Y')}")
        embed.add_field(name="Nickname", value=f"{'<:owner:810678076497068032>'if member.id == ctx.guild.owner.id else '<:bot:816692223566544946>' if member.bot else ''} {member.display_name}")
        embed.add_field(name="Messages", value=f"<:messages:816696500314701874>  {messages[0]}")
        embed.add_field(name="Commands", value=f"<:command:816693906951372870>  {command_count[0]}")
        embed.add_field(name="Status", value=f"{status_dict[str(member.status)]}")
        embed.add_field(name="Highest Role", value=f"<:role:816699853685522442> {'@everyone' if member.top_role.name == '@everyone' else member.top_role.mention}")
        embed.add_field(name="Join Position", value=f"<:invite:816700067632513054> #{msg}")
        #embed.add_field(name=f"**{member.display_name}'s Info:**", value=
        #                                                               f"> **Nickname:** {member.display_name}\n"
        #                                                               f"> **ID:** {member.id}\n"
        #                                                               f"> **Messages:** {messages[0]}\n"
        #                                                               f"> **Commands:** {command_count[0]}\n"
        #                                                               f"> **Highest Role:** {member.top_role.mention}\n"
        #                                                               f"> **Status:** {(status_dict[str(member.status)])}\n"
        #                                                               f"> **Registered:** {member.created_at.__format__('%B %d, %Y at %I:%M %p')}\n"
        #                                                               f"> **Joined:** {member.joined_at.__format__('%B %d, %Y at %I:%M %p')}\n"
        #                                                               f"> **Bot:** {member.bot}\n", inline=False)
        #if len(member.roles) > 1:
        #    role_list = member.roles[::-1]
        #    role_list.remove(member.roles[0])
        #    embed.add_field(name=f"Roles: [{len(role_list)}]", value =" ".join([role.mention for role in role_list]), inline=False)
        #else:
        #    embed.add_field(name=f"Roles: [0]", value ="** **", inline=False)
        #embed.add_field(name="Permissions:", value=", ".join(perm_list).replace("_", " ").replace("guild", "server").title().replace("Tts", "TTS"), inline=False)
        await ctx.send(embed=embed)


    @commands.command(brief="Show information about the current server.", aliases=["si","serverstats","ss","server"])
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

        em = discord.Embed(color = default.config()["embed_color"])
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


    @commands.command(brief="Send a bugreport to the bot developer.", aliases=['reportbug','reportissue',"issuereport"])
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


    @commands.command(brief="Send a much appreciated suggestion to the bot developer.", aliases=["suggestion"])
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


    def get_bot_uptime(self, *, brief=False):
        now = datetime.datetime.utcnow()
        delta = now - self.bot.uptime
        hours, remainder = divmod(int(delta.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        days, hours = divmod(hours, 24)

        if not brief:
            if days:
                fmt = '{d} days, {h} hours, {m} minutes, and {s} seconds'
            else:
                fmt = '{h} hours, {m} minutes, and {s} seconds'
        else:
            fmt = '{h}h {m}m {s}s'
            if days:
                fmt = '{d}d ' + fmt

        return fmt.format(d=days, h=hours, m=minutes, s=seconds)


    @commands.command(brief="Show how long the bot has been running for.", aliases=['runningtime'])
    async def uptime(self, ctx):
        """
        Usage:  -uptime
        Alias:  -runningtime
        Output: Time since last reboot.
        """
        await ctx.send(f":stopwatch: I've been running for `{self.get_bot_uptime(brief=False)}`")


    @commands.command(brief="Show which server mods are online.", aliases=['moderators'])
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


    @commands.command(brief="Show which server admins are online.", aliases=['administrators'])
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


    @commands.command(brief="Test the bot's response time.", aliases=['latency'])        
    async def ping(self, ctx):
        """
        Usage: -ping
        Alias: -latency
        Output: API and Bot response time.
        """
        start = time.time()
        message = await ctx.send(f"{ctx.author.mention} The bot latency is {self.bot.latency*1000:,.0f} ms.")
        end = time.time()
        await message.edit(content=f"{ctx.author.mention} The bot latency is {self.bot.latency*1000:,.0f} ms. The response time is {(end-start)*1000:,.0f} ms.")


    @commands.command(brief="Get information on any discord user by ID.", aliases=['lookup'])
    async def user(self, ctx, snowflake:int = None):
        """
        Usage:   -user <user>
        Alias:   -lookup
        Example: -user 810377376269205546
        Output:  General information on any discord user.
        Notes:
            Accepts nickname, ID, mention, username, and username+discrim
            Neither you nor the bot must share a server with the user.
        """
        if snowflake is None: return await ctx.send(f"Usage: -user <user>")
        try:
            user = await self.bot.fetch_user(snowflake)
        except discord.NotFound:
            return await ctx.send(f"No user with id {snowflake} exists.")
        sid = int(snowflake)
        timestamp = ((sid >> 22) + 1420070400000) / 1000
        cdate = datetime.datetime.utcfromtimestamp(timestamp)
        fdate = cdate.strftime('%A, %B %d, %Y at %H:%M:%S')
        em = discord.Embed(description=f"{user}'s information.", color=default.config()["embed_color"])
        em.set_author(name=user, icon_url=user.avatar_url)
        em.set_thumbnail(url=user.avatar_url)
        em.add_field(name="Mention", value=user.mention)
        em.add_field(name="Name", value=user.name)
        em.add_field(name="ID", value=user.id)
        em.add_field(name="Discriminator", value=user.discriminator)
        em.add_field(name="Default Avatar", value=user.default_avatar)
        em.add_field(name="Registered On", value=fdate)
        await ctx.send(embed=em)


    @commands.command(brief="Show the date a discord snowflake ID was created.", aliases=['id'])
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


    @commands.command(brief="Show some info on the bot's developer and purpose.", aliases=['boss'])
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
                color=default.config()["embed_color"]
            )
            embed.set_author(
                name=owner, icon_url=owner.avatar_url
            )
            await ctx.send(embed=embed)
        else:
            await ctx.send("I don't know who my owner is ¯\_(ツ)_/¯.")

    @commands.command(brief="Displays the source code or for a specific command.", aliases=['sourcecode'])
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
                return await ctx.send(f'<:fail:816521503554273320> Command `{command}` does not exist.')

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
