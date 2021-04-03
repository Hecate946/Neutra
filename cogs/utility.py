import os
import io
import pytz
import json
import discord
from datetime import datetime
from discord.ext import commands
from .help import COG_EXCEPTIONS

from utilities import utils, permissions, pagination, converters
import discord
import pytz
from   discord.ext import commands, menus

def setup(bot):
    bot.add_cog(Utility(bot))


class Utility(commands.Cog):
    """
    Module for utility functions.
    """
    def __init__(self, bot):
        self.bot = bot

    def _get_help(self, command, max_len = 0):
        # A helper method to return the command help - or a placeholder if none
        if max_len == 0:
            # Get the whole thing
            if command.help == None:
                return "No description..."
            else:
                return command.help
        else:
            if command.help == None:
                c_help = "No description..."
            else:
                c_help = command.help.split("\n")[0]
            return (c_help[:max_len-3]+"...") if len(c_help) > max_len else c_help

    def _is_submodule(self, parent, child):
        return parent == child or child.startswith(parent + ".")

    @commands.command(
        brief   = "Sends a list of commands and descriptions to your DMs.", 
        aliases = ["txthelp","helpfile"]
    )
    async def dumphelp(self, ctx):
        """
        Usage: -dumphelp
        Aliases: -txthelp, -helpfile
        Output: List of commands and descriptions
        """
        timestamp = datetime.today().strftime("%m-%d-%Y")

        if not os.path.exists("./data/wastebin"):
            # Create it
            os.makedirs("./data/wastebin")

        help_txt = './data/wastebin/Help-{}.txt'.format(timestamp)

        message = await ctx.send('Uploading help list...')
        msg = ''
        prefix = ctx.prefix
        
        # Get and format the help
        for cog in sorted(self.bot.cogs):
            if cog.upper() in COG_EXCEPTIONS:
                continue
            cog_commands = sorted(self.bot.get_cog(cog).get_commands(), key=lambda x:x.name)
            cog_string = ""
            # Get the extension
            the_cog = self.bot.get_cog(cog)
            # Make sure there are non-hidden commands here
            visible = []
            for command in self.bot.get_cog(cog).get_commands():
                if not command.hidden:
                    visible.append(command)
            if not len(visible):
                # All hidden - skip
                continue
            cog_count = "1 command" if len(visible) == 1 else "{} commands".format(len(visible))
            for e in self.bot.extensions:
                b_ext = self.bot.extensions.get(e)
                if self._is_submodule(b_ext.__name__, the_cog.__module__):
                    # It's a submodule
                    cog_string += "{}{} Cog ({}) - {}.py Extension:\n".format(
                        "    ",
                        cog,
                        cog_count,
                        e[5:]
                    )
                    break
            if cog_string == "":
                cog_string += "{}{} Cog ({}):\n".format(
                    "    ",
                    cog,
                    cog_count
                )
            for command in cog_commands:
                cog_string += "{}  {}\n".format("    ", prefix + command.name + " " + command.signature)
                cog_string += "\n{}  {}  {}\n\n".format(
                    "\t",
                    " "*len(prefix),
                    self._get_help(command, 80)
                )
            cog_string += "\n"
            msg += cog_string
        
        # Encode to binary
        # Trim the last 2 newlines
        msg = msg[:-2].encode("utf-8")
        with open(help_txt, "wb") as myfile:
            myfile.write(msg)

        await ctx.send(file=discord.File(help_txt))
        await message.edit(content=f"{self.bot.emote_dict['success']} Uploaded Help-{timestamp}.txt")
        os.remove(help_txt)

    @commands.command(hidden=True, brief="Sends a list of all my servers to your DMs.")
    @commands.is_owner()
    async def dumpservers(self, ctx):
        """Dumps a timestamped list of servers."""
        timestamp = datetime.today().strftime("%Y-%m-%d %H.%M")
        server_file = 'Servers-{}.txt'.format(timestamp)

        mess = await ctx.send('Saving servers to **{}**...'.format(server_file))

        msg = ''
        for server in self.bot.guilds:
            msg += "Name:    " + server.name              + "\n"
            msg += "ID:      " + str(server.id)           + "\n"
            msg += "Owner:   " + str(server.owner)        + "\n"
            msg += "Members: " + str(len(server.members)) + "\n"
            msg += "\n\n"

        data = io.BytesIO(msg.encode('utf-8'))

        await mess.edit(content='Uploading `{}`...'.format(server_file))
        try:
            await ctx.author.send(file=discord.File(data, filename=server_file))
        except:
            await ctx.send(file=discord.File(data, filename=server_file))
            await mess.edit(content='{} Uploaded `{}`.'.format(self.bot.emote_dict['success'], server_file))
            return
        await mess.edit(content='{} Uploaded `{}`.'.format(self.bot.emote_dict['success'], server_file))
        await mess.add_reaction(self.bot.emote_dict['letter'])


    @commands.command(brief="Sends a file to your DMs with the server's settings.", aliases=['serversettings'])
    @commands.guild_only()
    @permissions.has_permissions(manage_guild=True)
    async def dumpsettings(self, ctx):
        """
        Usage: -dumpsettings
        Alias: -serversettings
        Permission: Manage Server
        Output: Sends a json file of server settings to your DMs.
        """
        
        timestamp = datetime.today().strftime("%Y-%m-%d %H.%M")
        settings_file = 'Settings-{}.json'.format(timestamp)

        mess = await ctx.send('Saving settings to **{}**...'.format(settings_file))

        settings = self.bot.server_settings[ctx.guild.id]

        utils.write_json(settings_file, settings)

        await mess.edit(content='Uploading `{}`...'.format(settings_file))
        try:
            await ctx.author.send(file=discord.File(settings_file, filename=settings_file.replace('json', 'txt')))
        except:
            await ctx.send(file=discord.File(settings_file, filename=settings_file.replace('json', 'txt')))
            await mess.edit(content='{} Uploaded `{}`.'.format(self.bot.emote_dict['success'], settings_file))
            os.remove(settings_file)
            return
        await mess.edit(content='{} Uploaded `{}`.'.format(self.bot.emote_dict['success'], settings_file))
        await mess.add_reaction(self.bot.emote_dict['letter'])
        os.remove(settings_file)


    @commands.command(brief="Sends a txt file to your DMs with a list of server roles.")
    @commands.guild_only()
    @permissions.has_permissions(manage_messages=True)
    async def dumproles(self, ctx):
        """
        Usage:  -dumproles
        Alias:  -txtroles
        Output:  Sends a list of roles for the server to your DMs
        Permission: Manage Messages
        """
        timestamp = datetime.today().strftime("%Y-%m-%d %H.%M")
        role_file = 'Roles-{}.txt'.format(timestamp)

        mess = await ctx.send('Saving roles to **{}**...'.format(role_file))

        allroles = ""

        for num, role in enumerate(sorted(ctx.guild.roles, reverse=True), start=1):
            allroles += f"[{str(num).zfill(2)}] {role.id}\t{role.name}\t[ Users: {len(role.members)} ]\r\n"

        data = io.BytesIO(allroles.encode('utf-8'))

        await mess.edit(content='Uploading `{}`...'.format(role_file))
        try:
            await ctx.author.send(file=discord.File(data, filename=role_file))
        except:
            await ctx.send(file=discord.File(data, filename=role_file))
            await mess.edit(content='{} Uploaded `{}`.'.format(self.bot.emote_dict['success'], role_file))
            return
        await mess.edit(content='{} Uploaded `{}`.'.format(self.bot.emote_dict['success'], role_file))
        await mess.add_reaction(self.bot.emote_dict['letter'])


    @commands.command(brief="Sends a txt file to your DMs with a list of server emojis.", aliases=['dumpemojis'])
    @commands.guild_only()
    @permissions.has_permissions(manage_messages=True)
    async def dumpemotes(self, ctx):
        """
        Usage:  -dumpemotes
        Alias:  -dumpemojis
        Output:  Sends a list of server emojis to your DMs
        Permission: Manage Messages
        """
        timestamp = datetime.today().strftime("%Y-%m-%d %H.%M")
        role_file = 'Emotes-{}.txt'.format(timestamp)

        mess = await ctx.send('Saving emotes to **{}**...'.format(role_file))

        allemotes = ""

        for num, emote in enumerate(sorted(ctx.guild.emojis, key=lambda a: str(a.url).endswith('gif')), start=1):
            allemotes += f"[{str(num).zfill(len(str(len(ctx.guild.emojis))))}]\tID: {emote.id}\tURL: {emote.url}\t{emote.name}\t\r\n"

        data = io.BytesIO(allemotes.encode('utf-8'))

        await mess.edit(content='Uploading `{}`...'.format(role_file))
        try:
            await ctx.author.send(file=discord.File(data, filename=role_file))
        except:
            await ctx.send(file=discord.File(data, filename=role_file))
            await mess.edit(content='{} Uploaded `{}`.'.format(self.bot.emote_dict['success'], role_file))
            return
        await mess.edit(content='{} Uploaded `{}`.'.format(self.bot.emote_dict['success'], role_file))
        await mess.add_reaction(self.bot.emote_dict['letter'])


    @commands.command(aliases=['logmessages','messagedump'], brief="Dumps a formatted txt file of channel messages.")
    @commands.guild_only()
    @permissions.has_permissions(manage_server=True)
    async def dumpmessages(self, ctx, messages : int = 25, *, chan : discord.TextChannel = None):
        """
        Usage:      -dumpmessages [message amount] [channel]
        Aliases:    -messagedump, -dumpmessages, logmessages
        Permission: Manage Server
        Output: 
            Logs a passed number of messages from a specified channel 
            - 25 by default.
        """

        timestamp = datetime.today().strftime("%Y-%m-%d %H.%M")
        log_file = 'Logs-{}.txt'.format(timestamp)

        if not chan:
            chan = ctx

        mess = await ctx.send('Saving logs to **{}**...'.format(log_file))

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
        
        await mess.edit(content='Uploading `{}`...'.format(log_file))
        try:
            await ctx.author.send(file=discord.File(data, filename=log_file))
        except:
            await ctx.send(file=discord.File(data, filename=log_file))
            await mess.edit(content='{} Uploaded `{}`.'.format(self.bot.emote_dict['success'], log_file))
            return
        await mess.edit(content='{} Uploaded `{}`.'.format(self.bot.emote_dict['success'], log_file))
        await mess.add_reaction(self.bot.emote_dict['letter'])


    @commands.command(aliases=['timezonelist','listtimezones'], brief="Sends a formatted txt file of time zones.")
    @commands.guild_only()
    @permissions.has_permissions(manage_server=True)
    async def dumptimezones(self, ctx):
        """
        Usage:      -dumptimezones
        Aliases:    -listtimezones, -timezonelist
        Output: 
            Sends a txt file to your DMs with all
            available timezones to set using -settz
        """

        timestamp = datetime.today().strftime("%Y-%m-%d %H.%M")
        time_file = 'Timezones-{}.txt'.format(timestamp)

        mess = await ctx.send('Saving logs to **{}**...'.format(time_file))

        all_tz = pytz.all_timezones

        msg = ""
        for x in all_tz:
            msg += f"{x}\n"
        
        data = io.BytesIO(msg.encode("utf-8"))
        await mess.edit(content='Uploading `{}`...'.format(time_file))
        try:
            await ctx.author.send(file=discord.File(data, filename=time_file))
        except:
            await ctx.send(file=discord.File(data, filename=time_file))
            await mess.edit(content='{} Uploaded `{}`.'.format(self.bot.emote_dict['success'], time_file))
            return
        await mess.edit(content='{} Uploaded `{}`.'.format(self.bot.emote_dict['success'], time_file))
        await mess.add_reaction(self.bot.emote_dict['letter'])


    async def get_datetime(self, member):
        a = None
        tzerror = False
        query = '''SELECT timezone FROM usertime WHERE user_id = $1'''
        timezone = await self.bot.cxn.fetchval(query, member.id) or None
        try:
            if timezone:
                tz = timezone
                a = pytz.timezone(tz)
        except pytz.exceptions.UnknownTimeZoneError:
            tzerror = True
        return datetime.now(a), tzerror

    @commands.command()
    async def timenow(self, ctx, twenty_four_hour_time = True):
        """Date time module."""

        dandt, tzerror = await self.get_datetime(ctx.author)
        em = discord.Embed(color=self.bot.constants.embed)
        if twenty_four_hour_time is True:
            em.add_field(name=u'\u23F0 Time', value="{:%H:%M:%S}".format(dandt), inline=True)
        else:
            em.add_field(name=u'\u23F0 Time', value="{:%I:%M:%S %p}".format(dandt), inline=True)
        em.add_field(name=u'\U0001F4C5 Date', value="{:%d %B %Y}".format(dandt), inline=True)
        if tzerror:
            em.add_field(name=u'\u26A0 Warning', value="Invalid timezone specified, system timezone was used instead.", inline=True)

        await ctx.send(content=None, embed=em)
        msg = '**Local Date and Time:** ```{:Time: %H:%M:%S\nDate: %Y-%m-%d```}'.format(dandt)
        await ctx.send(msg)

    @commands.command(brief="Remove your timezone", aliases=['rmtz', 'removetz', 'removetimzone', 'rmtimezone', 'remtimezone'])
    async def remtz(self, ctx):
        """Remove your timezone"""

        await self.bot.cxn.execute("DELETE FROM usertime WHERE user_id = $1;", ctx.author.id)
        await ctx.send(f"{self.bot.emote_dict['success']} Your timezone has been removed.")


    @commands.command(brief="Set your timezone.", aliases=['settimezone', 'settime'])
    async def settz(self, ctx, *, tz_search = None):
        """List all the supported timezones."""

        msg = ""
        if tz_search is None:
            title = "Available Timezones"
            entry = [x for x in pytz.all_timezones]
            p = pagination.SimplePages(entry, per_page=20, index=False, desc_head="```prolog\n", desc_foot="```")
            p.embed.title = title
            try:
                await p.start(ctx)
            except menus.MenuError as e:
                await ctx.send(e)
        else:
            tz_list = utils.disambiguate(tz_search, pytz.all_timezones, None, 5)
            if not tz_list[0]['ratio'] == 1:
                edit = True
                tz_list = [x['result'] for x in tz_list]
                index, message = await pagination.Picker(
                    embed_title="Select one of the 5 closest matches.",
                    list=tz_list,
                    ctx=ctx
                ).pick(embed=True, syntax="prolog")

                if index < 0:
                    return await message.edit(content=f"{self.bot.emote_dict['info']} Timezone selection cancelled.", embed=None)

                selection = tz_list[index]
            else:
                edit = False
                selection = tz_list[0]['result']

            query = '''INSERT INTO usertime VALUES ($1, $2) ON CONFLICT (user_id) DO UPDATE SET timezone = $2 WHERE usertime.user_id = $1;'''
            await self.bot.cxn.execute(query, ctx.author.id, selection)
            msg = f"{self.bot.emote_dict['success']} Timezone set to `{selection}`"
            if edit:
                await message.edit(content=msg, embed=None)
            else:
                await ctx.send(msg)

    @commands.command()
    async def tz(self, ctx, *, member: converters.DiscordUser = None):
        """See a member's timezone."""

        if member is None:
            member = ctx.message.author

        query = '''SELECT timezone FROM usertime WHERE user_id = $1'''
        timezone = await self.bot.cxn.fetchval(query, member.id) or None
        if timezone is None:
            return await ctx.send(f"{self.bot.emote_dict['error']} `{member}` has not set their timezone. Use the `{ctx.prefix}settz [Region/City]` command.")

        await ctx.send(f'`{member}\'` timezone is *{timezone}*')


    @commands.command(brief="Get a members time")
    async def time(self, ctx, *, member: discord.Member = None):
        """Get a members time"""
        timenow = utils.getClockForTime(datetime.utcnow().strftime("%I:%M %p"))
        timezone = None
        if member is None:
            member = ctx.author


        tz = await self.bot.cxn.fetchval('''SELECT timezone FROM usertime WHERE user_id = $1;''', member.id) or None
        if tz is None:
            msg = f'`{member}` hasn\'t set their timezone or offset yet - they can do so with `{ctx.prefix}settz [Region/City]` command.\nThe current UTC time is **{timenow}**.'
            await ctx.send(msg)
            return

        t = self.getTimeFromTZ(tz)
        if t is None:
            await ctx.send(f"{self.bot.emote_dict['failed']} I couldn't find that timezone.")
            return
        t["time"] = utils.getClockForTime(t["time"])
        if member:
            msg = f'It\'s currently **{t["time"]}** where {member.display_name} is.'
        else:
            msg = '{} is currently **{}**'.format(t["zone"], t["time"])

        await ctx.send(msg)

    def getTimeFromTZ(self, tz, t = None):
        # Assume sanitized zones - as they're pulled from pytz
        # Let's get the timezone list
        tz_list = utils.disambiguate(tz, pytz.all_timezones, None, 3)
        if not tz_list[0]['ratio'] == 1:
            # We didn't find a complete match
            return None
        zone = pytz.timezone(tz_list[0]['result'])
        if t == None:
            zone_now = datetime.now(zone)
        else:
            zone_now = t.astimezone(zone)
        return { "zone" : tz_list[0]['result'], "time" : zone_now.strftime("%I:%M %p") }
