import discord
from discord.ext import commands, tasks
from collections import defaultdict


def setup(bot):
    bot.add_cog(Tasks(bot))


class Tasks(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.current_tasks = defaultdict(list)
        # self.task_checker.start()

    def cog_unload(self):
        self.task_checker.stop()

    @tasks.loop(seconds=2.0)
    async def task_checker(self):
        pass

    @task_checker.before_loop
    async def load_tasks(self):
        query = """
                SELECT * FROM tasks;
                """
        all_tasks = await self.bot.cxn.fetch(query)
        for task in all_tasks:
            print(task)
            # self.current_tasks[]

    async def get_task(self, user, server, event, start, end):
        query = """
                SELECT (
                    user_id,
                    server_id,
                    ) tasks
                VALUES ($1, $2, $3, $4, $5)
                """
        await self.bot.cxn.execute(query)
