import io
import os
import re
import pytz
import discord
import requests
from datetime import datetime
from discord.ext import commands
from .help import COG_EXCEPTIONS

from utilities import utils, permissions, pagination, converters, image
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


      ##############################
     ## Aiohttp Helper Functions ##
    ##############################

    async def query(self, url, method="get", res_method="text", *args, **kwargs):
        async with getattr(self.bot.session, method.lower())(url, *args, **kwargs) as res:
            return await getattr(res, res_method)()


    async def get(self, url, *args, **kwargs):
        return await self.query(url, "get", *args, **kwargs)


    async def post(self, url, *args, **kwargs):
        return await self.query(url, "post", *args, **kwargs)


    def _get_help(self, command, max_len = 0):
        # A helper method to return the command help - or a placeholder if none
        if max_len == 0:
            # Get the whole thing
            if command.help is None:
                return "No description..."
            else:
                return command.help
        else:
            if command.help is None:
                c_help = "No description..."
            else:
                c_help = command.help.split("\n")[0]
            return (c_help[:max_len-3]+"...") if len(c_help) > max_len else c_help

    def _is_submodule(self, parent, child):
        return parent == child or child.startswith(parent + ".")

    @commands.command(
        brief   = "DMs you a file of commands and descriptions.", 
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


    @commands.command(brief="DMs you a file with the server's settings.", aliases=['serversettings'])
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


    @commands.command(brief="DMs you a file of server roles.")
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


    @commands.command(brief="DMs you a file of server emojis.", aliases=['dumpemojis'])
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
        emote_list = sorted(ctx.guild.emojis, key=lambda e: str(e.name))

        for num, emote in enumerate(sorted(emote_list, key=lambda a: str(a.url).endswith('gif')), start=1):
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


    @commands.command(aliases=['logmessages','messagedump'], brief="DMs you a file of channel messages.")
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


    @commands.command(aliases=['timezonelist','listtimezones'], brief="DMs you a file of time zones.")
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

    @commands.command(brief="Show the current time.")
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

    @commands.command(brief="Remove your timezone.", aliases=['rmtz', 'removetz', 'removetimzone', 'rmtimezone', 'remtimezone'])
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

    @commands.command(brief="See a member's timezone.", aliases=['tz'])
    async def timezone(self, ctx, *, member: converters.DiscordUser = None):
        """See a member's timezone."""

        if member is None:
            member = ctx.message.author

        query = '''SELECT timezone FROM usertime WHERE user_id = $1'''
        timezone = await self.bot.cxn.fetchval(query, member.id) or None
        if timezone is None:
            return await ctx.send(f"{self.bot.emote_dict['error']} `{member}` has not set their timezone. Use the `{ctx.prefix}settz [Region/City]` command.")

        await ctx.send(f'`{member}\'` timezone is *{timezone}*')


    @commands.command(brief="Show what time it is for a member.")
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
        if t is None:
            zone_now = datetime.now(zone)
        else:
            zone_now = t.astimezone(zone)
        return { "zone" : tz_list[0]['result'], "time" : zone_now.strftime("%I:%M %p") }


    def _get_emoji_url(self, emoji):
        if len(emoji) < 3:
            # Emoji is likely a built-in like :)
            h = "-".join([hex(ord(x)).lower()[2:] for x in emoji])
            return ("https://github.com/twitter/twemoji/raw/master/assets/72x72/{}.png".format(h),h)
        # Must be a custom emoji
        emojiparts = emoji.replace("<","").replace(">","").split(":") if emoji else []
        if not len(emojiparts) == 3: return None
        # Build a custom emoji object
        emoji_obj = discord.PartialEmoji(animated=len(emojiparts[0]) > 0, name=emojiparts[1], id=emojiparts[2])
        # Return the url
        return (emoji_obj.url,emoji_obj.name)

    def _get_emoji_mention(self, emoji):
        return "<{}:{}:{}>".format("a" if emoji.animated else "",emoji.name,emoji.id)


    @commands.command(hidden=True)
    async def be(self, ctx, emoji = None):
        '''Outputs the passed emoji... but bigger!'''
        if emoji is None:
            await ctx.send("Usage: `{}emoji [emoji]`".format(ctx.prefix))
            return
        # Get the emoji
        emoji_url = self._get_emoji_url(emoji)
        if not emoji_url:
            return await ctx.send("Usage: `{}emoji [emoji]`".format(ctx.prefix))
        f = await image.download(emoji_url[0])
        if not f: return await ctx.send("I could not access that emoji.")
        await ctx.send(file=discord.File(f))
        os.remove(f)


    def find_emoji(self, msg):
        msg = re.sub("<a?:(.+):([0-9]+)>", "\\2", msg)
        color_modifiers = ["1f3fb", "1f3fc", "1f3fd", "1f44c", "1f3fe", "1f3ff"]  # These color modifiers aren't in Twemoji
        
        name = None

        for guild in self.bot.guilds:
            for emoji in guild.emojis:
                if msg.strip().lower() in emoji.name.lower():
                    name = emoji.name + (".gif" if emoji.animated else ".png")
                    url = emoji.url
                    id = emoji.id
                    guild_name = guild.name
                if msg.strip() in (str(emoji.id), emoji.name):
                    name = emoji.name + (".gif" if emoji.animated else ".png")
                    url = emoji.url
                    return name, url, emoji.id, guild.name
        if name:
            return name, url, id, guild_name

        # Here we check for a stock emoji before returning a failure
        codepoint_regex = re.compile('([\d#])?\\\\[xuU]0*([a-f\d]*)')
        unicode_raw = msg.encode('unicode-escape').decode('ascii')
        codepoints = codepoint_regex.findall(unicode_raw)
        if codepoints == []:
            return "", "", "", ""

        if len(codepoints) > 1 and codepoints[1][1] in color_modifiers:
            codepoints.pop(1)

        if codepoints[0][0] == '#':
            emoji_code = '23-20e3'
        elif codepoints[0][0] == '':
            codepoints = [x[1] for x in codepoints]
            emoji_code = '-'.join(codepoints)
        else:
            emoji_code = "3{}-{}".format(codepoints[0][0], codepoints[0][1])
        url = "https://raw.githubusercontent.com/astronautlevel2/twemoji/gh-pages/128x128/{}.png".format(emoji_code)
        name = "emoji.png"
        return name, url, "N/A", "Official"


    @commands.command(brief="View enlarged emojis.", aliases=['bigemotes', 'bigemojis', 'bigemote', 'bem'])
    async def bigemoji(self, ctx, *, emojis = None):
        """
        Usage: bigemoji [info] <emojis>
        Aliases: -bigemote, -bigemojis, -bigemotes, -be
        Output: Large version of the passed emoji
        Notes:
            Pass the optional info argument to show
            the emoji's server, name, and url.
        """
        if emojis is None:
            return await ctx.send(f"Usage: `{ctx.prefix}bigemoji [info] <emojis>`")
        msg = emojis

        emojis = msg.split()
        if msg.startswith('info '):
            emojis = emojis[1:]
            get_guild = True
        else:
            get_guild = False

        if len(emojis) > 5:
            raise commands.BadArgument("Maximum of 5 emojis at a time.")

        images = []
        for emoji in emojis:
            name, url, id, guild = self.find_emoji(emoji)
            if url == "":
                downloader = self.bot.get_command('be')
                await downloader(ctx, emoji)
            response = requests.get(url, stream=True)
            if response.status_code == 404:
                downloader = self.bot.get_command('be')
                await downloader(ctx, emoji)
                continue

            img = io.BytesIO()
            for block in response.iter_content(1024):
                if not block:
                    break
                img.write(block)
            img.seek(0)
            images.append((guild, str(id), url, discord.File(img, name)))

        for (guild, id, url, fp) in images:
            if ctx.channel.permissions_for(ctx.author).attach_files:
                if get_guild:
                    await ctx.send('**ID:** {}\n**Server:** {}\n**URL: {}**'.format(id, guild, url))
                    await ctx.send(file=fp)
                else:
                    await ctx.send(file=fp)
            else:
                if get_guild:
                    await ctx.send('**ID:** {}\n**Server:** {}\n**URL: {}**'.format(id, guild, url))
                    await ctx.send(url)
                else:
                    await ctx.send(url)
            fp.close()


    @commands.command(aliases=["emojisteal", "emojicopy", "emotesteal"], brief="Copy a custom emoji from another server and add it.")
    @commands.guild_only()
    @permissions.has_permissions(manage_emojis=True)
    async def emotecopy(self, ctx, *, msg):
        """Copy a custom emoji from another server and add it."""
        msg = re.sub("<:(.+):([0-9]+)>", "\\2", msg)

        match = None
        exact_match = False
        for guild in self.bot.guilds:
            if ctx.author not in guild.members:
                continue
            for emoji in guild.emojis:
                if msg.strip().lower() in str(emoji):
                    match = emoji
                if msg.strip() in (str(emoji.id), emoji.name):
                    match = emoji
                    exact_match = True
                    break
            if exact_match:
                break

        if not match:
            return await ctx.send(f"{self.bot.emote_dict['failed']} No emoji found in servers you share with me.")
        response = await self.get(str(match.url), res_method="read")
        try:
            emoji = await ctx.guild.create_custom_emoji(name=match.name, image=response)
            await ctx.send(f"{self.bot.emote_dict['success']} Successfully added the emoji {emoji.name} <{'a' if emoji.animated else ''}:{emoji.name}:{emoji.id}>")
        except discord.HTTPException:
            await ctx.send(f"{self.bot.emote_dict['failed']} No available emoji slots.")


    @commands.command(brief="Add an emoji to the server.", aliases=['addemoji', 'addemote', 'emojiadd'])
    @commands.guild_only()
    @commands.bot_has_guild_permissions(manage_emojis = True)
    @permissions.has_permissions(manage_emojis = True)
    async def emoteadd(self, ctx, *, emoji = None, name = None):
        '''Adds the passed emoji, url, or attachment as a custom emoji.'''

        if not len(ctx.message.attachments) and emoji == name is None:
            return await ctx.send("Usage: `{}addemoji [emoji, url, attachment] [name]`".format(ctx.prefix))

        if len(ctx.message.attachments):
            name = emoji
            emoji = " ".join([x.url for x in ctx.message.attachments])
            if name: 
                emoji += " "+name

        emojis_to_add = []
        last_name = []
        for x in emoji.split():
            # Check for a url
            urls = utils.get_urls(x)
            if len(urls):
                url = (urls[0], os.path.basename(urls[0]).split(".")[0])
            else:
                # Check for an emoji
                url = self._get_emoji_url(x)
                if not url:
                    # Gotta be a part of the name - add it
                    last_name.append(x)
                    continue
            if len(emojis_to_add) and last_name:
                # Update the previous name if need be
                emojis_to_add[-1][1] = "".join([z for z in "_".join(last_name) if z.isalnum() or z == "_"])
            # We have a valid url or emoji here - let's make sure it's unique
            if not url[0] in [x[0] for x in emojis_to_add]:
                emojis_to_add.append([url[0],url[1]])
            # Reset last_name
            last_name = []
        if len(emojis_to_add) and last_name:
            # Update the final name if need be
            emojis_to_add[-1][1] = "".join([z for z in "_".join(last_name) if z.isalnum() or z == "_"])
        if not emojis_to_add:
            return await ctx.send(f"Usage: `{ctx.prefix}addemoji [emoji, url, attachment] [name]`")
        # Now we have a list of emojis and names
        added_emojis = []
        allowed = len(emojis_to_add) if len(emojis_to_add)<=10 else 10
        omitted = " ({} omitted, beyond the limit of {})".format(len(emojis_to_add)-10,10) if len(emojis_to_add)>10 else ""
        message = await ctx.send("Adding {} emoji{}{}...".format(
            allowed,
            "" if allowed==1 else "s",
            omitted))
        for emoji_to_add in emojis_to_add[:10]:
            # Let's try to download it
            emoji,e_name = emoji_to_add # Expand into the parts
            f = await self.get(str(emoji), res_method="read")
            if not f:
                await message.edit(content=f"{self.bot.emote_dict['failed']} Could not read emoji.")
                continue
            # Clean up
            if not e_name.replace("_",""):
                continue
            # Create the emoji and save it
            try:
                new_emoji = await ctx.guild.create_custom_emoji(name=e_name,image=f,roles=None,reason="Added by {}#{}".format(ctx.author.name,ctx.author.discriminator))
            except discord.HTTPException:
                await message.edit(content=f"{self.bot.emote_dict['failed']} Out of emoji slots.")
                continue
            except Exception:
                continue
            added_emojis.append(new_emoji)
        if len(added_emojis):
            msg = f"{self.bot.emote_dict['success']} Created {len(added_emojis)} emote{'' if len(added_emojis) == 1 else 's'}:"
            msg += "\n\n"
            emoji_text = ["{} - `:{}:`".format(self._get_emoji_mention(x),x.name) for x in added_emojis]
            msg += "\n".join(emoji_text)
            await message.edit(content=msg)


    @commands.command(aliases=['emoteremove', 'removeemoji', 'removeemote'], brief="Remove an emoji from the server.")
    @commands.guild_only()
    @commands.bot_has_guild_permissions(manage_emojis = True)
    @permissions.has_permissions(manage_emojis=True)
    async def emojiremove(self, ctx, name):
        """Remove an emoji from the current server."""
        emotes = [x for x in ctx.guild.emojis if x.name == name]
        emote_length = len(emotes)
        if not emotes:
            return await ctx.send("No emotes with that name could be found on this server.")
        for emote in emotes:
            await emote.delete()
        if emote_length == 1:
            await ctx.send("Successfully removed the {} emoji!".format(name))
        else:
            await ctx.send("Successfully removed {} emoji with the name {}.".format(emote_length, name))


    @commands.command(aliases=['se', 'nitro'], brief="Send an emoji using the bot.")
    async def sendemoji(self, ctx, msg: str = None):
        '''Sends an emoji'''
        if msg is None:
            await ctx.send("Usage: `{}emoji [emoji]`".format(ctx.prefix))
            return

        msg = re.sub("<:(.+):([0-9]+)>", "\\2", msg)

        match = None
        exact_match = False
        for guild in self.bot.guilds:
            for emoji in guild.emojis:
                if msg.strip().lower() in str(emoji):
                    match = emoji
                if msg.strip() in (str(emoji.id), emoji.name):
                    match = emoji
                    exact_match = True
                    break
            if exact_match:
                break

        if not match:
            return await ctx.send('Could not find emoji.')
        
        # await ctx.send(match.url)
        await ctx.send(match)


    @commands.command(aliases=["listemojis"], brief="Shows all server emojis")
    async def listemotes(self, ctx):
        """Displays all emotes avaiable on a server."""
        title = "Available Emojis"
        width = max([len(x.name) for x in ctx.guild.emojis])
        entry = [f"{x.name: <{width}}: {x.id}" for x in ctx.guild.emojis]
        p = pagination.SimplePages(entry, per_page=20, index=False, desc_head="```yaml\n", desc_foot="```")
        p.embed.title = title
        try:
            await p.start(ctx)
        except menus.MenuError as e:
            await ctx.send(e)

    # TODO use TextPageSource and make this decent.

    # @commands.command(aliases=['es'], brief="Scan all servers for an emoji.")
    # async def emojiscan(self, ctx, msg):
    #     """Scan all servers for a certain emote"""
    #     bool = None
    #     servers = ""
    #     emote = msg.split(":")[1] if msg.startswith("<") else msg
    #     for guild in self.bot.guilds:
    #         if ctx.author not in guild.members:
    #             continue
    #         if len(servers + "{}\n".format(guild.name)) > 2000:
    #             bool = False
    #             break
    #         for emoji in guild.emojis:
    #             if emoji.name == emote:
    #                 servers += guild.name + "\n"
    #     if servers is None:
    #         await ctx.send("That emote is not on any of your servers.")
    #     else:
    #         if len(servers) <= 1964 and bool is False:
    #             servers += "**Could not print the rest, sorry.**"
    #         elif bool is False:
    #             bool = True
    #         try:
    #             embed = discord.Embed(title="Servers with the {} emote".format(msg), color=ctx.guild.me.color)
    #             embed.description = servers
    #             await ctx.send(embed=embed)
    #         except:
    #             await ctx.send("```{}```".format(servers))
    #         if bool is True:
    #             await ctx.send("**Could not print the rest, sorry**")
