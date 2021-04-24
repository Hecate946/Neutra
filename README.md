# Snowbot Moderation & Stat Tracking Discord Bot
![6010fc1cf1ae9c815f9b09168dbb65a7-1](https://user-images.githubusercontent.com/74381783/108671227-f6d3f580-7494-11eb-9a77-9478f5a39684.png)
### [Bot Invite Link](https://discord.com/oauth2/authorize?client_id=810377376269205546&permissions=8589934591&scope=applications.commands%20bot)
### [Support Server](https://discord.gg/947ramn)
### [DiscordBots.gg](https://discord.bots.gg/bots/810377376269205546)
## Overview
Hello! I'm Snowbot, and I specialize in tracking and moderation.
I was designed to collect all sorts of data on servers, users,
messages, emojis, online time, and more! I also come with a fast
and clean moderation system that offers every opportunity for effective
server management. Apart from moderation and tracking, I feature 186
commands across 13 categories that provide awesome utilities!
Some examples include managing user timezones, role management, and logging.
## Categories
##### [Admin](#Admin-1)
##### [Bot](#Bot-1)
##### [Conversion](#Conversion-1)
##### [Files](#Files-1)
##### [Logging](#Logging-1)
##### [Mod](#Mod-1)
##### [Restrict](#Restrict-1)
##### [Roles](#Roles-1)
##### [Server](#Server-1)
##### [Time](#Time-1)
##### [Users](#Users-1)
##### [Utility](#Utility-1)
##### [Warn](#Warn-1)


### Admin
#### Module for server administration. (15 Commands)

```yaml
addprefix: Add a custom server prefix.

antiinvite: Enable or disable auto-deleting invite links

autorole: Assign roles to new members.

clearprefix: Clear all custom server prefixes.

filter: Manage the server's word filter.

leave: Have the bot leave the server.

lock: Lock a channel

massascify: Mass nickname users with odd names.

massdehoist: Dehoist all server users.

muterole: Setup server muting system.

prefixes: Show all server prefixes.

reassign: Reassign roles on user rejoin.

removeprefix: Remove a custom server prefix.

slowmode: Set the slowmode for a channel

unlock: Unlock a channel.
```

### Bot
#### Module for bot information. (15 Commands)

```yaml
about: Display information about the bot.

botinvite: Invite me to your server!

bugreport: Send a bugreport to the developer.

changelog: Show my changelog.

hostinfo: Show the bot's host environment.

lines: Show sourcecode statistics.

overview: Show some info on the bot's purpose.

ping: Test the bot's response latency.

sharedservers: Servers you and the bot share.

source: Display the source code.

speed: Bot network speed.

suggest: Send a suggestion to the developer.

support: Join my support server!

uptime: Show the bot's uptime.

users: Shows all users I'm connected to.
```

### Conversion
#### Module for unit conversions. (16 Commands)

```yaml
binint: Convert binary to an integer.

binstr: Convert binary to a string

cm: Convert centimeters to feet and inches.

color: Show a given color and its values.

dechex: Convert decimal into hex.

decode: Decode from b32, b64, b85, rot13, hex.

encode: Encode to: b32, b64, b85, rot13, hex.

ft: Convert feet.inches to centimeters

hexdec: Convert hex to decimal.

intbin: Convert an integer to binary.

kg: Convert kilograms to pounds.

lb: Convert pounds to kilograms

morse: Converts ascii to morse code.

morsetable: Show the morse lookup table

strbin: Convert a string to binary.

unmorse: Converts morse code to ascii.
```

### Files
#### Module for downloading files. (14 Commands)

```yaml
dumpbans: DMs you a file of server bans.

dumpbots: DMs you a file of server bots.

dumpcategories: DMs you a file of voice channels.

dumpchannels: DMs you a file of text channels.

dumpemotes: DMs you a file of server emojis.

dumphelp: DMs you a file of commands.

dumphumans: DMs you a file of server humans.

dumpmembers: DMs you a file of server members.

dumpmessages: DMs you a file of channel messages.

dumproles: DMs you a file of server roles.

dumpsettings: DMs you a file of server settings.

dumptimezones: DMs you a file of time zones.

dumpvoicechannels: DMs you a file of voice channels.

readme: DMs you my readme file.
```

### Logging
#### Log all server events. (4 Commands)

```yaml
log: Enable specific logging events.

logchannel: Set your server's logging channel.

unlog: Disable specific logging events.

unlogchannel: Remove the logging channel.
```

### Mod
#### Keep your server under control. (16 Commands)

```yaml
ban: Ban users from the server.

blind: Hide a channel from a user.

block: Restrict users from sending messages.

cleanup: Clean up command usage.

hackban: Hackban multiple users by ID.

kick: Kick users from the server.

mute: Mute users for misbehaving.

prune: Remove any type of content.

softban: Softban users from the server.

unban: Unban a previously banned user.

unblind: Reallow users see a channel.

unblock: Reallow users to send messages.

unmute: Unmute previously muted members.

vckick: Kick users from a voice channel.

vcmove: Move a user from a voice channel.

vcpurge: Kick all users from a voice channel.
```

### Restrict
#### Module for disabling commands. (9 Commands)

```yaml
disable: Disable a command.

disableall: Disable all commands.

disabledreact: React on disabled commands.

enable: Enable a command.

enableall: Enable all commands

ignore: Disallow users from using the bot.

isdisabled: Show the status of a command.

listdisabled: List disabled commands.

unignore: Reallow users to use the bot.
```

### Roles
#### Manage all actions regarding roles. (10 Commands)

```yaml
addrole: Adds roles to users.

emptyroles: Show roles that have no users.

listroles: Show an embed of all server roles.

massrole: Mass adds or removes a role to users.

removerole: Removes roles from users.

rolecall: Counts the users with a role.

rolecount: Counts the roles on the server.

roleinfo: Get info on a specific role.

roleperms: Show the permissions for a role.

whohas: Show the people who have a role.
```

### Server
#### Module for all server stats. (13 Commands)

```yaml
activity: Show the most active server users.

admins: Show the server admins.

channelinfo: Get info about a channel.

firstjoins: Show the first users to join.

joinedat: Check when a user joined the server.

joinedatpos: Show who joined at a position.

joinpos: Show the join position of a user.

listbots: Shows all the server's bots.

listchannels: Show the server's channels.

mods: Show the server mods.

recentjoins: Show the latest users to join.

serverinfo: Show server information.

topic: Show a channel topic.
```

### Time
#### Module for time functions. (8 Commands)

```yaml
clock: Get the time of any location

listtz: List all available timezones.

remtz: Remove your timezone.

settz: Set your timezone.

stopwatch: Start or stop a stopwatch.

timezone: See a member's timezone.

usertime: Show a user's current time.

usertimes: Show times for all users.
```

### Users
#### Module for all user stats (13 Commands)

```yaml
commands: Count the commands run.

commandstats: Bot commands listed by popularity.

messagecount: Count the messages a user sent.

messagestats: Show the top message senders.

names: Show a user's usernames.

nicks: Show a user's nicknames.

platform: Show which platform a user is on.

seen: Check when a user was last seen.

status: Show a user's status

usage: Show the top bot users.

user: Show information on a user.

word: Usage for a specific word.

words: Most used words from a user.
```

### Utility
#### Module for general utilities. (15 Commands)

```yaml
ascify: Convert special characters to ascii.

avatar: Show a user's avatar.

calculate: Calculate a math formula.

charinfo: Show information on a character.

defaultavatar: Show a user's default avatar.

dehoist: Dehoist a specified user.

emoji: Get usage stats on an emoji.

emojistats: Emoji usage tracking.

find: Find any user using a search.

nickname: Edit or reset a user's nickname

permissions: Show a user's permissions.

raw: Shows the raw content of a message.

shorten: Shorten a URL.

snipe: Snipe a deleted message.

snowflake: Show info on a discord snowflake.
```

### Warn
#### Manage the server warning system. (5 Commands)

```yaml
clearwarns: Clear a user's warnings

revokewarn: Revoke a warning from a user

serverwarns: Display the server warnlist.

warn: Warn users with an optional reason.

warncount: Count the warnings a user has.
```