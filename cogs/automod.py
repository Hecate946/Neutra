import discord

from discord.ext import commands
from better_profanity import profanity
from collections import OrderedDict

from utilities import permissions, default
from lib.db import db

def setup(bot):
    bot.add_cog(Automoderation(bot))


class Automoderation(commands.Cog):
    """
    Manage countering profanity in your server.
    """
    def __init__(self, bot):
        self.bot = bot


    @commands.command(brief="Toggle whether you want to have a user's old roles be reassigned to them on rejoin.")
    @commands.guild_only()
    @permissions.has_permissions(manage_guild=True)
    async def reassign(self, ctx, *, yes_no = None):
        """
        Usage:      -reassign <yes|enable|true|on||no|disable|false|off>
        Aliases:    -stickyroles
        Permission: Manage Server
        Output:     Removes invite links sent by users without the Manage Messages permission.
        """
        current = db.record("SELECT reassign FROM roleconfig WHERE server = ?", ctx.guild.id)
        current = current[0]
        if current == 1: 
            reassign = True
        else:
            current == 0
            reassign = False
        if yes_no is None:
            # Output what we have
            msg =  "{} currently *{}*.".format("Reassigning roles on member rejoin","enabled" if current == 1 else "disabled")
        elif yes_no.lower() in [ "yes", "on", "true", "enabled", "enable" ]:
            yes_no = True
            reassign = True
            msg = "{} {} *enabled*.".format("Reassigning roles on member rejoin","remains" if current == 1 else "is now")
        elif yes_no.lower() in [ "no", "off", "false", "disabled", "disable" ]:
            yes_no = False
            reassign = False
            msg = "{} {} *disabled*.".format("Reassigning roles on member rejoin","is now" if current == 1 else "remains")
        else:
            msg = "That is not a valid setting."
            yes_no = current
        if yes_no != current:
            db.execute("UPDATE roleconfig SET reassign = ? WHERE server = ?", reassign, ctx.guild.id)
        await ctx.send(msg)


    @commands.group(invoke_without_command=True, name="filter", aliases=['profanity'], brief="Manage the server's word filter list (Command Group).")
    @commands.guild_only()
    @permissions.has_permissions(manage_guild=True)
    async def _filter(self, ctx):
        """ 
        Usage:      -filter <method>
        Alias:      -profanity
        Example:    -filter add <badword>
        Permission: Manage Server
        Output:     Adds, removes, clears, or shows the filter.
        Methods:
            add          
            remove
            display     (Alias: show)
            clear       
        Notes:
            Words added the the filter list will delete all
            messages containing that word. Users with the 
            Manage Messages permission are immune.
        """
        if ctx.invoked_subcommand is None:
            help_command = self.bot.get_command("help")
            await help_command(ctx, invokercommand="filter")


    @_filter.command(name="add", aliases=['+'])
    @permissions.has_permissions(manage_guild=True)
    async def add_word(self, ctx, *, word_to_filter: str=None):
        if word_to_filter is None:
            return await ctx.channel.send(f"Usage: `{ctx.prefix}filter add <word>`")

        word_to_filter = str(word_to_filter).lower()

        word_list = db.record("""
        SELECT word FROM profanity WHERE server = ?
        """, ctx.guild.id) or None
        if word_list is None:         

            db.execute("""
            INSERT INTO profanity VALUES (?, ?)
            """, ctx.guild.id, word_to_filter)

            await ctx.send(f'Added word `{word_to_filter}` to the filter')
        else:
            word_list = word_list[0].split(', ')
            word_list = list(OrderedDict.fromkeys(word_list))

            if word_to_filter not in word_list:
                word_list.append(word_to_filter)
            else:

                old_index = word_list.index(word_to_filter)
                word_list.pop(old_index)
                word_list.append(word_to_filter)
            new_words = ', '.join(word_list)

            db.execute("""
            UPDATE profanity SET word=? WHERE server = ?
            """, new_words, ctx.guild.id)

            await ctx.send(f'Added word `{word_to_filter}` to the filter')

    @_filter.command(name="remove", aliases=['-'], brief="Remove a word from the servers filtere list")
    @permissions.has_permissions(manage_guild=True)
    async def remove_word(self, ctx, *, word: str=None):
        if word is None:
            return await ctx.send(f"Usage: `{ctx.prefix}filter remove <word>`")


        word_list = db.record("""
        SELECT word FROM profanity WHERE server = ?
        """, ctx.guild.id) or None
        if word_list is None:
            return await ctx.send(f":warning: This server has no filtered words.")   

        word_list = word_list[0].split(', ')
        word_list = list(OrderedDict.fromkeys(word_list))

        if word not in word_list: 
            return await ctx.send(f":warning: Word `{word}` is not in the filtered list.")

        else:

            old_index = word_list.index(word)
            word_list.pop(old_index)
            new_words = ', '.join(word_list)

            db.execute("""
            UPDATE profanity SET word=? WHERE server = ?
            """, new_words, ctx.guild.id)

            await ctx.send(f'Added word `{word}` to the filter')

        await ctx.send(f'Removed "{word}" from the filter')


    @_filter.command(brief="Display a list of this server's filtered words.", aliases=['show'])
    @permissions.has_permissions(manage_guild=True)
    async def display(self, ctx):
        words = db.records("""
        SELECT word FROM profanity WHERE server=?
        """, ctx.guild.id) or None

        if words == [] or None:
            return await ctx.send(f"No filtered words yet, use `{ctx.prefix}filter add <word>` to filter words")
        e = discord.Embed(description='\n'.join(x[0] for x in words), color=default.config()["embed_color"])
        e.set_author(name="**Filtered Words**")
        await ctx.send(embed=e)


    @_filter.command(name="clear")
    @permissions.has_permissions(manage_guild=True)
    async def _clear(self, ctx):
        db.execute("""
        DELETE FROM profanity WHERE server=?
        """, ctx.guild.id)

        await ctx.send("Removed all filtered words")


    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        if before.guild is None:
            return
        if before.author.bot:
            return
        immune = before.author.guild_permissions.manage_messages
        if immune:
            return
        msg = str(after.content)
        try:
            server = db.record("""
            SELECT server FROM profanity WHERE server = ?
            """, after.guild.id) or None
            if server is None: return

            words = db.record("""
            SELECT word FROM profanity WHERE server = ?
            """, after.guild.id)

            formatted_words = str(words[0])

            filtered_words = [x for x in formatted_words.split(", ")]

            profanity.load_censor_words(filtered_words)

            for filtered_word in filtered_words:
                if profanity.contains_profanity(msg) or filtered_word in msg:
                    try:
                        await after.delete()
                        return await after.author.send(f'''Your message "{after.content}" was removed for containing the filtered word "{filtered_word}"''')
                    except Exception as e:
                        chan = self.bot.get_channel(793941369282494494)
                        await chan.send(f"Error when trying to remove message {type(e).__name__}: {e}")

        except Exception as e:
            chan = self.bot.get_channel(793941369282494494)
            await chan.send(f"Error when trying to remove message fat {type(e).__name__}: {e}")


    @commands.Cog.listener()
    async def on_message(self, message):
        if not message.guild:
            return
        if message.author.bot:
            return
        immune = message.author.guild_permissions.manage_messages
        if immune:
            return
        msg = str(message.content)

        try:
            server = db.record("""
            SELECT server FROM profanity WHERE server = ?
            """, message.guild.id) or None
            if server is None: return

            words = db.record("""
            SELECT word FROM profanity WHERE server = ?
            """, message.guild.id)

            formatted_words = str(words[0])

            filtered_words = [x for x in formatted_words.split(", ")]

            profanity.load_censor_words(filtered_words)

            for filtered_word in filtered_words:
                if profanity.contains_profanity(msg) or filtered_word in msg:
                    try:
                        await message.delete()
                        return await message.author.send(f'''Your message "{message.content}" was removed for containing the filtered word "{filtered_word}"''')
                    except Exception as e:
                        chan = self.bot.get_channel(793941369282494494)
                        await chan.send(f"Error when trying to remove message {type(e).__name__}: {e}")

        except Exception as e:
            chan = self.bot.get_channel(793941369282494494)
            await chan.send(f"Error when trying to remove message fat {type(e).__name__}: {e}")


    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        roles = ','.join([str(x.id)
                          for x in after.roles if x.name != "@everyone"])
        db.execute('UPDATE users SET roles=? WHERE id=? AND server=?',
                       roles, before.id, before.guild.id)
        if len(before.roles) < len(after.roles):
            # role added
            s = set(before.roles)
            # Check for what actually happened
            newrole = [x for x in after.roles if x not in s]
            if len(newrole) == 1:
                fmt = ":warning: **{}#{}** had the role **{}** added.".format(
                    before.name, before.discriminator, newrole[0].name)
            elif not newrole:
                return
            else:
                # This happens when the bot autoassigns your roles
                # after rejoining the server
                new_roles = [x.name for x in newrole]
                fmt = ":warning: **{}#{}** had the roles **{}** added.".format(
                    before.name, before.discriminator, ', '.join(new_roles))
        else:
            s = set(after.roles)
            newrole = [x for x in before.roles if x not in s]
            if len(newrole) == 1:
                fmt = ":warning: **{}#{}** had the role **{}** removed.".format(
                    before.name, before.discriminator, newrole[0].name)
            elif len(newrole) == 0:
                return
            else:
                new_roles = [x.name for x in newrole]
                fmt = ":warning: **{}#{}** had the roles **{}** removed.".format(
                    before.name, before.discriminator, ', '.join(new_roles))


    @commands.Cog.listener()
    async def on_member_join(self, member):
        required_perms = member.guild.me.guild_permissions.manage_roles
        if not required_perms: 
            print("no")
            return
        print("hi")


        reassign = db.record("""
        SELECT reassign FROM roleconfig WHERE server = ?
        """, member.guild.id) or None
        print(reassign)
        if reassign is None or reassign[0] == 0 or reassign[0] is None: 
            pass
        else:
            old_roles = db.record("""
            SELECT roles FROM users WHERE server = ? and id = ?
            """, member.guild.id, member.id) or None
            print(old_roles)
            if old_roles is None: return
            roles = str(old_roles[0]).split(",")
            for role_id in roles:
                role = member.guild.get_role(int(role_id))
                try:
                    await member.add_roles(role)
                except Exception as e: raise e

        autoroles = db.record("""
        SELECT autoroles FROM roleconfig WHERE server = ?
        """, member.guild.id) or None
        if autoroles is None or autoroles[0] is None: 
            pass
        else:
            roles = str(autoroles[0]).split(",")
            for role_id in roles:
                role = self.bot.get_role(int(role_id))
                try:
                    await member.add_roles(role)
                except Exception as e: raise e
        