# NGC0000 Moderation & Stat Tracking Discord Bot
##### [Admin](#Admin-1)
##### [Bot](#Bot-1)
##### [Conversion](#Conversion-1)
##### [Files](#Files-1)
##### [Logging](#Logging-1)
##### [Moderation](#Moderation-1)
##### [Restrict](#Restrict-1)
##### [Roles](#Roles-1)
##### [Server](#Server-1)
##### [Users](#Users-1)
##### [Utility](#Utility-1)
##### [Warn](#Warn-1)


### Admin
#### Module for server administration. (13 Commands)

```yaml
addprefix: Add a custom server prefix.

antiinvite: Enable or disable auto-deleting invite links

autorole: Assign roles to new members.

clearprefix: Clear all custom server prefixes.

filter: Manage the server's word filter list (Command Group).

leave: Have the bot leave the server.

lock: Lock a channel

muterole: Setup server muting system.

prefixes: Show all server prefixes.

reassign: Reassign roles on user rejoin.

removeprefix: Remove a custom server prefix.

slowmode: Set the slowmode for a channel

unlock: Unlock a channel.
```

### Bot
#### Module for bot information (12 Commands)

```yaml
about: Display information about the bot.

botinvite: Invite me to your server!

botowner: Show some info on the developer.

bugreport: Send a bugreport to the developer.

hostinfo: Show the bot's host environment.

ping: Test the bot's response time.

sharedservers: Servers you and the bot share.

source: Display the source code.

suggest: Send a suggestion to the developer.

support: Join my support server!

uptime: Show the bot's uptime.

users: Shows all users I'm connected to.
```

### Conversion
#### Module for unit conversions (16 Commands)

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
#### Log your server events (4 Commands)

```yaml
log: Enable specific logging events.

logchannel: Set your server's logging channel.

unlog: Disable specific logging events.

unlogchannel: Remove the logging channel.
```

### Moderation
#### Keep your server under control. (13 Commands)

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
```

### Restrict
#### Module for disabling commands (9 Commands)

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
#### Module for all server stats (13 Commands)

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
#### Module for general utilities (19 Commands)

```yaml
avatar: Show a user's avatar.

clock: Get the time of any location

defaultavatar: Show a user's default avatar.

emoji: Get usage stats on an emoji.

emojistats: Emoji usage tracking.

find: Find any user using a search.

nickname: Edit or reset a user's nickname

permissions: Show a user's permissions.

raw: Shows the raw content of a message.

remtz: Remove your timezone.

settz: Set your timezone.

shorten: Shorten a URL.

snipe: Snipe a deleted message.

snowflake: Show info on a discord snowflake.

time: Show a user's current time.

timezone: See a member's timezone.

vckick: Kick users from a voice channel.

vcmove: Move a user from a voice channel.

vcpurge: Kick all users from a voice channel.
```

### Warn
#### Manage the server warning system (5 Commands)

```yaml
clearwarns: Clear a user's warnings

revokewarn: Revoke a warning from a user

serverwarns: Display the server warnlist.

warn: Warn users with an optional reason.

warncount: Count the warnings a user has.
```