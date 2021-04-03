import os
import json
import asyncio
import logging
import discord
from datetime import datetime
from discord.ext import tasks, commands

from settings import database
from utilities import utils

log = logging.getLogger("INFO_LOGGER")

class Settings:
    def __init__(self, bot):
        self.bot = bot
        self.backup_folder   = "./data/json/settings-backup"
        self.max_backups     = 20
        self.backup_interval = 7200 # runs every 2 hours
        self.initial_backup  = 10 # initial wait time before first backup
        self.dump_interval   = 3600 # runs every hour

        self.server_settings = database.settings

        utils.write_json("./data/json/settings.json", self.server_settings)

        self.backup.start()


    # Get the requested stat
    async def get_server_setting(self, server, setting, default = None):
        return self.server_settings.get(server.id,{}).get(setting, default)
    
    # Set the provided stat
    async def set_server_setting(self, server, setting, value):
        self.server_settings[server.id][setting] = value


    @tasks.loop(minutes=5)
    async def backup(self):

        if not os.path.exists(self.backup_folder):
            # Create it
            os.makedirs(self.backup_folder)
        # Flush backup
        timestamp = datetime.today().strftime("%Y-%m-%d %H.%M")
        utils.write_json(f"./{self.backup_folder}/Backup-{timestamp}.json", self.server_settings)

        # Get curr dir and change curr dir
        retval = os.getcwd()
        os.chdir(self.backup_folder)

        # Get reverse sorted backups
        backups = sorted(os.listdir(os.getcwd()), key=os.path.getmtime)
        num_to_remove = None
        if len(backups) > self.max_backups:
            num_to_remove = len(backups)-self.max_backups
            for i in range(0, num_to_remove):
                os.remove(backups[i])
        
        # Restore curr dir
        os.chdir(retval)
        if num_to_remove:
            log.info("Settings Backed Up ({} removed): {}".format(num_to_remove, timestamp))
        else:
            log.info("Settings Backed Up: {}".format(timestamp))
        await asyncio.sleep(self.backup_interval)


