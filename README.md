# NGC0000 Moderation & Stat Tracking Discord Bot                                
![6010fc1cf1ae9c815f9b09168dbb65a7-1](https://user-images.githubusercontent.com/74381783/108671227-f6d3f580-7494-11eb-9a77-9478f5a39684.png) 
### [Bot Invite Link](https://discord.com/api/oauth2/authorize?client_id=810377376269205546&permissions=4294967287&scope=applications.commands%20bot) 
### [Support Server](https://discord.gg/947ramn)
### [DiscordBots.gg](https://discord.bots.gg/bots/810377376269205546)
## Overview
Hello there! NGC0000 is an awesome feature rich bot named after the Milky Way. She features over 100 commands, all with extensive and easy to understand help. Her commands are fast and offer every opportunity for customization and utility.  
## Categories

##### [Information](#information-24-commands)
##### [Logging](#logging-4-commands)
##### [Moderation](#moderation-24-commands)
##### [Roles](#roles-10-commands)
##### [Settings](#settings-17-commands)
##### [Statistics](#statistics-21-commands)
##### [Utility](#utility-11-commands)
  
### Information (24 Commands)
###### Module for general information on users, servers, and bots. 
```yaml

about: Display information about the bot.
                      
admins: Show the server admins.

avatar: Display a user's avatar in an embed.

botinvite: Invite me to your server!

botowner: Show some info on the bot's developer.

bugreport: Send a bugreport to the bot creator.

defaultavatar: Show a user's default avatar.

find: Find any user using a search (Command Group).

hostinfo: Get info about the bot's host environment.

listchannels: Lists the servers channels in an embed

mods: Show the server mods.

permissions: Show a user's permissions.

ping: Test the bot's response time.

platform: Show which discord platform a user is on.

raw: Shows the raw content of a message

serverinfo: Show server information.

snipe: Snipe a message.

snowflake: Show info on a discord snowflake.

source: Display the source code.

status: Show a member's status

suggest: Send a suggestion to the bot creator.

uptime: Show the bot's uptime.

user: Get info on any discord user.

userinfo: Display information on a passed member.
                     
```
### Logging (4 Commands)
###### Module for logging all server events.

```yaml

log: Customize the server's logging by enabling specific logging events

logchannel: Set the server's logging channel.

unlog: Customize the server's logging by disabling specific logging events

unlogchannel: Remove the server's logging channel.
```

### Moderation (24 Commands)
###### Module for keeping the server under control.

```yaml

ban: Ban users from the server.
                      
blind: Hide a channel from a user.

block: Restrict users from sending messages in a channel.

clearwarns: Clear a user's warnings.

hackban: Hackban multiple users by ID.

kick: Kick users from the server.

lock: Lock a channel.

mute: Mute members with an optional timer.

nickname: Edit or reset a member's nickname.

prune: Remove any type of content.

revokewarn: Revoke a warning from a user.

serverwarns: Display the server warnlist.

slowmode: Set the slowmode for a channel.

softban: Softbans members from the server.

unban: Unban a previously banned member.

unblind: Reallow users see a channel.

unblock: Reallow users to send messages in a channel.

unlock: Unlock a previously locked channel.

unmute: Unmute previously muted members.

vckick: Kick members from a voice channel.

vcmove: Move a member from one voice channel into another.

vcpurge: Disconnect all members from a voice channel.

warn: Warn members for misbehaving.

warncount: Show how many warnings a member has.
                     
```

### Roles (10 Commands)
###### Module for managing server roles.
```yaml

addrole: Adds multiple roles to multiple users
                      
emptyroles: Shows a list of roles that have zero members.

listroles: Shows an embed of all the server roles.

massrole: Adds or removes a role to all users with a role.

removerole: Removes multiple roles from multiple users

rolecall: Counts the number of members with a specific role.

rolecount: Counts the number of roles on the server. 

roleinfo: Gets info on a specific role

roleperms: Get the permissions for a passed role.

whohas: Lists the people who have the specified role.
                     
```

### Settings (7 Commands)
###### Module for managing server settings.
```yaml

antiinvite: Enable or disable auto-deleting invite links.

filter: Manage the server's word filter list (Command Group).

ignore: Disallows passed users from using the bot within the server.

muterole: Setup server muting system.

prefix: Set your server's custom prefix.

reassign: Toggle whether or not to reaasign users old roles on rejoin.

unignore: Reallow passed to use using the bot within your server.
                     
```

### Statistics (21 Commands)
###### Module for stat tracking on users.
```yaml

activity: Show the most active server members.

commands: Show how many commands have been run.

commandstats: Show bot commands listed by popularity.

emoji: Get stats on an emoji.

emojistats: Emoji usage tracking.

firstjoins: Lists the first users to join.

joinedat: Check when a user joined the server.

joinedatpos: Shows the user that joined at the passed position.

joinpos: Tells when a user joined compared to other users.

listbots: Shows all the bots in a server.

messagecount: Show how many messages a user has sent.

messagestats: Show the top message senders in the server.

names: Show all past usernames for a given user.

nicks: Show all past nicknames for a given user.

recentjoins: Show the most recent users to join.

seen: Check when a user was last observed.

sharedservers: Lists how many servers a user shares with the bot.

usage: Show top bot users ordered by command usage.

users: Shows all users I'm connected to across all servers.

word: Show usage stats for a specific word.

words: Show the most common words used by a user.
                     
```


### Utility (11 Commands)
###### Module for timezones and files.
```yaml

dumpemotes: DMs you a file of server emojis.

dumphelp: DMs you a file of commands and descriptions.

dumpmessages: DMs you a file of channel messages.

dumproles: DMs you a file of server roles.

dumpsettings: DMs you a file with the server's settings.

dumptimezones: DMs you a file of time zones.

remtz: Remove your timezone.

settz: Set your timezone.

time: Show what time it is for a member.

timenow: Show the current time.

timezone: See a member's timezone.
```