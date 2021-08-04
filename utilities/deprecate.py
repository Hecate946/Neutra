import discord

notified = []

async def check(ctx):
    if ctx.bot.user.id != 810377376269205546:
        return
    if ctx.author.id in notified:
        return
    message = f"Hello {ctx.author.mention}, Thank you for using Snowbot! Unfortunately, "
    message += "Snowbot was permanently denied verification from discord. As a result, "
    message += "Snowbot will not function as it has for very much longer. "
    message += "If you are interested in continuing to this bot, I've created a brand new bot, Neutra, "
    message += "that will retain all the commands and functionality that Snowbot had in the past. "
    message += "Note that Neutra now has a clean slate and no current collected data, "
    message += "so if you wish to transfer some of your data from Snowbot over to Neutra, "
    message += "please contact me in the support server. "
                
    embed = discord.Embed(color=ctx.bot.constants.embed)
    embed.description = message
    embed.set_author(name=str(ctx.bot.hecate), url=ctx.bot.constants.support, icon_url=ctx.bot.hecate.avatar.url)
    embed.set_thumbnail(url=ctx.bot.get_user(806953546372087818).avatar.url)
    inv = discord.ui.Button(label="Invite Neutra", url=ctx.bot.genoauth(806953546372087818))
    sup = discord.ui.Button(label="Support Server", url=ctx.bot.constants.support)
    view = discord.ui.View()
    view.add_item(inv)
    view.add_item(sup)
    await ctx.send(embed=embed, view=view)
    notified.append(ctx.author.id)
    return True
