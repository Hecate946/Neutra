import discord
import asyncio
from discord.ext import menus
from utilities import pagination

async def error_info(ctx, failed):
    mess = await ctx.send(
        reference=ctx.bot.rep_ref(ctx),
        content=f"{ctx.bot.emote_dict['failed']} Failed to kick `{', '.join([x[0] for x in failed])}`",
    )
    try:
        await mess.add_reaction(ctx.bot.emote_dict['info'])
    except Exception:
        return
    def rxn_check(r):
        if (
            r.message_id == mess.id
            and r.user_id == ctx.author.id
            and str(r.emoji) == ctx.bot.emote_dict['info']
        ):
            return True
        return False

    try:
        await ctx.bot.wait_for(
            "raw_reaction_add", timeout=30.0, check=rxn_check
        )
        await mess.delete()
        await ctx.send(f"{ctx.bot.emote_dict['announce']} **Failure explanation:**")
        text = '\n'.join([f"User: {x[0]} Reason: {x[1]}" for x in failed])
        p = pagination.MainMenu(
            pagination.TextPageSource(
                text=text, prefix="```prolog"
            )
        )
        try:
            await p.start(ctx)
        except menus.MenuError as e:
            await ctx.send(e)

    except asyncio.TimeoutError:
            try:
                await mess.clear_reactions()
            except Exception:
                await mess.remove_reaction(ctx.bot.emote_dict['info'], ctx.bot.user)