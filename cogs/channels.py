import asyncio
import discord
import random

from discord.ext import commands

from utilities import permissions, default, converters
from core import bot
from core import OWNERS


def setup(bot):
    bot.add_cog(Channels(bot))


class Channels(commands.Cog):
    """
    Moderate your server's channels.
    """
    def __init__(self, bot):
        self.bot = bot
        self.cxn = bot.connection


    @commands.command(brief="Move a member from one voice channel into another")
    @commands.guild_only()
    @commands.bot_has_permissions(move_members=True)
    @permissions.has_permissions(move_members=True)
    async def vcmove(self, ctx, targets:commands.Greedy[discord.Member] = None, channel:str = None):
        """
        Usage:      -vcmove <target> <target>... <channel>
        Output:     Moves members into a new voice channel
        Permission: Move Members
        """
        if not targets: return await ctx.send(f"Usage: `{ctx.prefix}vc move <to channel> <target> [target]...`")
        if not channel: return await ctx.send(f"Usage: `{ctx.prefix}vc move <to channel> <target> [target]...`")
        voice = []
        try:
            voicechannel = ctx.guild.get_channel(int(channel))
        except Exception as e:
            try:
                voicechannel = discord.utils.get(ctx.guild.voice_channels, name = channel)
            except Exception as e:
                await ctx.send(e)
        for target in targets:
            if target.id in OWNERS: return await ctx.send('You cannot move my master.')
            if ctx.author.top_role.position < target.top_role.position and ctx.author.id not in OWNERS: return await ctx.send('You cannot move other staff members')
            try:
                await target.edit(voice_channel=voicechannel)
            except discord.HTTPException:
                await ctx.send("<:error:816456396735905844> Target is not connected to a voice channel")
            voice.append(target)
        if voice:
            vckicked = []
            for member in voice: 
                users = []
                people = await self.bot.fetch_user(int(member.id))
                users.append(people)
                for user in users:
                    username = f"{user.name}#{user.discriminator}"
                    vckicked += [username]
            await ctx.send('<:checkmark:816534984676081705> VC Moved `{0}`'.format(", ".join(vckicked)))


    @commands.command(brief="Kick members from a voice channel")
    @commands.guild_only()
    @commands.bot_has_permissions(move_members=True)
    @permissions.has_permissions(move_members=True)
    async def vckick(self, ctx, targets:commands.Greedy[discord.Member] = None):
        """
        Usage:      -vckick <target> <target>
        Output:     Kicks passed members from their channel
        Permission: Move Members
        """
        if not len(targets): return await ctx.send(f"Usage: `{ctx.prefix}vc kick <target> [target]...`")
        voice = []
        for target in targets:
            if ctx.author.top_role.position <= target.top_role.position and ctx.author.id not in OWNERS or ctx.author.id != ctx.guild.owner.id: return await ctx.send('<:fail:816521503554273320> You cannot move other staff members')
            try:
                await target.edit(voice_channel=None)
            except discord.HTTPException:
                await ctx.send("<:error:816456396735905844> Target is not connected to a voice channel")
            voice.append(target)
        if voice:
            vckicked = []
            for member in voice: 
                users = []
                people = await self.bot.fetch_user(int(member.id))
                users.append(people)
                for user in users:
                    username = f"{user.name}#{user.discriminator}"
                    vckicked += [username]
            await ctx.send('<:checkmark:816534984676081705> VC Kicked `{0}`'.format(", ".join(vckicked)))


    @commands.group(brief="Find and destroy a channel")
    @commands.guild_only()
    @commands.bot_has_permissions(manage_channels=True)
    @permissions.has_permissions(manage_guild=True, manage_channels=True)
    async def destroy(self, ctx):
        """
        Usage:      -destroy <option> <name/id/mention>
        Example:    -destroy textchannel General just-chatting
        Permission: Manage Channels, Manage Server
        Output:
            Destroys a channel.
        Option: 
            textchannel  (Alias: tc)
            voicechannel (Alias: vc)
        """
        if ctx.invoked_subcommand is None:
            await ctx.send_help(str(ctx.command))


    @destroy.group(aliases=['tc'])
    @commands.guild_only()
    @commands.bot_has_permissions(manage_channels=True)
    async def textchannel(self, ctx, textchannel: discord.TextChannel = None):
        """ Destroy a text channel """
        if textchannel is None: return await ctx.send(f"Usage: `{ctx.prefix}destroy tc <ID/name>`")
        try:
            await textchannel.delete()
            await ctx.send(f'Text channel **{textchannel}** has been deleted by {ctx.author.display_name}')
        except:
            return await ctx.send('I couldn\'t find that text channel')


    @destroy.group(aliases=['vc'])
    async def voicechannel(self, ctx, voicechannel: discord.VoiceChannel = None):
        """ Destroy a voice channel """
        if voicechannel is None: return await ctx.send(f"Usage: `{ctx.prefix}destroy vc <ID/name>`")
        try:
            await voicechannel.delete()
            await ctx.send(f'Voice channel **{voicechannel}** has been deleted by {ctx.author.display_name}')
        except:
            return await ctx.send('I couldn\'t find that voice channel')


    @commands.group(brief="Create a channel (Command Group")
    @commands.guild_only()
    @commands.bot_has_permissions(manage_channels=True)
    @permissions.has_permissions(manage_channels=True)
    async def create(self, ctx):
        """
        Usage: -create <option> [category] <name>
        Example: -create textchannel General just-chatting
        Permission: Manage Channels
        Output:
            Creates a channel under your optionally
            specified category.
        Option: 
            textchannel (Alias: tc)
            voicechannel (Alias: vc)
        """
        if ctx.invoked_subcommand is None:
            await ctx.send_help(str(ctx.command))


    @create.group(aliases=['textchannel'])
    async def tc(self, ctx, category: discord.CategoryChannel = None, *, name: str = None):
        """ Creates a text channel """
        if name is None: return await ctx.send(f"Usage: `{ctx.prefix}create tc [category] <name>`")
        guild = ctx.message.guild
        try:
            await guild.create_text_channel(name, category=category)
            await ctx.send(f'<:checkmark:816534984676081705> Text channel **{name}** has been created by {ctx.author.display_name}')
        except Exception as e: raise


    @create.group(aliases=['voicechannel'])
    async def vc(self, ctx, category: discord.CategoryChannel = None, *, name: str = None):
        """ Creates a voice channel """
        if name is None: return await ctx.send(f"Usage: `{ctx.prefix}create vc [category] <name>`")
        guild = ctx.message.guild
        try:
            await guild.create_voice_channel(name, category=category)
            await ctx.send(f'<:checkmark:816534984676081705> Voice channel **{name}** has been created by {ctx.author.display_name}')
        except:
            return await ctx.send('<:fail:816521503554273320> I couldn\'t create that voice channel')


    @commands.command(brief="Set the slowmode of the current channel in seconds.")
    @commands.guild_only()
    @commands.bot_has_permissions(manage_channels=True)
    @permissions.has_permissions(manage_channels=True)
    async def slowmode(self, ctx, time: int):
        """
        Usage:      -slowmode [seconds]
        Output:     Sets the channel's slowmode to your input value.
        Permission: Manage Channels
        """
        try:
            await ctx.channel.edit(slowmode_delay=time)
        except discord.HTTPException as e:
            await ctx.send(f'<:fail:816521503554273320> Failed to set slowmode because of an error\n{e}')
        else:
            await ctx.send(f'<:checkmark:816534984676081705> Slowmode set to `{time}s`')


    @commands.command(pass_context=True, aliases=["lockdown","lockchannel"], brief="Lock message sending in a channel.")
    @commands.guild_only()
    @commands.bot_has_permissions(manage_channels=True)
    @permissions.has_permissions(manage_channels=True)
    async def lock(self, ctx, channel:str = None, minutes: int = None):
        """
        Usage:      -lock [channel] [minutes]
        Output:     Locked channel for the specified time. Infinite if not specified
        Permission: Manage Channels
        """
        try:
            channel_id = int(channel)
            channel = ctx.guild.get_channel(channel_id)
        except:
            try:
                channel_obj = discord.utils.get(ctx.guild.text_channels, name=channel)
                if channel_obj is None: 
                    channel = ctx.channel
                else:
                    channel = channel_obj
            except Exception as e: return await ctx.send(e)
        if channel is None: 
            channel = ctx.channel
        try:
            overwrites_everyone = channel.overwrites_for(ctx.guild.default_role)
            everyone_overwrite_current = overwrites_everyone.send_messages
            locked = await self.cxn.fetchrow("SELECT ChannelID FROM lockedchannels WHERE ChannelID = ?", channel.id) or (None)
            if locked is not None: return await ctx.send(f"<:locked:810623219677397013> Channel {channel.mention} is already locked. ID: `{channel.id}`")
            msg = await ctx.send(f"Locking channel {channel.mention}...")
            await self.cxn.execute("INSERT INTO lockedchannels VALUES (?, ?, ?, ?, ?, ?, ?)", 
                                                                                channel.id, 
                                                                                channel.name, 
                                                                                ctx.guild.id, 
                                                                                ctx.guild.name, 
                                                                                ctx.author.id, 
                                                                                str(ctx.author), 
                                                                                str(everyone_overwrite_current))

            overwrites_everyone.send_messages = False
            await ctx.message.channel.set_permissions(ctx.guild.default_role, overwrite=overwrites_everyone, reason=(default.responsible(ctx.author, "Channel locked by command execution")))
            if minutes is not None:
                await msg.edit(content=f"<:locked:810623219677397013> Channel {channel.mention} locked for `{minutes}` minute{'' if minutes == 1 else 's'}. ID: `{channel.id}`")
                await asyncio.sleep(minutes*60)
                await self.unlock(ctx, channel=channel, surpress=True)
            await msg.edit(content=f"<:locked:810623219677397013> Channel {channel.mention} locked. ID: `{channel.id}`")
        except discord.errors.Forbidden:
            await msg.edit(content=f"<:fail:816521503554273320> I have insufficient permission to lock channels.")


    @commands.command(brief="Unlock message sending in the channel.", pass_context=True, aliases=["unlockchannel"])
    @commands.guild_only()
    @commands.bot_has_permissions(manage_channels=True)
    @permissions.has_permissions(manage_channels=True)
    async def unlock(self, ctx, channel:discord.TextChannel = None, surpress = False):
        """
        Usage:      -unlock [channel]
        Output:     Unlocks a previously locked channel
        Permission: Manage Channels
        """
        if channel is None:
            channel = ctx.channel
        try:
            locked = await self.cxn.fetchrow("SELECT ChannelID FROM lockedchannels WHERE ChannelID = ?", channel.id) or (None)
            if locked is None: 
                if surpress is True:
                    return 
                else:
                    return await ctx.send(f"<:locked:810623219677397013> Channel {channel.mention} is already unlocked. ID: `{channel.id}`")

            msg = await ctx.send(f"Unlocking channel {channel.mention}...")
            old_overwrites = await self.cxn.fetchrow("SELECT EveryonePermissions FROM lockedchannels WHERE ChannelID = ?", channel.id)
            everyone_perms = str(old_overwrites).strip("(),'")

            if everyone_perms == "None": 
                everyone_perms = None
            elif everyone_perms == "False": 
                everyone_perms = False
            elif everyone_perms == "True": 
                everyone_perms = True

            overwrites_everyone = ctx.channel.overwrites_for(ctx.guild.default_role)
            overwrites_everyone.send_messages = everyone_perms
            await ctx.message.channel.set_permissions(ctx.guild.default_role, overwrite=overwrites_everyone, reason=(default.responsible(ctx.author, "Channel unlocked by command execution")))
            await self.cxn.execute("DELETE FROM lockedchannels WHERE ChannelID = ?", channel.id)
            await msg.edit(content=f"<:unlocked:810623262055989289> Channel {channel.mention} unlocked. ID: `{channel.id}`")
        except discord.errors.Forbidden:
            await msg.edit(content=f"<:fail:816521503554273320> I have insufficient permission to unlock channels.")


    @commands.command(brief="Lists all channels in the server in an embed.", aliases=['channels'])
    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True)
    @commands.cooldown(1, 20, commands.BucketType.guild)
    @permissions.has_permissions(manage_messages=True)
    async def listchannels(self, ctx):
        """
        Usage:      -listchannels
        Alias:      -channels
        Output:     Embed of all server channels
        Permission: Manage Messages
        """

        channel_categories = {}

        for chn in sorted(ctx.guild.channels, key=lambda c: c.position):
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

        paginator = Paginator(title='Channels', description=description)

        for category_id in sorted(channel_categories.keys(), key=lambda k: ctx.guild.get_channel(k).position):
            category = ctx.guild.get_channel(category_id)

            val = make_category(channel_categories[category_id])

            paginator.add_field(name=category.name.upper(), value=val, inline=False)

        paginator.finalize()

        for page in paginator.pages:
            await ctx.send(embed=page)


class EmbedLimits:
    Field = 1024
    Name = 256
    Title = 256
    Description = 2048
    Fields = 25
    Total = 6000


class Paginator:
    def __init__(self, title=None, description=None, page_count=True, init_page=True, color=default.config()["embed_color"]):
        """
        Args:
            title: title of the embed
            description: description of the embed
            page_count: whether to show page count in the footer or not
            init_page: create a page in the init method
        """
        self.color = color
        self._fields = 0
        self._pages = []
        self.title = title
        self.description = description
        self.set_page_count = page_count
        self._current_page = -1
        self._char_count = 0
        self._current_field = None
        if init_page:
            self.add_page(title, description)

    @property
    def pages(self):
        return self._pages

    def finalize(self):
        self._add_field()
        if not self.set_page_count:
            return

        total = len(self.pages)
        for idx, embed in enumerate(self.pages):
            embed.set_footer(text=f'{idx+1}/{total}')

    def add_page(self, title=None, description=None, color=default.config()["embed_color"], paginate_description=False):
        """
        Args:
            title:
            description:
            paginate_description:
                If set to true will split description based on max description length
                into multiple embeds
        """
        title = title or self.title
        description = description or self.description
        overflow = None
        if description:
            if paginate_description:
                description_ = description[:EmbedLimits.Description]
                overflow = description[EmbedLimits.Description:]
                description = description_
            else:
                description = description[:EmbedLimits.Description]

        self._pages.append(discord.Embed(title=title, description=description, color=default.config()["embed_color"]))
        self._current_page += 1
        self._fields = 0
        self._char_count = 0
        self._char_count += len(title) if title else 0
        self._char_count += len(description) if description else 0
        self.title = title
        self.description = description
        self.color = color

        if overflow:
            self.add_page(title=title, description=overflow, color=color, paginate_description=True)

    def edit_page(self, title=None, description=None, color=default.config()["embed_color"]):
        page = self.pages[self._current_page]
        if title:
            self._char_count -= len(str(title))
            page.title = str(title)
            self.title = title
            self._char_count += len(title)
        if description:
            self._char_count -= len(str(description))
            page.description = str(description)
            self.description = description
            self._char_count += len(description)

    def _add_field(self):
        if not self._current_field:
            return

        if not self._current_field['value']:
            self._current_field['value'] = 'Emptiness'

        self.pages[self._current_page].add_field(**self._current_field)
        self._fields += 1
        self._char_count += len(self._current_field['name']) + len(self._current_field['value'])
        self._current_field = None

    def add_field(self, name, value='', inline=False):
        if self._current_field is not None and self._fields < 25:
            self._add_field()

        name = name[:EmbedLimits.Title]
        leftovers = value[EmbedLimits.Field:]
        value = value[:EmbedLimits.Field]
        length = len(name) + len(value)

        if self._fields == 25:
            self._pages.append(discord.Embed(title=self.title))
            self._current_page += 1
            self._fields = 0
            self._char_count = len(self.title)
            if self._current_field is not None:
                self._add_field()

        elif length + self._char_count > EmbedLimits.Total:
            self._pages.append(discord.Embed(title=self.title))
            self._current_page += 1
            self._fields = 0
            self._char_count = len(self.title)

        self._current_field = {'name': name, 'value': value, 'inline': inline}

        if leftovers:
            self.add_field(name, leftovers, inline=inline)

    def add_to_field(self, value):
        v = self._current_field['value']
        if len(v) + len(value) > EmbedLimits.Field:
            self.add_field(self._current_field['name'], value)
        else:
            self._current_field['value'] += value