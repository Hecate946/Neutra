import discord
import asyncio
from discord import user
from discord.ext import menus
from utilities import pagination, utils


async def error_info(ctx, failed):
    mess = await ctx.send_or_reply(
        content=f"{ctx.bot.emote_dict['failed']} Failed to {ctx.command.name} `{', '.join([x[0] for x in failed])}`",
    )
    try:
        await mess.add_reaction(ctx.bot.emote_dict["error"])
    except Exception:
        return

    def rxn_check(r):
        if (
            r.message_id == mess.id
            and r.user_id == ctx.author.id
            and str(r.emoji) == ctx.bot.emote_dict["error"]
        ):
            return True
        return False

    try:
        await ctx.bot.wait_for("raw_reaction_add", timeout=30.0, check=rxn_check)
        await mess.delete()
        await ctx.send_or_reply(
            f"{ctx.bot.emote_dict['announce']} **Failure explanation:**"
        )
        text = "\n".join([f"User: {x[0]} Reason: {x[1]}" for x in failed])
        p = pagination.MainMenu(
            pagination.TextPageSource(text=text, prefix="```prolog")
        )
        try:
            await p.start(ctx)
        except menus.MenuError as e:
            await ctx.send_or_reply(e)

    except asyncio.TimeoutError:
        try:
            await mess.clear_reactions()
        except Exception:
            await mess.remove_reaction(ctx.bot.emote_dict["error"], ctx.bot.user)


async def userperms(ctx):
    channel_perms = [
        x[0] for x in ctx.channel.permissions_for(ctx.author) if x[1] is True
    ]
    guild_perms = [x[0] for x in ctx.author.guild_permissions if x[1] is True]
    userperms = guild_perms + channel_perms
    return userperms


async def choose(ctx, search, option_dict):
    options = [x for x in option_dict]
    option_list = utils.disambiguate(search, options, None, 5)
    if len(option_list) != 1:
        if not option_list[0]["ratio"] == 1:
            option_list = [x["result"] for x in option_list]
            index, message = await pagination.Picker(
                embed_title="Select one of the closest matches.",
                list=option_list,
                ctx=ctx,
            ).pick(embed=True, syntax="prolog")

            if index < 0:
                await message.edit(
                    content=f"{ctx.bot.emote_dict['info']} Selection cancelled.",
                    embed=None,
                )
                return (None, None)

            selection = option_list[index]
            return (option_dict[selection], message)
        else:
            selection = option_list[0]["result"]
            return (option_dict[selection], None)
    else:
        selection = option_list[0]["result"]
    return (option_dict[selection], None)
