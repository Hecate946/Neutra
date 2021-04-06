import re
import time
import asyncio
import discord
import logging
import datetime

from collections import OrderedDict, Counter, defaultdict
from discord.ext import commands, tasks, menus

from utilities import utils, permissions, converters, pagination


EMOJI_REGEX      = re.compile(r'<a?:.+?:([0-9]{15,21})>')
EMOJI_NAME_REGEX = re.compile(r'[0-9a-zA-Z\_]{2,32}')


def setup(bot):
    bot.add_cog(Stats(bot))

class Stats(commands.Cog):
    """
    Statistics on users, activity, and more.
    """
    def __init__(self, bot):
        self.bot = bot
        self.emoji_batch = defaultdict(Counter)
        self.batch_lock = asyncio.Lock(loop=bot.loop)
        
        self.bulk_inserter.start()

    def cog_unload(self):
        self.bulk_inserter.stop()


    @commands.command(brief="Shows all the bots in a server.")
    @commands.guild_only()
    async def listbots(self, ctx, *, guild: converters.DiscordGuild = None):
        """
        Usage: -listbots [server]
        """
        if guild is None:
            guild = ctx.guild

        list_of_bots = [x for x in guild.members if x.bot]
        if not len(list_of_bots):
            # No bots - should... never... happen.
            await ctx.send(f"This server has no bots.")
        else:
            # Got some bots!
            bot_list = []
            for bot in list_of_bots:
                bot_list.append(
                {
                    "name": str(bot),
                    "value":"Mention: {}\nID: `{}`".format(bot.mention, bot.id)
                }
                )
            p = pagination.MainMenu(pagination.FieldPageSource(
                entries=[("{}. {}".format(y+1,x["name"]), x["value"]) for y,x in enumerate(bot_list)], 
                title="Bots in **{}** ({:,} total)".format(guild.name, len(list_of_bots)),
                per_page=10))
            try:
                await p.start(ctx)
            except menus.MenuError as e:
                await ctx.send(e)

    @commands.command(brief="Shows all users I'm connected to.")
    async def users(self, ctx):
        """
        Usage: -users
        """
        users         = [x for x in self.bot.get_all_members() if not x.bot]
        users_online  = [x for x in users if x.status != discord.Status.offline]
        unique_users  = set([x.id for x in users])
        bots          = [x for x in self.bot.get_all_members() if x.bot]
        bots_online   = [x for x in bots if x.status != discord.Status.offline]
        unique_bots   = set([x.id for x in bots])
        e = discord.Embed(
            title="User Stats",
            color=self.bot.constants.embed
        )
        e.add_field(
            name='Humans',
            value="{:,}/{:,} online ({:,g}%) - {:,} unique ({:,g}%)".format(
                    len(users_online),
                    len(users),
                    round((len(users_online)/len(users))*100, 2),
                    len(unique_users),
                    round((len(unique_users)/len(users))*100, 2)
            ),
            inline=False
        )
        e.add_field(
            name='Bots',
            value="{:,}/{:,} online ({:,g}%) - {:,} unique ({:,g}%)".format(
                    len(bots_online),
                    len(bots),
                    round((len(bots_online)/len(bots))*100, 2),
                    len(unique_bots),
                    round(len(unique_bots)/len(bots)*100, 2)
            ),
            inline=False
        )
        e.add_field(
            name='Total',
            value="{:,}/{:,} online ({:,g}%)".format(
                    len(users_online)+len(bots_online),
                    len(users)+len(bots),
                    round(((len(users_online)+len(bots_online))/(len(users)+len(bots)))*100, 2)
            ),
            inline=False
        )
        await ctx.send(embed=e)

    @commands.command(brief="Lists how many servers you share with the bot.")
    @commands.guild_only()
    async def sharedservers(self, ctx, *, member: converters.DiscordUser = None):
        """
        Usage: -sharedservers [member]
        Output: The servers that the passed member share with the bot
        Notes:
            Will default to youself if no member is passed
        """

        if member is None:
            member = ctx.author

        if member.id == self.bot.user.id:
            return await ctx.send("I'm on **{:,}** server{}. ".format(len(self.bot.guilds),"" if len(self.bot.guilds)==1 else "s"))
        
        count = 0
        for guild in self.bot.guilds:
            for mem in guild.members:
                if mem.id == member.id:
                    count += 1
        if ctx.author.id == member.id:
            targ = "You share"
        else:
            targ = "**{}** shares".format(member.display_name)

        await ctx.send("{} **{:,}** server{} with me.".format(targ,count,"" if count==1 else "s"))


    @commands.command(brief="Check when a user joined the server")
    @commands.guild_only()
    async def joinedat(self, ctx, *, user: discord.Member = None):
        """
        Usage: -joinedat <member>
        Output: Shows when the passed user joined the server
        Notes:
            Will default to youself if no member is passed.
        """
        user = user or ctx.author

        embed = discord.Embed(colour=user.top_role.colour.value)
        embed.set_thumbnail(url=user.avatar_url)
        embed.description = f'**{user}** joined **{ctx.guild.name}**\n{utils.date(user.joined_at)}'
        await ctx.send(embed=embed)


    @commands.command(brief="Tells when a user joined compared to other users.", aliases=["joinposition"])
    @commands.guild_only()
    async def joinpos(self, ctx, *, member: discord.Member = None):
        """
        Usage: -joinpos <member>
        Alias: -joinposition
        Example: -joinpos @Hecate
        Output: Tells when a user joined compared to other users.
        """

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

        before = ""
        after  = ""
        
        msg = "**{}'s** join position is **{:,}**.".format(member.display_name, position, total)
        if position-1 == 1:
            # We have previous members
            before = "**1** user"
        elif position-1 > 1:
            before = "**{:,}** users".format(position-1)
        if total-position == 1:
            # There were users after as well
            after = "**1** user"
        elif total-position > 1:
            after = "**{:,}** users".format(total-position)
        # Build the string!
        if len(before) and len(after):
            # Got both
            msg += "\n\n{} joined before, and {} after.".format(before, after)
        elif len(before):
            # Just got before
            msg += "\n\n{} joined before.".format(before)
        elif len(after):
            # Just after
            msg += "\n\n{} joined after.".format(after)
        await ctx.send(msg)


    @commands.command(brief="Shows the user that joined at the passed position.", aliases=["joinedatposition"])
    @commands.guild_only()
    async def joinedatpos(self, ctx, *, position):
        """
        Usage: -joinedatpos <integer>
        Alias: -joinedatposition
        Example: -joinedatpos 34
        Output: Shows the user that joined at the passed position.
        """
        try:
            position = int(position) - 1
            assert -1 < position < len(ctx.guild.members) 
        except:
            return await ctx.send("Position must be an int between 1 and {:,}".format(len(ctx.guild.members)))
        joinedList = [{"member":mem,"joined":mem.joined_at} for mem in ctx.guild.members]
        # sort the users by join date
        joinedList = sorted(joinedList, key=lambda x:x["joined"].timestamp() if x["joined"] != None else - 1)
        join = joinedList[position]
        msg = "**{}** joined at position **{:,}**.".format(join["member"].display_name, position + 1)
        await ctx.send(msg)


    @commands.command(brief="Lists the first users to join.")
    @commands.guild_only()
    async def firstjoins(self, ctx):
        """
        Usage: -firstjoins
        Output: Embed of members to first join the current server.
        """
        our_list = []
        for member in ctx.guild.members:
            our_list.append(
                {
                    "name":member.display_name,
                    "value":"{} UTC".format(member.joined_at.strftime("%Y-%m-%d %I:%M %p") if member.joined_at != None else "Unknown"),
                    "date":member.joined_at
                }
            )
        our_list = sorted(our_list, key=lambda x:x["date"].timestamp() if x["date"] != None else -1)
        p = pagination.MainMenu(pagination.FieldPageSource(
            entries=[("{}. {}".format(y+1,x["name"]), x["value"]) for y,x in enumerate(our_list)], 
            title="First Members to Join {} ({:,} total)".format(ctx.guild.name,len(ctx.guild.members)),
            per_page=15))

        try:
            await p.start(ctx)
        except menus.MenuError as e:
            await ctx.send(e)


    @commands.command(brief="Show the most recent users to join.")
    @commands.guild_only()
    async def recentjoins(self, ctx):
        """
        Usage: -recentjoins
        Output: Embed of most recent members to join the server.
        """
        our_list = []
        for member in ctx.guild.members:
            our_list.append(
                {
                    "name":member.display_name,
                    "value":"{} UTC".format(member.joined_at.strftime("%Y-%m-%d %I:%M %p") if member.joined_at != None else "Unknown"),
                    "date":member.joined_at
                }
            )
        our_list = sorted(our_list, key=lambda x:x["date"].timestamp() if x["date"] != None else -1, reverse=True)
        p = pagination.MainMenu(pagination.FieldPageSource(
            entries=[("{}. {}".format(y+1,x["name"]), x["value"]) for y,x in enumerate(our_list)], 
            title="First Members to Join {} ({:,} total)".format(ctx.guild.name,len(ctx.guild.members)),
            per_page=15))

        try:
            await p.start(ctx)
        except menus.MenuError as e:
            await ctx.send(e)


    # @commands.command(aliases=['listinvites','invitelist'], brief="List all current server invites.")
    # @commands.guild_only()
    # @permissions.has_permissions(manage_invites=True)
    # async def invites(self, ctx):
    #     """
    #     Usage: -invites
    #     Aliases: -listinvites -invitelist
    #     Output: Embed with all server invites listed
    #     Permission: Manage Messages
    #     """
    #     invites = await ctx.guild.invites()
    #     if len(invites) == 0:
    #         await ctx.send(f"{self.bot.emote_dict['error']} There currently no invites active.")
    #     else:
    #         try:
    #             em = discord.Embed(description="**Invites:**\n {0}".format(",\n ".join(map(str, invites))), color=self.bot.constants.embed)
    #             await ctx.send(embed=em)
    #         except: return await ctx.send(f"{self.bot.emote_dict['failed']} Too many invites to list.")


    @commands.command(aliases=['mc'], brief="Show how many messages a user has sent.")
    @commands.guild_only()
    async def messagecount(self, ctx, member: discord.Member = None):
        """
        Usage:  -messagecount [user]
        Alias:  -mc
        Output: Shows how many messages a user has sent on the server.
        Permission: Manage Messages
        Notes:
            Will default to yourself if no user is passed.
        """
        user = ctx.author if member is None else member
        query = '''SELECT COUNT(*) as c FROM messages WHERE author_id = $1 AND server_id = $2'''
        a = await self.bot.cxn.fetchrow(query, user.id, ctx.guild.id) or None
        if a is None:
            #await self.fix_member(ctx.author)
            return await ctx.send("`{}` has sent **0** messages.".format(user))
        else:
            a = int(a[0])
            await ctx.send(f"`{user}` has sent **{a}** message{'' if a == 1 else 's'}")


    @commands.command(brief="Show the top message senders in the server", aliases=['top'])
    @commands.guild_only()
    async def messagestats(self, ctx, limit: int = 100):
        """
        Usage: -messagestats
        Alias: -top
        Output: Top message senders in the server
        Permission: Manage Messages
        """

        query = '''SELECT 
                author_id, count(author_id) 
                FROM messages
                WHERE server_id = $1
                GROUP BY author_id
                ORDER BY COUNT(author_id) DESC
                LIMIT $2
                '''
        a = await self.bot.cxn.fetch(query, ctx.guild.id, limit)
        sum_query = '''SELECT COUNT(*) FROM messages WHERE server_id = $1'''
        b = await self.bot.cxn.fetchrow(sum_query, ctx.guild.id)
        b = b[0]
        p = pagination.SimplePages(entries=[f"<@!{row[0]}>. [ Messages: {row[1]} ]" for row in a], per_page=20)
        p.embed.title = "**{0}** messages by **{1}** users.".format(b, len([x for x in ctx.guild.members]))

        try:
            await p.start(ctx)
        except menus.MenuError as e:
            await ctx.send(e)

    @commands.command(brief="Show a user's nicknames.", aliases=["nicknames"])
    @commands.guild_only()
    async def nicks(self, ctx, user: discord.Member = None):
        """
        Usage: -nicks [user]
        Alias: -nicknames
        Output: Embed of all user's nicknames.
        Permission: Manage Messages
        Notes:
            Will default to yourself if no user is passed
        """
        if user is None:
            user = ctx.author
        query = '''SELECT nicknames FROM nicknames WHERE server_id = $1 AND user_id = $2'''
        name_list = await self.bot.cxn.fetchrow(query, ctx.guild.id, user.id)
        name_list = name_list[0].split(',')
        name_list = list(OrderedDict.fromkeys(name_list))

        p = pagination.SimplePages(entries=[f"`{n}`" for n in name_list])
        p.embed.title = f"Nicknames for {user}"

        try:
            await p.start(ctx)
        except menus.MenuError as e:
            await ctx.send(e)

    @commands.command(brief="Show a user's names.", aliases=["usernames"])
    @commands.guild_only()
    async def names(self, ctx, user: discord.Member = None):
        """
        Usage: -names [user]
        Alias: -usernames
        Output: Embed of all user's names.
        Permission: Manage Messages
        Notes:
            Will default to yourself if no user is passed
        """
        if user is None:
            user = ctx.author
        if user.bot:
            return await ctx.send(f"{self.bot.emote_dict['warning']} I do not track bots.")

        query = '''SELECT usernames FROM usernames WHERE user_id = $1'''
        name_list = await self.bot.cxn.fetchrow(query, user.id)
        name_list = name_list[0].split(',')
        name_list = list(OrderedDict.fromkeys(name_list))

        p = pagination.SimplePages(entries=[f"`{n}`" for n in name_list])
        p.embed.title = f"Usernames for {user}"

        try:
            await p.start(ctx)
        except menus.MenuError as e:
            await ctx.send(e)

    # @commands.command(brief="Show a user's avatars.", aliases=["avs"])
    # @commands.guild_only()
    # async def avatars(self, ctx, user: discord.Member = None):
    #     """
    #     Usage: -names [user]
    #     Alias: -usernames
    #     Output: Embed of all user's names.
    #     Permission: Manage Messages
    #     Notes:
    #         Will default to yourself if no user is passed
    #     """
    #     if user is None:
    #         user = ctx.author
    #     query = '''SELECT avatars FROM useravatars WHERE user_id = $1'''
    #     name_list = await self.bot.cxn.fetchrow(query, user.id)
    #     name_list = name_list[0].split(',')
    #     name_list = list(OrderedDict.fromkeys(name_list))

    #     p = pagination.SimplePages(entries=[f"`{n}`" for n in name_list], per_page=5)
    #     p.embed.title = f"Avatars for {user}"

    #     try:
    #         await p.start(ctx)
    #     except menus.MenuError as e:
    #         await ctx.send(e)

    

    @commands.command(brief="Check when a user was last observed", aliases=['lastseen','track','tracker'])
    @permissions.has_permissions(manage_messages=True)
    async def seen(self, ctx, user: converters.DiscordUser = None):
        """
        Usage:  -seen [user]
        Alias:  -lastseen, -track, -tracker
        Output: Get when a user was last observed on discord.
        Permission: Manage Messages
        Notes:
            User can be a mention, user id, or full discord 
            username with discrim Username#0001.
            Will default to yourself if no user is passed
        """
        if user is None:
            return await ctx.send(f"Usage: `{ctx.prefix}seen <user>`")

        if user.bot:
            return await ctx.send(f"{self.bot.emote_dict['warning']} I do not track bots.")

        tracker = self.bot.get_cog('Tracker')

        data = await tracker.last_observed(user)

        if data['last_seen'] is None:
            return await ctx.send(f"I have not seen `{user}`")
        
        await ctx.send(f"User `{user}` was last seen {data['last_seen']} ago.")
        

    @commands.command(brief="Show bot commands listed by popularity.")
    @commands.guild_only()
    async def commandstats(self, ctx, user: discord.Member = None, limit=100):
        """
        Usage: -commandstats [user] [limit]
        Output: Most popular commands
        Permission: Manage Messages
        """
        if user is None:
            query = '''SELECT command FROM commands WHERE server_id = $1'''
            command_list = await self.bot.cxn.fetch(query, ctx.guild.id)
            premsg = f"Commands most frequently used in **{ctx.guild.name}**"
        else:
            if user.bot:
                return await ctx.send(f"{self.bot.emote_dict['warning']} I do not track bots.")
            query = '''SELECT command FROM commands WHERE server_id = $1 AND user_id = $2'''
            command_list = await self.bot.cxn.fetch(query, ctx.guild.id, user.id)
            premsg = f"Commands most frequently used by **{user}**"
        formatted_list = []
        for c in command_list:
            formatted_list.append(c[0])

        counter = Counter(formatted_list)
        try:
            width = len(max(counter, key=len))
        except ValueError:
            return await ctx.send(f"{self.bot.emote_dict['error']} User `{user}` has not run any commands.")
        total = sum(counter.values())

        if limit > 0:
            common = counter.most_common(limit)
        else:
            common = counter.most_common()[limit:]
        output = '\n'.join('{0:<{1}} : {2}'.format(str(k), width, c)
                           for k, c in common)

        msg = "{0} \n\nTOTAL: {1}".format(output, total)
        #await ctx.send(premsg + '```yaml\n{}\n\nTOTAL: {}```'.format(output, total))
        pages = pagination.MainMenu(pagination.TextPageSource(msg, prefix="```yaml", max_size=500))
        if user is None:
            title = f"Most common commands used in **{ctx.guild.name}**"
        else:
            title = f"Most common commands used by **{user.display_name}**"

        await ctx.send(title)
        try:
            await pages.start(ctx)
        except menus.MenuError as e:
            await ctx.send(str(e))


    @commands.command(name="commands", brief="Show how many commands have been run.")
    @commands.guild_only()
    async def commandcount(self, ctx, user: discord.Member = None):
        '''
        Usage:  -commands [user]
        Output: Command count for the user or server
        Permission: Manage Messages
        Notes:
            If no user is passed, will show total server commands
        '''
        if user is None:
            query = '''SELECT COUNT(*) as c FROM commands WHERE server_id = $1'''
            command_count = await self.bot.cxn.fetchrow(query, ctx.guild.id)
            return await ctx.send(f"A total of **{command_count[0]:,}** command{' has' if int(command_count[0]) == 1 else 's have'} been executed on this server.")
        else:
            if user.bot:
                return await ctx.send(f"{self.bot.emote_dict['warning']} I do not track bots.")
            query = '''SELECT COUNT(*) as c FROM commands WHERE executor_id = $1 AND server_id = $2'''
            command_count = await self.bot.cxn.fetchrow(query, user.id, ctx.guild.id)
            return await ctx.send(f"User `{user}` has executed **{int(command_count[0]):,}** commands.")


    @commands.command(brief="Top bot users.",aliases=["botusage"])
    @commands.guild_only()
    async def usage(self, ctx, unit: str="month"):
        """
        Usage: -usage [unit of time]
        ALias: -botusage
        Output: Top bot users in the server
        Permission: Manage Messages 
        """
        unit = unit.lower()
        time_dict = {
            "day": 86400,
            "week": 604800,
            "month": 2592000,
            "year": 31556952
        }
        if unit not in time_dict:
            unit = "month"
        query = '''SELECT COUNT(*) as c, author_id FROM commands WHERE server_id = $1 GROUP BY author_id ORDER BY c DESC LIMIT 25'''
        usage = await self.bot.cxn.fetch(query, ctx.guild.id)
        e = discord.Embed(title=f"Bot usage for the last {unit}", description=f"{sum(x[0] for x in usage)} commands from {len(usage)} user{'' if len(usage) == 1 else 's'}", color=self.bot.constants.embed)
        for n, v in enumerate(usage[:24]):
            name = await self.bot.fetch_user(v[1])
            e.add_field(name=f"{n+1}. {name}", value=f"{v[0]} command{'' if int(v[0]) == 1 else 's'}")
        
        await ctx.send(embed=e)


    @commands.group(brief="Show the most active server members", invoke_without_command=True)
    @commands.guild_only()
    async def activity(self, ctx, unit: str="month"):
        """
        Usage: -activity [characters] [unit of time]
        Output: Top message senders in the server
        Permission: Manage Messages
        """
        unit = unit.lower()
        time_dict = {
            "day": 86400,
            "week": 604800,
            "month": 2592000,
            "year": 31556952
        }
        if unit not in time_dict:
            unit = "month"
        time_seconds = time_dict.get(unit, 2592000)
        now = int(datetime.datetime.utcnow().timestamp())
        diff = now - time_seconds
        query = '''SELECT COUNT(*) as c, author_id FROM messages WHERE server_id = $1 AND unix > $2 GROUP BY author_id ORDER BY c DESC LIMIT 25'''
        stuff = await self.bot.cxn.fetch(query, ctx.guild.id, diff)

        e = discord.Embed(title=f"Activity for the last {unit}", description=f"{sum(x[0] for x in stuff)} messages from {len(stuff)} user{'' if len(stuff) == 1 else 's'}", color=self.bot.constants.embed)
        for n, v in enumerate(stuff[:24]):
            try:
                name = ctx.guild.get_member(int(v[1])).name
            except AttributeError:
                name = f"Unknown member"
            e.add_field(name=f"{n+1}. {name}", value=f"{v[0]} message{'' if int(v[0]) == 1 else 's'}")
        
        await ctx.send(embed=e)


    @activity.command(aliases=['characters'])
    @commands.guild_only()
    async def char(self, ctx, unit: str="day"):
        if ctx.author.id not in self.bot.constants.owners:
            return
        unit = unit.lower()
        time_dict = {
            "day": 86400,
            "week": 604800,
            "month": 2592000,
            "year": 31556952
        }
        if unit not in time_dict:
            unit = "month"
        time_seconds = time_dict.get(unit, 2592000)
        now = int(datetime.datetime.utcnow().timestamp())
        diff = now - time_seconds
        query = '''SELECT SUM(LENGTH(content)) as c, author_id, COUNT(*) FROM messages WHERE server_id = $1 AND unix > $2 GROUP BY author_id ORDER BY c DESC LIMIT 25'''
        stuff = await self.bot.cxn.fetch(query, ctx.guild.id, diff)
        e = discord.Embed(title="Current leaderboard", description=f"Activity for the last {unit}", color=self.bot.constants.embed)
        for n, v in enumerate(stuff): 
            try:
                name = ctx.guild.get_member(int(v[1])).name
            except AttributeError:
                name = "Unknown member"
            #ratio = int(v[0] / 1440)
            #e.add_field(name=f"{n+1}. {name}", value=f"{v[0]:,} chars ({ratio} chars/minute)")
            e.add_field(name=f"{n+1}. {name}", value=f"{v[0]:,} chars")
        
        await ctx.send(embed=e)


    @commands.command(brief="Most used words.")
    @commands.guild_only()
    async def words(self, ctx, member: discord.Member=None, limit:int = 20):
        """
        Usage: -words [user]
        Output: Most commonly used words by the passed user
        Permission: Manage Messages
        Notes:
            Will default to yourself if no user is passed.
        """
        if member is None:
            member = ctx.author

        if member.bot:
            return await ctx.send(f"{self.bot.emote_dict['warning']} I do not track bots.")

        all_msgs = await self.bot.cxn.fetch('''SELECT content FROM messages WHERE author_id = $1 AND server_id = $2''', member.id, ctx.guild.id)
        all_msgs = [x[0] for x in all_msgs]
        all_msgs = ' '.join(all_msgs).split()
        all_msgs = list(filter(lambda x: len(x) > 0, all_msgs))
        all_words = (Counter(all_msgs).most_common()[:limit])
        msg = ""
        for i in all_words:
            msg += f'Uses: [{str(i[1]).zfill(2)}] Word: {i[0]}\n'
        pages = pagination.MainMenu(pagination.TextPageSource(msg, prefix="```ini", max_size=1000))
        await ctx.send(f"Most common words sent by **{member.display_name}**")
        try:
            await pages.start(ctx)
        except menus.MenuError as e:
            await ctx.send(str(e))


    @commands.command(brief="Usage for a word.")
    @commands.guild_only()
    async def word(self, ctx, word: str = None, member: discord.Member = None):
        """
        Usage: -word [user] [word]
        Output: Number of times a word has been used by a user
        Permission: Manage Messages
        Notes:
            Will default to you if no user is passed.
        """
        if word is None:
            return await ctx.send(f"Usage: `{ctx.prefix}word [user] <word>`")
        if member is None:
            member = ctx.author
        if member.bot:
            return await ctx.send(f"{self.bot.emote_dict['warning']} I do not track bots.")

        all_msgs = await self.bot.cxn.fetch('''SELECT content FROM messages WHERE author_id = $1 AND server_id = $2''', member.id, ctx.guild.id)
        all_msgs = [x[0] for x in all_msgs]
        all_msgs = ' '.join(all_msgs).split()
        all_msgs = list(filter(lambda x: len(x) > 0, all_msgs))
        all_msgs = ' '.join(all_msgs).split()
        all_msgs = list(all_msgs)
        all_words = (Counter(all_msgs).most_common())
        found = []
        for x in all_words:
            if x[0] == word:
                found.append(x)
                found.append(int(all_words.index(x)) + 1)
        if found == []:
            return await ctx.send(f"The word `{word}` has never been used by **{member.display_name}**")
        if str(found[1]).endswith("1") and found[1] != 11:
            common = str(found[1]) + "st"
        elif str(found[1]).endswith("2") and found[1] != 12:
            common = str(found[1]) + "nd"
        elif str(found[1]).endswith("3") and found[1] != 13:
            common = str(found[1]) + "rd"
        else:
            common = str(found[1]) + "th"
        await ctx.send(f"The word `{word}` has been used {found[0][1]} time{'' if found[0][1] == 1 else 's'} and is the {common} most common word used by **{member.display_name}**")


    @commands.command(brief="Emoji usage tracking.")
    @commands.guild_only()
    async def emojistats(self, ctx):
        async with ctx.channel.typing():
            msg = await ctx.send(f"{self.bot.emote_dict['loading']} **Collecting Emoji Statistics**")
            query = """SELECT (emoji_id, total) FROM emojistats WHERE server_id = $1 ORDER BY total DESC;"""

            emoji_list = []
            result = await self.bot.cxn.fetch(query, ctx.guild.id)
            for x in result:
                try:
                    emoji = await ctx.guild.fetch_emoji(int(x[0][0]))
                    emoji_list.append((emoji, x[0][1]))

                except Exception:
                    continue


            p = pagination.SimplePages(entries = ['{}: Uses: {}'.format(e[0], e[1]) for e in emoji_list], per_page = 15)
            p.embed.title = f"Emoji usage stats in **{ctx.guild.name}**"
            await msg.delete()
            try:
                await p.start(ctx)
            except menus.MenuError as e:
                await ctx.send(e)


    # @commands.command(brief="Emoji usage tracking.")
    # @commands.guild_only()
    # async def emojistats(self, ctx, member: discord.Member = None):
    #     async with ctx.channel.typing():
    #         if member is None:
    #             msg = await ctx.send(f"{self.bot.emote_dict['loading']} **Collecting Emoji Statistics**")
    #             query = """SELECT content FROM messages WHERE content ~ '<a?:.+?:([0-9]{15,21})>' AND server_id = $1;"""

    #             stuff = await self.bot.cxn.fetch(query, ctx.guild.id)
    #             fat_msg = ""
    #             for x in stuff:
    #                 fat_msg += '\n'.join(x)
    #             matches = EMOJI_REGEX.findall(fat_msg)

    #             emoji_list = []
    #             for x in matches:
    #                 try:
    #                     emoji = await ctx.guild.fetch_emoji(int(x))
    #                 except discord.NotFound:
    #                     continue
    #                 emoji_list.append(emoji)

    #             emoji_list = Counter(emoji_list)
    #             emoji_list = emoji_list.most_common()

    #             p = pagination.SimplePages(entries = ['{}: Uses: {}'.format(e[0], e[1]) for e in emoji_list], per_page = 15)
    #             p.embed.title = f"Emoji usage stats in **{ctx.guild.name}**"
    #             await msg.delete()
    #             try:
    #                 await p.start(ctx)
    #             except menus.MenuError as e:
    #                 await ctx.send(e)
    #         else:
    #             msg = await ctx.send(f"{self.bot.emote_dict['loading']} **Collecting Emoji Statistics**")
    #             query = """SELECT content FROM messages WHERE content ~ '<a?:.+?:([0-9]{15,21})>' AND server_id = $1 AND author_id = $2;"""

    #             stuff = await self.bot.cxn.fetch(query, ctx.guild.id, member.id)
    #             fat_msg = ""
    #             for x in stuff:
    #                 fat_msg += '\n'.join(x)
    #             matches = EMOJI_REGEX.findall(fat_msg)
    #             emoji_list = []

    #             for x in matches:
    #                 try:
    #                     emoji = await ctx.guild.fetch_emoji(int(x))
    #                 except discord.NotFound:
    #                     continue
    #                 emoji_list.append(emoji)

    #             emoji_list = Counter(emoji_list)
    #             emoji_list = emoji_list.most_common()
    #             p = pagination.SimplePages(entries = ['{}: Uses: {}'.format(e[0], e[1]) for e in emoji_list], per_page = 15)
    #             p.embed.title = f"Emoji usage stats for **{member.display_name}**"
    #             await msg.delete()
    #             try:
    #                 await p.start(ctx)
    #             except menus.MenuError as e:
    #                 await ctx.send(e)


    @commands.command(brief="Get usage stats on an emoji.")
    async def emoji(self, ctx, emoji: converters.SearchEmojiConverter = None):
        """
        Usage: -emoji <custom emoji>
        Output: Usage stats on the passed emoji
        """
        async with ctx.channel.typing():
            if emoji is None:
                return await ctx.send(f"Usage: `{ctx.prefix}emoji <custom emoji>`")
            emoji_id = emoji.id

            msg = await ctx.send(f"{self.bot.emote_dict['loading']} **Collecting Emoji Statistics**")
            query = f"""SELECT (author_id, content) FROM messages WHERE content ~ '<a?:.+?:{emoji_id}>';"""

            stuff = await self.bot.cxn.fetch(query)

            emoji_users = []
            for x in stuff:
                emoji_users.append(x[0][0])

            fat_msg = ""
            for x in stuff:
                fat_msg += x[0][1]

            emoji_users = Counter(emoji_users).most_common()

            matches = re.compile(f"<a?:.+?:{emoji_id}>").findall(fat_msg)
            total_uses = len(matches)

            p = pagination.SimplePages(entries = ['`{}`: Uses: {}'.format(await self.bot.fetch_user(u[0]), u[1]) for u in emoji_users], per_page = 15)
            p.embed.title = f"Emoji usage stats for {emoji} (Total: {total_uses})"
            await msg.delete()
            try:
                await p.start(ctx)
            except menus.MenuError as e:
                await ctx.send(e)

      #####################
     ## Emoji Task Loop ##
    #####################

    @tasks.loop(seconds=2.0)
    async def bulk_inserter(self):

        #============#
        # On Message #
        #============#
        # query = """INSERT INTO emojistats (server_id, emoji_id, total)
                #    VALUES ($1, $2, $3) ON CONFLICT (server_id, emoji_id)
                #    DO UPDATE SET total = emoji_stats.total + excluded.total;
                # """

        query = """INSERT INTO emojistats (serveremoji, server_id, emoji_id, total)
                   VALUES ($1, $2, $3, $4) ON CONFLICT (serveremoji) DO UPDATE
                   SET total = emojistats.total + excluded.total;
                """

        async with self.batch_lock:
            for data in self.emoji_batch.items():
                server_id = data[0]
                for key in data[1]:
                    emoji_id = key
                count = data[1][emoji_id]
                await self.bot.cxn.execute(query, f"{server_id}:{emoji_id}", server_id, emoji_id, count)
            self.bot.emojis_seen += len(self.emoji_batch.items())
            self.emoji_batch.clear()
        

    @commands.Cog.listener()
    async def on_message(self, message):
        if self.bot.bot_ready is False:
            return
        if message.author.bot:
            return
        if not message.guild:
            return

        matches = EMOJI_REGEX.findall(message.content)
        if not matches:
            return
        async with self.batch_lock:
            self.emoji_batch[message.guild.id].update(map(int, matches))

