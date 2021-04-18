import discord
import os
from discord.ext import commands, menus
from datetime import datetime
from utilities import pagination, permissions, utils

def setup(bot):
    bot.add_cog(Master(bot))
def checker():
    return True
class Master(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.todo = './data/txts/todo.txt'

    async def cog_check(self, ctx):
        return permissions.is_admin(ctx)

    @commands.group(case_insensitive=True, aliases=['to-do'], invoke_without_subcommand=True)
    async def todo(self, ctx):
        if ctx.invoked_subcommand is None:
            try:
                with open(self.todo) as fp:
                    data = fp.readlines()
            except FileNotFoundError:
                return await ctx.send(f"{self.bot.emote_dict['exclamation']} No current todos.")
            if data is None or data == "":
                return await ctx.send(f"{self.bot.emote_dict['exclamation']} No current todos.")
            msg = ""
            for index, line in enumerate(data, start=1):
                msg += f"{index}. {line}\n"
            p = pagination.MainMenu(pagination.TextPageSource(msg, prefix="```prolog\n"))
            try:
                await p.start(ctx)
            except menus.MenuError as e:
                await ctx.send(e)

    @todo.command()
    async def add(self, ctx, *, todo: str = None):
        if todo is None:
            return await ctx.send(f"Usage: `{ctx.prefix}todo add <todo>`")
        with open(self.todo, "a", encoding="utf-8") as fp:
            fp.write(todo + "\n")
        await ctx.send(f"{self.bot.emote_dict['success']} Successfully added `{todo}` to the todo list.")

    @todo.command()
    async def remove(self, ctx, *, index_or_todo: str = None):
        if index_or_todo is None:
            return await ctx.send(f"Usage: `{ctx.prefix}todo remove <todo>`")
        with open(self.todo, mode="r", encoding="utf-8") as fp:
            lines = fp.readlines()
            print(lines)
        found = False
        for index, line in enumerate(lines, start=1):
            if str(index) == index_or_todo:
                lines.remove(line)
                found = True
                break
            elif line.lower().strip('\n') == index_or_todo.lower():
                lines.remove(line)
                found = True
                break
        if found is True:
            with open(self.todo, mode="w", encoding="utf-8") as fp:
                print(lines)
                fp.write(''.join(lines))
            await ctx.send(f"{self.bot.emote_dict['success']} Successfully removed todo `{index_or_todo}` from the todo list.")
        else:
            await ctx.send(f"{self.bot.emote_dict['failed']} Could not find todo `{index_or_todo}` in the todo list.")
    
    @todo.command()
    async def clear(self, ctx):
        try:
            os.remove(self.todo)
        except FileNotFoundError:
            return await ctx.send(f"{self.bot.emote_dict['success']} Successfully cleared the todo list.")
        await ctx.send(f"{self.bot.emote_dict['success']} Successfully cleared the todo list.")

    @commands.group(case_insensitive=True, aliases=['set','add'], invoke_without_subcommand=True)
    async def write(self, ctx):
        if ctx.invoked_subcommand is None:
            return await ctx.send_help(str(ctx.command))
        
    @write.command()
    async def overview(self, ctx, *, overview:str = None):
        if overview is None:
            return await ctx.invoke(self.bot.get_command('overview'))
        c = await pagination.Confirmation(
            f"**{self.bot.emote_dict['exclamation']} This action will overwrite my current overview. Do you wish to continue?**"
        ).prompt(ctx)
        if c:
            with open("./data/txts/overview.txt", "w", encoding="utf-8") as fp:
                fp.write(overview)
            await ctx.send(f"{self.bot.emote_dict['success']} **Successfully updated overview.**")
        else:
            await ctx.send(f"{self.bot.emote_dict['exclamation']} **Cancelled.**")

    @write.command()
    async def changelog(self, ctx, *, entry:str = None):
        if entry is None:
            return await ctx.send(f"Usage: `{ctx.prefix}write changelog <entry>`")
        c = await pagination.Confirmation(
            f"**{self.bot.emote_dict['exclamation']} This action will post to my changelog. Do you wish to continue?**"
        ).prompt(ctx)
        if c:
            with open("./data/txts/changelog.txt", "a", encoding="utf-8") as fp:
                fp.write(f"({datetime.utcnow()}+00:00) " + entry + "\n")
            await ctx.send(f"{self.bot.emote_dict['success']} **Successfully posted to the changelog.**")
        else:
            await ctx.send(f"{self.bot.emote_dict['exclamation']} **Cancelled.**")
            



    
