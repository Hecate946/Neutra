import time, discord, asyncio, json, re, sys, random

from datetime import datetime, timedelta
from discord.ext import commands
from discord.ext.menus import MenuPages, ListPageSource

from utilities import default, permissions

from lib.bot import owners
from lib.bot import bot
from lib.db import asyncdb as db


def setup(bot):
    bot.add_cog(Warnings(bot))
    
    
class HelpMenu(ListPageSource):
    def __init__(self, ctx, data):
        self.ctx = ctx

        super().__init__(data, per_page=10)

    async def write_page(self, menu, offset, fields=[]):
        len_data = len(self.entries)

        embed = discord.Embed(title="Server Warnings",
                      colour=default.config()["embed_color"])
        embed.set_thumbnail(url=self.ctx.guild.icon_url)
        embed.set_footer(text=f"{offset:,} - {min(len_data, offset+self.per_page-1):,} of {len_data:,} members.")

        for name, value in fields:
            embed.add_field(name=name, value=value, inline=False)

        return embed

    async def format_page(self, menu, entries):
        offset = (menu.current_page*self.per_page) + 1

        fields = []
        table = ("\n".join(f"{idx+offset}. {self.ctx.bot.guild.get_member(entry[0])} Warnings: {entry[1]}"
                for idx, entry in enumerate(entries)))

        fields.append(("Warnings", table))

        return await self.write_page(menu, offset, fields)

class Warnings(commands.Cog):
    """
    Manage the server's warning system.
    """

    def __init__(self, bot):
        self.bot = bot

      ###################
     ## WARN COMMANDS ##
    ###################

    @commands.command()
    @permissions.has_permissions(kick_members=True)
    async def warn(self, ctx, targets: commands.Greedy[discord.Member], *, reason: str = None):
        if not len(targets): return await ctx.send(f"Usage: `{ctx.prefix}warn <target> [target]... [reason]`")
        warned = []
        for target in targets:
            if target.id in owners: return await ctx.send('You cannot warn my master.')
            if target.id == ctx.author.id: return await ctx.send('I don\'t think you really want to warn yourself...')
            if target.id == self.bot.user.id: return await ctx.send('I don\'t think I want to warn myself...')
            if target.guild_permissions.manage_messages and ctx.author.id not in owners: return await ctx.send('You cannot punish other staff members.')
            if ctx.guild.me.top_role.position > target.top_role.position and not target.guild_permissions.administrator:
                try:
                    warnings = await db.record("SELECT Warnings FROM warn WHERE UserID = ? AND GuildID = ?", target.id, ctx.guild.id) or (None)
                    if warnings is None: 
                        warnings = 0
                        warnings = str(warnings).strip("(),").lower()
                        await db.execute("INSERT INTO warn VALUES (?, ?, ?)", target.id, ctx.guild.id, int(warnings) + 1)
                        warned.append(f"{target.name}#{target.discriminator}")
                    else:
                        warnings = str(warnings).strip("(),").lower()
                        try:
                            await db.execute("UPDATE warn SET Warnings = ? WHERE GuildID = ? AND UserID = ?", (int(warnings) + 1), ctx.guild.id, target.id)
                            warned.append(f"{target.name}#{target.discriminator}")
                        except Exception: raise

                except Exception as e: return await ctx.send(e)
                if reason:
                    try:
                        await target.send(f"<:announce:807097933916405760> You have been warned in **{ctx.guild.name}** `{reason}`.")
                    except: return
            else: return await ctx.send('<:fail:812062765028081674> `{0}` could not be warned.'.format(target))
        if warned:
            await ctx.send(f'<:ballot_box_with_check:805871188462010398> Warned `{", ".join(warned)}`')


    @commands.command()
    async def listwarns(self, ctx, target: discord.Member =None):
        if target is None:
            target = ctx.author

        try:
            warnings = await db.record("SELECT Warnings FROM warn WHERE UserID = ? AND GuildID = ?", target.id, ctx.guild.id) or (None)
            if warnings is None: return await ctx.send(f"<:ballot_box_with_check:805871188462010398> User `{target}` has no warnings.")
            warnings = str(warnings).strip("(),")
            await ctx.send(f"<:announce:807097933916405760> User `{target}` currently has **{warnings}** warning{'' if int(warnings) == 1 else 's'} in this server.")
        except Exception as e: return await ctx.send(e)


    @commands.command(aliases = ['deletewarnings','removewarns','removewarnings','deletewarns','clearwarnings'])
    @permissions.has_permissions(kick_members = True)
    async def clearwarns(self, ctx, target: discord.Member = None):
        if target is None: return await ctx.send(f"Usage: `{ctx.prefix}deletewarn <target>`")
        try:
            warnings = await db.record("SELECT Warnings FROM warn WHERE UserID = ? AND GuildID = ?", target.id, ctx.guild.id) or (None)
            if warnings is None: return await ctx.send(f"<:ballot_box_with_check:805871188462010398> User `{target}` has no warnings.")
            warnings = str(warnings).strip("(),")
            await db.execute("DELETE FROM warn WHERE UserID = ? and GuildID = ?", target.id, ctx.guild.id)
            await ctx.send(f"<:ballot_box_with_check:805871188462010398> Cleared all warnings for `{target}` in this server.")
            try:
                await target.send(f"<:announce:807097933916405760> All your warnings have been cleared in **{ctx.guild.name}**.")
            except: return
        except Exception as e: return await ctx.send(e)


    @commands.command(aliases=['revokewarning','undowarning','undowarn'])
    @permissions.has_permissions(kick_members = True)
    async def revokewarn(self, ctx, target: discord.Member = None):
        if target is None: return await ctx.send(f"Usage: `{ctx.prefix}revokewarn <target>`")
        try:
            warnings = await db.record("SELECT Warnings FROM warn WHERE UserID = ? AND GuildID = ?", target.id, ctx.guild.id) or (None)
            if warnings is None: return await ctx.send(f"<:ballot_box_with_check:805871188462010398> User `{target}` has no warnings to revoke.")
            warnings = str(warnings).strip("(),")
            if int(warnings) == 1: 
                await db.execute("DELETE FROM warn WHERE UserID = ? and GuildID = ?", target.id, ctx.guild.id)
                await ctx.send(f"<:ballot_box_with_check:805871188462010398> Cleared all warnings for `{target}` in this server.")
            else:
                await db.execute("UPDATE warn SET Warnings = ? WHERE GuildID = ? AND UserID = ?", (int(warnings) - 1), ctx.guild.id, target.id)
                await ctx.send(f"<:ballot_box_with_check:805871188462010398> Revoked a warning for `{target}` in this server.")
            try:
                await target.send(f"<:announce:807097933916405760> You last warning has been revoked in **{ctx.guild.name}**.")
            except: return
        except Exception as e: return await ctx.send(e)
    

    #@commands.command(aliases = ['serverwarnings','allwarnings','allwarns'])
    #async def serverwarns(self, ctx, show = None):
    #    """Show all warnings in this server"""
    #    message = 'Warnings: '
    #    for member in ctx.message.guild.members:
    #        if member.bot:
    #            continue
    #        try:
    #            warn = await db.record("SELECT Warnings FROM warn WHERE UserID = ? AND GuildID = ?", member.id, ctx.guild.id) or (None)
    #        except TypeError: continue
    #        warn = str(warn).strip("(),")
    #        print(warn)
    #        if warn == "None":
    #            if show is not None:
    #                message += f'<:fail:812062765028081674> `{member}` has no warnings.'
    #        else:
    #            message += f'\n<:announce:807097933916405760> `{member}` has `{warn}` warning{"" if int(warn) == 1 else "s"}.'
    #    await ctx.send(message)


    @commands.command(description="Display the server leaderboard.", aliases=["sw"])
    async def serverwarns(self, ctx):
        """Display the global leaderboard."""
        records = await db.records("SELECT UserID, Warnings FROM warn ORDER BY Warnings DESC")

        menu = MenuPages(source=HelpMenu(ctx, records),
                         clear_reactions_after=True,
                         timeout=60.0)
        await menu.start(ctx)