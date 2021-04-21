import discord
from discord.ext import commands, menus

from utilities import pagination, permissions


def setup(bot):
    bot.add_cog(Warn(bot))


class Warn(commands.Cog):
    """
    Manage the server warning system
    """

    def __init__(self, bot):
        self.bot = bot
        self.emote_dict = bot.emote_dict

    ###################
    ## Warn Commands ##
    ###################

    @commands.command(brief="Warn users with an optional reason.")
    @commands.guild_only()
    @permissions.has_permissions(kick_members=True)
    async def warn(
        self, ctx, targets: commands.Greedy[discord.Member], *, reason: str = None
    ):
        """
        Usage: -warn [target] [target]... [reason]
        Output: Warns members and DMs them the reason they were warned for
        Permission: Kick Members
        Notes:
            Warnings do not automatically enforce punishments on members.
            They only store a record of how many instances a user has misbehaved.
        """
        if not len(targets):
            return await ctx.send(
                reference=self.bot.rep_ref(ctx),
                content=f"Usage: `{ctx.prefix}warn <target> [target]... [reason]`",
            )
        warned = []
        for target in targets:
            if target.id in self.bot.constants.owners:
                return await ctx.send(
                    reference=self.bot.rep_ref(ctx),
                    content="You cannot warn my developer.",
                )
            if target.id == ctx.author.id:
                return await ctx.send(
                    "I don't think you really want to warn yourself..."
                )
            if target.id == self.bot.user.id:
                return await ctx.send(
                    reference=self.bot.rep_ref(ctx),
                    content="I don't think I want to warn myself...",
                )
            if (
                target.guild_permissions.manage_messages
                and ctx.author.id not in self.bot.constants.owners
            ):
                return await ctx.send(
                    reference=self.bot.rep_ref(ctx),
                    content="You cannot punish other staff members.",
                )
            if (
                ctx.guild.me.top_role.position > target.top_role.position
                and not target.guild_permissions.administrator
            ):
                try:
                    warnings = (
                        await self.bot.cxn.fetchrow(
                            "SELECT warnings FROM warn WHERE user_id = $1 AND server_id = $2",
                            target.id,
                            ctx.guild.id,
                        )
                        or (None)
                    )
                    if warnings is None:
                        warnings = 0
                        await self.bot.cxn.execute(
                            "INSERT INTO warn VALUES ($1, $2, $3)",
                            target.id,
                            ctx.guild.id,
                            int(warnings) + 1,
                        )
                        warned.append(f"{target.name}#{target.discriminator}")
                    else:
                        warnings = int(warnings[0])
                        try:
                            await self.bot.cxn.execute(
                                "UPDATE warn SET warnings = warnings + 1 WHERE server_id = $1 AND user_id = $2",
                                ctx.guild.id,
                                target.id,
                            )
                            warned.append(f"{target.name}#{target.discriminator}")
                        except Exception:
                            raise

                except Exception as e:
                    return await ctx.send(e)
                if reason:
                    try:
                        await target.send(
                            f"<:announce:807097933916405760> You have been warned in **{ctx.guild.name}** `{reason}`."
                        )
                    except Exception:
                        return
            else:
                return await ctx.send(
                    "<:fail:816521503554273320> `{0}` could not be warned.".format(
                        target
                    )
                )
        if warned:
            await ctx.send(
                reference=self.bot.rep_ref(ctx),
                content=f'{self.bot.emote_dict["success"]} Warned `{", ".join(warned)}`',
            )

    @commands.command(brief="Count the warnings a user has.", aliases=["listwarns"])
    @commands.guild_only()
    async def warncount(self, ctx, *, target: discord.Member = None):
        """
        Usage: -warncount [member]
        Alias: -listwarns
        Output: Show how many warnings the user has
        """
        if target is None:
            target = ctx.author

        try:
            warnings = (
                await self.bot.cxn.fetchrow(
                    "SELECT warnings FROM warn WHERE user_id = $1 AND server_id = $2",
                    target.id,
                    ctx.guild.id,
                )
                or None
            )
            if warnings is None:
                return await ctx.send(
                    f"{self.emote_dict['success']} User `{target}` has no warnings."
                )
            warnings = int(warnings[0])
            await ctx.send(
                reference=self.bot.rep_ref(ctx),
                content=f"<:announce:807097933916405760> User `{target}` currently has **{warnings}** warning{'' if int(warnings) == 1 else 's'} in this server.",
            )
        except Exception as e:
            return await ctx.send(e)

    @commands.command(
        brief="Clear a user's warnings",
        aliases=[
            "deletewarnings",
            "removewarns",
            "removewarnings",
            "deletewarns",
            "clearwarnings",
        ],
    )
    @commands.guild_only()
    @permissions.has_permissions(kick_members=True)
    async def clearwarns(self, ctx, *, target: discord.Member = None):
        """
        Usage: -clearwarns [user]
        Aliases: -deletewarnings, -removewarns, -removewarnings, -deletewarns, -clearwarnings
        Permission: Kick Members
        Output: Clears all warnings for that user
        """
        if target is None:
            return await ctx.send(
                reference=self.bot.rep_ref(ctx),
                content=f"Usage: `{ctx.prefix}deletewarn <target>`",
            )
        try:
            warnings = (
                await self.bot.cxn.fetchrow(
                    "SELECT warnings FROM warn WHERE user_id = $1 AND server_id = $2",
                    target.id,
                    ctx.guild.id,
                )
                or None
            )
            if warnings is None:
                return await ctx.send(
                    f"{self.emote_dict['success']} User `{target}` has no warnings."
                )
            warnings = int(warnings[0])
            await self.bot.cxn.execute(
                "DELETE FROM warn WHERE user_id = $1 and server_id = $2",
                target.id,
                ctx.guild.id,
            )
            await ctx.send(
                reference=self.bot.rep_ref(ctx),
                content=f"{self.emote_dict['success']} Cleared all warnings for `{target}` in this server.",
            )
            try:
                await target.send(
                    f"<:announce:807097933916405760> All your warnings have been cleared in **{ctx.guild.name}**."
                )
            except Exception:
                return
        except Exception as e:
            return await ctx.send(e)

    @commands.command(
        brief="Revoke a warning from a user",
        aliases=["revokewarning", "undowarning", "undowarn"],
    )
    @commands.guild_only()
    @permissions.has_permissions(kick_members=True)
    async def revokewarn(self, ctx, *, target: discord.Member = None):
        """
        Usage: -revokewarn [user]
        Aliases: -revokewarning, -undowarning, -undowarn
        Permission: Kick Members
        Output: Revokes a warning from a user
        """
        if target is None:
            return await ctx.send(
                reference=self.bot.rep_ref(ctx),
                content=f"Usage: `{ctx.prefix}revokewarn <target>`",
            )
        try:
            warnings = (
                await self.bot.cxn.fetchrow(
                    "SELECT warnings FROM warn WHERE user_id = $1 AND server_id = $2",
                    target.id,
                    ctx.guild.id,
                )
                or None
            )
            if warnings is None:
                return await ctx.send(
                    f"{self.emote_dict['success']} User `{target}` has no warnings to revoke."
                )
            warnings = int(warnings[0])
            if int(warnings) == 1:
                await self.bot.cxn.execute(
                    "DELETE FROM warn WHERE user_id = $1 and server_id = $2",
                    target.id,
                    ctx.guild.id,
                )
                await ctx.send(
                    f"{self.emote_dict['success']} Cleared all warnings for `{target}` in this server."
                )
            else:
                await self.bot.cxn.execute(
                    "UPDATE warn SET warnings = warnings - 1 WHERE server_id = $1 AND user_id = $2",
                    ctx.guild.id,
                    target.id,
                )
                await ctx.send(
                    f"{self.emote_dict['success']} Revoked a warning for `{target}` in this server."
                )
            try:
                await target.send(
                    f"<:announce:807097933916405760> You last warning has been revoked in **{ctx.guild.name}**."
                )
            except Exception:
                return
        except Exception as e:
            return await ctx.send(e)

    @commands.command(brief="Display the server warnlist.", aliases=["warns"])
    @commands.guild_only()
    @permissions.has_permissions(manage_messages=True)
    async def serverwarns(self, ctx):
        """
        Usage: -serverwarns
        Alias: -warns
        Output: Embed of all warned members in the server
        Permission: Manage Messages
        """
        query = """SELECT COUNT(*) FROM warn WHERE server_id = $1"""
        count = await self.bot.cxn.fetchrow(query, ctx.guild.id)
        query = """SELECT user_id, warnings FROM warn WHERE server_id = $1 ORDER BY warnings DESC"""
        records = await self.bot.cxn.fetch(query, ctx.guild.id) or None
        if records is None:
            return await ctx.send(
                reference=self.bot.rep_ref(ctx),
                content=f"{self.emote_dict['error']} No current warnings exist on this server.",
            )

        p = pagination.SimplePages(
            entries=[
                [
                    f"User: `{ctx.guild.get_member(x[0]) or 'Not Found'}` Warnings `{x[1]}`"
                ]
                for x in records
            ],
            per_page=20,
        )
        p.embed.title = "{} Warn List ({:,} total)".format(
            ctx.guild.name, int(count[0])
        )

        try:
            await p.start(ctx)
        except menus.MenuError as e:
            await ctx.send(e)
