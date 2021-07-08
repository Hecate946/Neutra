# Snowbot Moderation & Stat Tracking Discord Bot
### [Bot Invite Link](https://discord.com/oauth2/authorize?client_id=813275073459912725&scope=bot+applications.commands&permissions=956689622)
### [Support Server](https://discord.gg/H2qTG4yxqb)
### [DiscordBots.gg](https://discord.bots.gg/bots/810377376269205546)
### [Top.gg](https://top.gg/bot/810377376269205546)
## Overview
Hello! I'm Snowbot, and I specialize in tracking and moderation.
I was designed to collect all sorts of data on servers, users,
messages, emojis, online time, and more! I also come with a fast
and clean moderation system that offers every opportunity for effective
server management. Apart from moderation and tracking, I feature 268
commands across 12 categories that provide awesome utilities!
Some examples include managing user timezones, role management, and logging.
## Categories
##### [Admin](#Admin-1)
##### [Automod](#Automod-1)
##### [Config](#Config-1)
##### [Files](#Files-1)
##### [Help](#Help-1)
##### [Info](#Info-1)
##### [Logging](#Logging-1)
##### [Mod](#Mod-1)
##### [Music](#Music-1)
##### [Stats](#Stats-1)
##### [Tracking](#Tracking-1)
##### [Utility](#Utility-1)


### Admin
#### Module for server administration. (14 Commands)

```yaml
addprefix: Add a custom server prefix.

checkinactive: Count the inactive users.

clearprefix: Clear all custom prefixes.

kickinactive: Kick all inactive server members

kill: Have the bot leave the server.

massascify: Mass nickname users with odd names.

massban: Massban users matching a search.

massdehoist: Dehoist all server users.

masskick: Mass kick users matching a search.

muterole: Setup server muting system.

prefixes: Show all server prefixes.

removeprefix: Remove a custom server prefix

reset: Manage stored user data.

role: Manage mass adding/removing roles.
```

### Automod
#### Manage the automod system. (10 Commands)

```yaml
antiinvite: Enable or disable auto-deleting invite links

autorole: Assign roles to new members.

clearwarns: Clear a user's warnings

filter: Manage the server's word filter.

listwarns: Show all warnings a user has.

reassign: Reassign roles on user rejoin.

unwarn: Revoke a warning from a user

warn: Warn users with an optional reason.

warncount: Count the warnings a user has.

warns: Display the server warnlist.
```

### Config
#### Configure the permission system. (6 Commands)

```yaml
disable: Disable commands for users, roles, and channels.

disabled: Show disabled commands.

enable: Enable commands for users, roles, and channels.

ignore: Ignore channels, roles, and users.

ignored: Show ignored roles, users, and channels.

unignore: Unignore channels, users, and roles.
```

### Files
#### Module for downloading files. (15 Commands)

```yaml
audit: Get a file of a user's audit actions.

dumpbans: DMs you a file of server bans.

dumpbots: DMs you a file of server bots.

dumpcategories: DMs you a file of voice channels.

dumpchannels: DMs you a file of text channels.

dumpemotes: DMs you a file of server emojis.

dumphelp: DMs you a file of commands.

dumphumans: DMs you a file of server humans.

dumpmessages: DMs you a file of channel messages.

dumproles: DMs you a file of server roles.

dumpsettings: DMs you a file of server settings.

dumptimezones: DMs you a file of time zones.

dumpusers: DMs you a file of server members.

dumpvoicechannels: DMs you a file of voice channels.

dumpwarns: DMs you a file of server bans.
```

### Help
#### My extensive help category. (17 Commands)

```yaml
aliases: Show the aliases for a command

botperms: Check if the bot can run a command.

brief: Get the short description of a command.

canrun: See if a command can be executed.

category: Show the parent category of a command.

commandinfo: Get attribute info on a command.

commandsearch: Search for a command by name.

docstring: Get the help docstring of a command.

examples: Get specific examples for a command.

help: My documentation for all commands.

made: Show when a command was first made.

reqperms: Check if you can run a command.

updated: Show when a command was last updated.

usage: Get a usage example for a command.

where: Show where a command can be run.

writer: Show who wrote a command.

writers: Show all people who wrote for me.
```

### Info
#### Module for bot information. (23 Commands)

```yaml
about: Display information about the bot.

avgping: View the average message latency.

botadmins: Show the bot's admins.

botowners: Show the bot's owners.

bugreport: Send a bugreport to the developer.

changelog: Show my changelog.

cogs: List all my cogs in an embed.

hostinfo: Show the bot's host environment.

invite: Invite me to your server!

lines: Show sourcecode statistics.

neofetch: Run the neofetch command.

overview: Show some info on the bot's purpose.

ping: Test the bot's response latency.

privacy: View the privacy policy.

replytime: Show reply latencies.

sharedservers: Show servers shared with the bot.

socket: Show global bot socket stats.

source: Display the source code.

suggest: Send a suggestion to the developer.

support: Join my support server!

uptime: Show the bot's uptime.

uptimeinfo: Show a graph of uptime stats

users: Show users I'm connected to.
```

### Logging
#### Manage the logging system (7 Commands)

```yaml
auditcount: Count the audit log entries of a user.

editsnipe: Snipe an edited message.

log: Manage the logging setup.

logchannel: Set your server's logging channel.

snipe: Snipe a deleted message.

unlog: Disable logging events.

unlogchannel: Remove your server's logging channel.
```

### Mod
#### Keep your server under control. (22 Commands)

```yaml
addrole: Add multiple roles to a user.

ban: Ban users from the server.

blind: Hide a channel from a user.

block: Restrict users from sending messages.

cleanup: Clean up bot command usage.

kick: Kick users from the server.

lock: Prevent messages in a channel.

mute: Mute users for a duration.

purge: Remove any type of content.

removerole: Remove multiple roles to a user.

slowmode: Set the slowmode for a channel

softban: Softban users from the server.

tempban: Temporarily ban users.

temprole: Temporarily add roles to users.

unban: Unban a previously banned user.

unblind: Reallow users see a channel.

unblock: Reallow users to send messages.

unlock: Unlock a channel.

unmute: Unmute muted users.

vckick: Kick users from a voice channel.

vcmove: Move a user from a voice channel.

vcpurge: Kick all users from a voice channel.
```

### Music
#### Module for playing music (24 Commands)

```yaml
clear: Remove all queued songs.

connect: Joins a voice or stage channel.

current: Displays the currently playing song.

disconnect: Disconnect the bot from a channel.

fastforward: Fast forward a number of seconds

loop: Loop the current song or queue.

move: Move a song in the queue.

pause: Pauses the currently playing song.

play: Play a song from a youtube search.

playnext: Add a song to the beginning of the queue.

position: Show the current position of the song.

previous: Play the previous song.

queue: Display the current song queue.

remove: Remove a song from the queue.

resume: Resumes a currently paused song.

rewind: Rewind a number of seconds

seek: Seek to a position in a song.

shuffle: Shuffle the current song queue.

skip: Vote to skip the current song.

stop: Stops playing song and clears the queue.

subtitles: Request subtitles for the song.

unloop: Un-loop the current song or queue.

volume: Set the volume of the player.

youtube: Search for anything on youtube.
```

### Stats
#### Module for server stats (23 Commands)

```yaml
admins: Show the server admins.

channelinfo: Get info about a channel.

emoji: Get usage stats on an emoji.

emojistats: Emoji usage tracking.

emptyroles: Show roles that have no users.

firstjoins: Show the first users to join.

joined: Check when a user joined the server.

joinedatpos: Show who joined at a position.

joinpos: Show the join position of a user.

lastjoins: Show the latest users to join.

listbots: Shows all the server's bots.

listchannels: Show the server's channels.

listroles: Show an embed of all server roles.

mods: Show the server moderators.

permissions: Show a user's permissions.

rolecall: Counts the users with a role.

rolecount: Counts the roles on the server.

roleinfo: Get information on a role.

roleperms: Show the permissions for a role.

serverinfo: Show server information.

topic: Show the topic of a channel.

userinfo: Show information on a user.

whohas: Show the people who have a role.
```

### Tracking
#### Module for all user stats (24 Commands)

```yaml
activity: Show the most active server users.

avatars: Show a user's past avatars.

barstatus: Status info in a bar graph.

botusage: Show the top bot users.

characters: Show character usage.

clocker: Show the days a user was active.

clocking: Show all active users.

commandcount: Count the commands run by a user.

commandstats: Bot commands listed by popularity.

invited: See who invited a user.

invites: Count the invites of a user.

messagecount: Count the messages a user sent.

messagestats: Show messaging stats on users.

nicknames: Show a user's past nicknames.

seen: Check when a user was last seen.

spoke: Check when a user last spoke.

spokehere: Check when a user last spoke here.

status: Show a user's discord status.

statusinfo: Status info and online time stats.

top: Show the top message senders.

user: Show information on a user.

usernames: Show a user's past usernames.

word: Usage for a specific word.

words: Most used words from a user.
```

### Utility
#### Module for general utilities. (24 Commands)

```yaml
ascify: Convert special characters to ascii.

avatar: Show a user's avatar.

badges: Show all the badges a user has

calculate: Calculate a math formula.

charinfo: Show information on a character.

color: Show a given color and its values.

defaultavatar: Show a user's default avatar.

dehoist: Dehoist a specified user.

embed: Create an embed interactively.

emojipost: Sends all server emojis to your dms.

find: Find any user using a search.

gtoken: Generate a discord token.

nickname: Edit or reset a user's nickname

oauth: Generate a bot invite link.

platform: Show a user's discord platform.

ptoken: Decode a discord token.

raw: Shows the raw content of a message.

reactinfo: Get react info on a message.

replies: Find the first message of a reply thread.

serveravatar: Show the server's icon.

shorten: Shorten URLs to bitly links.

snowflake: Show info on a discord snowflake.

type: Find the type of a discord object.

voiceusers: Show all the users in a vc.
```