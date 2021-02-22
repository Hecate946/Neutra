import datetime
import discord
import io
import logging
import sys
import functools

from discord.ext import commands
from lib.db import db
from lib.bot import owners
from utilities import default

from collections import OrderedDict, Counter

def setup(bot):
    if not hasattr(bot, 'command_stats'):
        bot.command_stats = Counter()

    if not hasattr(bot, 'socket_stats'):
        bot.socket_stats = Counter()

    bot.add_cog(Statistics(bot))

# This is the Bot module - it contains things like nickname, status, etc
log = logging.getLogger()

class Statistics(commands.Cog):
    """
    Statistics on users, activity, and more.
    """
    def __init__(self, bot):
        self.bot = bot


    def fix_member(self, member):
        roles = ','.join([str(x.id)
                                for x in member.roles if x.name != "@everyone"])
        names = member.display_name
        db.execute('''INSERT OR IGNORE INTO users
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                    roles, str(member.guild.id), None, member.id, names, 0, 0, 0)

    def set_messagecount(self, message):
        if message.guild is None:
            return
        db.execute('UPDATE users SET messagecount = messagecount + 1 WHERE (id=? AND server=?)',
                    message.author.id, message.guild.id)           
    

    @commands.command(aliases=['listinvites','invitelist'], pass_context=True, brief="List all current server invites.")
    async def invites(self, ctx):
        """
        Usage: -invites
        Aliases: -listinvites -invitelist
        Output: Embed with all server invites listed
        """
        invites = await ctx.guild.invites()
        if len(invites) == 0:
            await ctx.send("`:warning: There currently no invites active.`")
        else:
            try:
                em = discord.Embed(description="**Invites:**\n {0}".format(",\n ".join(map(str, invites))), color=ctx.guild.me.color)
                await ctx.send(embed=em)
            except: return await ctx.send(f"<:fail:812062765028081674> Too many invites to list.")

    @commands.command()
    async def words(self, ctx, *, member: discord.Member=None):
        if member is None:
            member = ctx.author

        all_msgs = db.records('''SELECT content FROM messages WHERE server=? AND author=?''', ctx.guild.id, member.id)
        all_msgs = [x[0] for x in all_msgs]
        all_msgs = ' '.join(all_msgs).split()
        all_msgs = list(filter(lambda x: len(x) > 3 and x.startswith != "!", all_msgs))
        all_words = (Counter(all_msgs).most_common()[:20])
        msg = ""
        integer = 0
        for i in all_words:
            integer += 1
            msg += f'[{str(integer).zfill(2)}] {str(i)}\n'
        
        await ctx.send(f"```ini\n{msg}```")


    @commands.command(aliases=['mc'], brief="Find exactly how many messages a user has sent in the server.")
    @commands.guild_only()
    async def messagecount(self, ctx, member: discord.Member = None):
        """
        Usage:  -messagecount [user]
        Alias:  -mc
        Output: Shows how many messages a user has sent on the server.
        Notes:
            Will default to yourself if no user is passed.
        """
        user = ctx.author if member is None else member
        a = db.record('SELECT messagecount FROM users WHERE server=? AND id=?', ctx.guild.id, user.id) or (None)
        if a is None:
            self.fix_member(ctx.author)
            return await ctx.send("`{}` has sent **0** messages.".format(user))
        else:
            a = int(str(a).strip("(),'"))
            await ctx.send(f"`{user}` has sent **{a}** message{'' if a == 1 else 's'}")


    @commands.command(brief="Show the top message senders in the server", pass_context=True)
    @commands.guild_only()
    async def top(self, ctx):
        """
        Usage: -top
        Output: Top message senders in the server
        """
        a = db.records(
            'SELECT * FROM users WHERE (server=? AND messagecount > 0) ORDER BY messagecount DESC LIMIT 20', ctx.guild.id,)
        b = db.records(
            'SELECT SUM(messagecount) AS "hello" FROM users WHERE (server=? AND messagecount > 0)', ctx.guild.id,)
        b = b[0]
        post_this = ""
        rank = 1
        for row in a:
            name = f'<@{row[3]}>'
            post_this += ("{}. {} (Messages: {})\n".format(rank, name, row[5]))
            rank += 1
        post_this += "\n**{0}** messages by **{1}** users.".format(
            b, len([x for x in ctx.guild.members]))
        em = discord.Embed(
                           description=post_this, colour=default.config()["embed_color"])
        em.set_author(name=self.bot.user.name,
                      icon_url=self.bot.user.avatar_url)
        await ctx.send(embed=em)


    @commands.command(brief="Show all past and current nicknames for a user on the server.", aliases=["nicknames"])
    @commands.guild_only()
    async def nicks(self, ctx, user: discord.Member = None):
        """
        Usage: -nicks [user]
        Alias: -nicknames
        Output: Embed of all user's nicknames.
        Notes:
            Will default to yourself if no user is passed
        """
        if user is None:
            user = ctx.author
        name_list = db.record('''SELECT nicknames
                          FROM users
                          WHERE (server=? AND id=?)''',
                       str(ctx.guild.id), user.id)
        name_list = name_list[0].split(',')
        name_list = list(OrderedDict.fromkeys(name_list))
        msg = ""
        integer = 0
        for i in name_list:
            integer += 1
            msg += f"{str(integer).zfill(2)}. `{i}`\n"
        
        embed = discord.Embed(color=default.config()["embed_color"])
        embed.description = msg
        embed.set_author(name=f"{user.name}'s Nicknames")
        await ctx.send(embed=embed)

    @commands.Cog.listener()
    async def on_command(self, ctx):
        try:
            db.execute(
                """ UPDATE users 
                    SET commandcount = commandcount + 1 
                    WHERE id = ? 
                    AND server = ? 
                """, ctx.author.id, ctx.guild.id
            )
        except AttributeError:
            return

        command = ctx.command.qualified_name
        self.bot.command_stats[command] += 1
        message = ctx.message
        destination = None
        if ctx.guild is None:
            destination = 'Private Message'
            guild_id = None
        else:
            destination = '#{0.channel} [{0.channel.id}] ({0.guild}) [{0.guild.id}]'.format(message)
            guild_id = ctx.guild.id

        log.debug('{0.created_at}: {0.author} in {1}: {0.content}'.format(
            message, destination))

    @commands.Cog.listener()
    async def on_socket_response(self, msg):
        self.bot.socket_stats[msg.get('t')] += 1


    @commands.command(hidden=True)
    async def socketstats(self, ctx, limit=20):

        delta = datetime.datetime.utcnow() - self.bot.uptime
        minutes = delta.total_seconds() / 60
        total = sum(self.bot.socket_stats.values())
        cpm = total / minutes
        width = len(max(self.bot.socket_stats, key=lambda x: len(str(x))))
        con = self.bot.socket_stats.most_common(limit)
        fancy = '\n'.join('{0:<{1}}: {2:>12,}'.format(str(k), width, c)
                         for k, c in con)

        await ctx.send('{0:,} socket events observed ({1:.2f}/minute):\n```yaml\n{2}```'.format(total, cpm, fancy))
    @commands.command(hidden=True)
    @commands.is_owner()
    async def commandstats(self, ctx, limit=20):
        counter = self.bot.command_stats
        width = len(max(counter, key=len))
        total = sum(counter.values())

        if limit > 0:
            common = counter.most_common(limit)
        else:
            common = counter.most_common()[limit:]
        output = '\n'.join('{0:<{1}}: {2}'.format(k, width, c)
                           for k, c in common)

        await ctx.send('```yaml\n{}\n```'.format(output))


    def get_activity(self, g, diff):
        db.record('''SELECT count(*) as c, author
                          FROM messages
                          WHERE (server=? AND unix > ?)
                          GROUP BY author
                          ORDER BY c DESC;''',
                          (g.id, diff))



    @commands.group(invoke_without_command=True)
    async def activity(self, ctx, unit: str="month"):

        if ctx.author.id not in owners or not ctx.author.guild_permissions.administrator: return
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
        thing = functools.partial(self.get_activity, ctx.guild, diff)
        #record = await self.bot.loop.run_in_executor(None, thing)
        stuff = db.records('''SELECT count(*) as c, author
                          FROM messages
                          WHERE (server=? AND unix > ?)
                          GROUP BY author
                          ORDER BY c DESC;''',
                          ctx.guild.id, diff)
        e = discord.Embed(title=f"Activity for the last {unit}", description=f"{sum(x[0] for x in stuff)} messages from {len(stuff)} users", color=default.config()["embed_color"])
        for n, v in enumerate(stuff[:25]):
            try:
                name = ctx.guild.get_member(int(v[1])).name
            except AttributeError:
                name = f"Unknown member"
            e.add_field(name=f"{n+1}. {name}", value=f"{v[0]} messages")
        
        await ctx.send(embed=e)


    @activity.command(aliases=['characters'])
    async def char(self, ctx, unit: str="day"):
        if ctx.author.id not in owners and ctx.author.guild_permissions.administrator:
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
        stuff = db.records('''SELECT SUM(LENGTH(content)) as c, author, COUNT(*)
                          FROM messages
                          WHERE (server=? AND unix > ?)
                          GROUP BY author
                          ORDER BY c DESC LIMIT 25;''',
                          ctx.guild.id, diff)
        e = discord.Embed(title="Current leaderboard", description=f"Activity for the last {unit}", color=default.config()["embed_color"])
        for n, v in enumerate(stuff): 
            try:
                name = ctx.guild.get_member(int(v[1])).name
            except AttributeError:
                name = "Unknown member"
            ratio = int(v[0] / 1440)
            e.add_field(name=f"{n+1}. {name}", value=f"{v[0]:,} chars ({ratio} chars/minute)")
        
        await ctx.send(embed=e)

    @commands.command(brief="👀 Check a user's eyecount 👀", aliases=['👀','eyecount'])
    @commands.guild_only()
    async def eyes(self, ctx, user: discord.Member = None):
        """
        Usage:   -eyes [user]
        Aliases: -eyecount 👀
        Output:  👀 Check a user's eyecount 👀
        Notes:
            Will default to yourself if no user is passed
        """
        if user is None:
            user = ctx.author
        eyes = db.record("""
        SELECT eyecount FROM users WHERE id = ? AND server = ?
        """, user.id, ctx.guild.id)

        await ctx.send(f"👀 User `{user}` has sent {eyes[0]} 👀 emoji{'' if int(eyes[0]) == 1 else 's'}")


    @commands.command(brief="Get how long ago a user was seen by the bot.", aliases=['seen'])
    async def lastseen(self, ctx, *, user: discord.User):
        """
        Usage:  -lastseen [user]
        Alias:  -seen
        Output: Get when a user was last seen on discord.
        Notes:
            User can be a mention, user id, or full discord 
            username with discrim Username#0001.
            Will default to yourself if no user is passed
        """

        sql = db.record('SELECT LastSeen FROM last_seen WHERE UserID = ?', user.id) or (None)
        if str(sql) == "None": return await ctx.send(f"I have not seen `{user}`")

        sql = str(sql).strip("()',")

        everything = []
        try:
            first_time = datetime.datetime.strptime(sql, '%Y-%m-%d %H:%M:%S.%f')
        except ValueError: return await ctx.send(f"I have not seen `{user}.`")
        later_time = datetime.datetime.utcnow()
        difference = later_time - first_time
        seconds_in_day = 24 * 60 * 60
        elapsed = divmod(difference.days * seconds_in_day + difference.seconds, 60)
        args = str(elapsed).strip("()").replace(",","").split(" ")
        seconds = args[1]
        everything.append(str(seconds) + " seconds")

        if int(args[0]) > 60:
            elapsed2 = divmod(int(args[0]), 60)
            args2 = str(elapsed2).strip("()").replace(",","").split(" ")
            minutes = args2[1]
            everything.append(str(minutes) + f" minute{'' if int(minutes) == 1 else 's'}")

            if int(args2[0]) > 24:
                elapsed3 = divmod(int(args2[0]), 24)
                args3 = str(elapsed3).strip("()").replace(",","").split(" ")
                hours = args3[1]
                everything.append(str(hours) + f" hour{'' if int(hours) == 1 else 's'}")

                if int(args3[0]) > 30:
                    elapsed4 = divmod(int(args2[0]), 30)
                    args4 = str(elapsed4).strip("()").replace(",","").split(" ")
                    days = args4[1]
                    everything.append(str(days) + f" day{'' if int(days) == 1 else 's'}")

                    if int(args4[0]) > 12:
                        elapsed5 = divmod(int(args2[0]), 12)
                        args5 = str(elapsed5).strip("()").replace(",","").split(" ")
                        months = args5[1]
                        years = args5[0]
                        everything.append(str(months) + f" month{'' if int(months) == 1 else 's'}")
                        everything.append(str(years) + f" year{'' if int(years) == 1 else 's'}")
                    else:
                        months = args4[0]
                        everything.append(str(months) + f" month{'' if int(months) == 1 else 's'}")
                else:
                    days = args3[0]
                    everything.append(str(days) + f" day{'' if int(days) == 1 else 's'}")
            else:
                hours = args2[0]
                everything.append(str(hours) + f" hour{'' if int(hours) == 1 else 's'}")
        else:
            minutes = args[0]
            everything.append(str(minutes) + f" minute{'' if int(minutes) == 1 else 's'}")


        everything.reverse()
        everything = str(everything).strip("[]").replace("'","")
        msg = f"User: `{user}` was last seen **{everything}** ago"
        await ctx.send(msg)


      #####################
     ## Event Listeners ##
    #####################

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot: return None
        db.execute("""
        INSERT OR REPLACE INTO last_seen (UserID, Username, LastSeen) VALUES (?, ?, ?)
        """, int(message.author.id), str(message.author), datetime.datetime.utcnow())

        if not message.guild: return
        
        message_eyes = 0

        trigger = '👀'
        for x in str(message.content):
            if x == trigger:
                message_eyes += 1

        db.execute("""
        UPDATE users SET eyecount = eyecount + ? WHERE id = ? AND server = ?
        """, message_eyes, message.author.id, message.guild.id)

        self.set_messagecount(message)
        if message.content == "":
            return
        db.execute("""
        INSERT INTO messages VALUES (?, ?, ?, ?, ?, ?, ?)
        """, message.created_at.timestamp(), 
             message.created_at.strftime('%Y-%m-%d %H:%M:%S'), 
             message.clean_content, 
             message.id, 
             message.author.id, 
             message.channel.id, 
             message.guild.id)


    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        user = await self.bot.fetch_user(payload.user_id)
        db.execute("INSERT OR REPLACE INTO last_seen VALUES (?, ?, ?)", user.id, str(user), datetime.datetime.utcnow())


    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        db.execute("INSERT OR REPLACE INTO last_seen VALUES (?, ?, ?)", after.id, str(after), datetime.datetime.utcnow())


    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        db.execute("INSERT OR REPLACE INTO last_seen VALUES (?, ?, ?)", member.id, str(member), datetime.datetime.utcnow())


    @commands.Cog.listener()
    async def on_user_update(self, before, after):
        db.execute("INSERT OR REPLACE INTO last_seen VALUES (?, ?, ?)", after.id, str(after), datetime.datetime.utcnow())


    @commands.Cog.listener()
    async def on_invite_create(self, invite):
        db.execute("INSERT OR REPLACE INTO last_seen VALUES (?, ?, ?)", invite.inviter.id, str(invite.inviter), datetime.datetime.utcnow())


    @commands.Cog.listener()
    async def on_typing(self, channel, user, when):
        db.execute("INSERT OR REPLACE INTO last_seen VALUES (?, ?, ?)", user.id, str(user), datetime.datetime.utcnow())


    @commands.Cog.listener()
    async def on_member_join(self, user):
        db.execute("INSERT OR REPLACE INTO last_seen VALUES (?, ?, ?)", user.id, str(user), datetime.datetime.utcnow())


    @commands.Cog.listener()
    async def on_member_leave(self, user):
        db.execute("INSERT OR REPLACE INTO last_seen VALUES (?, ?, ?)", user.id, str(user), datetime.datetime.utcnow())



    async def on_member_join(self, member):
        a = db.records('SELECT * FROM users WHERE (id=? AND server=?)', member.id, member.guild.id)
        if a != []:
            return
        roles = ','.join([str(x.id) for x in member.roles if (
            x.name != "@everyone")])
        db.execute("INSERT INTO users VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                       (roles, member.guild.id, None, member.id, member.display_name, 0, 0, 0))
        # xd = self.c.execute(
        #     'SELECT * FROM userconfig WHERE (guild_id=? AND user_id=?)', (member.guild.id, member.id))
        # xd = xd.fetchall()
        # if xd == []:
        #     self.c.execute('INSERT INTO userconfig VALUES (?, ?, ?, ?, ?, ?)',
        #                    (member.guild.id, member.id, None, None, False, None))
        #     self.conn.commit()

    async def on_guild_join(self, guild):
        #db.execute('INSERT OR IGNORE  INTO servers VALUES (?, ?, ?, ?, ?, ?)',
        #                (guild.id, None, None, None, None, '?,!'))
        #db.execute('INSERT OR IGNORE INTO logging VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
        #                (guild.id, 1, 1, 1, 1, 1, 1, 1, None))
#
        #db.execute('''INSERT OR IGNORE INTO role_config
        #                VALUES (?, ?, ?, ?, ?)''',
        #            (None, False, guild.id, None, True))
        #db.execute('''INSERT OR IGNORE INTO config
        #                VALUES (?, ?, ?, ?, ?, ?)''',
        #            (guild.id, None, None, True, None, None))
        for member in guild.members:
            roles = ','.join(
                [str(x.id) for x in member.roles if x.name != "@everyone"])
            db.execute("INSERT OR IGNORE INTO users VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                        (roles, member.guild.id, None, member.id, member.display_name, 0, 0, 0))
            # self.c.execute('''SELECT *
            #                   FROM userconfig
            #                   WHERE (user_id=? AND guild_id=?)''',
            #                 (member.id, member.guild.id))
            # userconfig = self.c.fetchall()
            # if userconfig == []:
            #     self.c.execute('''INSERT INTO userconfig VALUES (?, ?, ?, ?, ?, ?)''',
            #     (member.guild.id, member.id, None, None, False, None))
            #     self.conn.commit()
