# Snowbot Moderation & Stat Tracking Discord Bot
### [Bot Invite Link](https://discord.com/oauth2/authorize?client_id=813275073459912725&scope=bot+applications.commands&permissions=956689654)
### [Support Server](https://discord.gg/bbZWhcB77Y)
### [DiscordBots.gg](https://discord.bots.gg/bots/810377376269205546)
### [Top.gg](https://top.gg/bot/810377376269205546)
## Overview
Hello! I'm Snowbot, and I specialize in tracking and moderation.
I was designed to collect all sorts of data on servers, users,
messages, emojis, online time, and more! I also come with a fast
and clean moderation system that offers every opportunity for effective
server management. Apart from moderation and tracking, I feature 254
commands across 13 categories that provide awesome utilities!
Some examples include managing user timezones, role management, and logging.
## Categories
##### [Logging](#Logging-1)
##### [Files](#Files-1)
##### [Roles](#Roles-1)
##### [Utility](#Utility-1)
##### [Conversion](#Conversion-1)
##### [Times](#Times-1)
##### [Admin](#Admin-1)
##### [Stats](#Stats-1)
##### [Automod](#Automod-1)
##### [Help](#Help-1)
##### [Info](#Info-1)
##### [Tracking](#Tracking-1)
##### [Mod](#Mod-1)


### Logging
#### Log all server events. (5 Commands)

```yaml
auditcount: Count the audit log entries of a user.

log: Enable specific logging events.

logchannel: Set your server's logging channel.

unlog: Disable specific logging events.

unlogchannel: Remove the logging channel.
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

readme: DMs you my readme file.
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

roleinfo: Get information on a role.

roleperms: Show the permissions for a role.

whohas: Show the people who have a role.
```

### Utility
#### Module for general utilities. (23 Commands)

```yaml
ascify: Convert special characters to ascii.

avatar: Show a user's avatar.

calculate: Calculate a math formula.

charinfo: Show information on a character.

color: Show a given color and its values.

colors: Send an image with some hex codes.

defaultavatar: Show a user's default avatar.

dehoist: Dehoist a specified user.

embed: Create an embed interactively.

emojipost: Sends all server emojis to your dms.

find: Find any user using a search.

gtoken: Generate a discord token.

nickname: Edit or reset a user's nickname

oauth: Generate a bot invite link.

ptoken: Decode a discord token.

raw: Shows the raw content of a message.

reactinfo: Show reaction info in a channel.

replies: Find the first message of a reply thread.

serveravatar: Show a user's default avatar.

shorten: Shorten URLs to bitly links.

snipe: Snipe a deleted message.

snowflake: Show info on a discord snowflake.

type: Find the type of a discord object.
```

### Conversion
#### Module for unit conversions. (15 Commands)

```yaml
binint: Convert binary to an integer.

binstr: Convert binary to a string

cm: Convert centimeters to feet and inches.

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

### Times
#### Module for time functions. (9 Commands)

```yaml
clock: Get the time of any location

listtz: List all available timezones.

removetz: Remove your timezone.

settz: Set your timezone.

stopwatch: Start or stop a stopwatch.

timezone: See a member's timezone.

usertime: Show a user's current time.

usertimes: Show times for all users.

utcnow: Show the current utc time.
```

### Admin
#### Module for server administration. (20 Commands)

```yaml
addprefix: Add a custom server prefix.

checkinactive: Count the inactive users.

clearprefix: Clear all custom prefixes.

disable: Disable a command.

disableall: Disable all commands.

disabledreact: React on disabled commands.

enable: Enable a command.

enableall: Enable all commands

ignore: Disallow users from using the bot.

isdisabled: Show the status of a command.

kickinactive: Kick all inactive server members

leave: Have the bot leave the server.

listdisabled: List disabled commands.

massascify: Mass nickname users with odd names.

massban: Massban users matching a search.

massdehoist: Dehoist all server users.

muterole: Setup server muting system.

prefixes: Show all server prefixes.

removeprefix: Remove a custom server prefix

unignore: Reallow users to use the bot.
```

### Stats
#### Module for server stats (16 Commands)

```yaml
admins: Show the server admins.

channelinfo: Get info about a channel.

emoji: Get usage stats on an emoji.

emojistats: Emoji usage tracking.

firstjoins: Show the first users to join.

joined: Check when a user joined the server.

joinedatpos: Show who joined at a position.

joinpos: Show the join position of a user.

lastjoins: Show the latest users to join.

listbots: Shows all the server's bots.

listchannels: Show the server's channels.

mods: Show the server mods.

permissions: Show a user's permissions.

serverinfo: Show server information.

topic: Show the topic of a channel.

userinfo: Show information on a user.
```

### Automod
#### Manage the automod system. (9 Commands)

```yaml
antiinvite: Enable or disable auto-deleting invite links

autorole: Assign roles to new members.

clearwarns: Clear a user's warnings

filter: Manage the server's word filter.

reassign: Reassign roles on user rejoin.

revokewarn: Revoke a warning from a user

serverwarns: Display the server warnlist.

warn: Warn users with an optional reason.

warncount: Count the warnings a user has.
```

### Help
#### My extensive help category. (15 Commands)

```yaml
botperms: Check if the bot can run a command.

brief: Get the short description of a command.

canrun: See if a command can be executed.

category: Show the parent category of a command.

commandinfo: Get attribute info on a command.

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
#### Module for bot information. (24 Commands)

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

pieuptime: Show a graph of uptime stats

ping: Test the bot's response latency.

privacy: View the privacy policy.

replytime: Show reply latencies.

sharedservers: Show servers shared with the bot.

socket: Show global bot socket stats.

source: Display the source code.

speed: Bot network speed.

suggest: Send a suggestion to the developer.

support: Join my support server!

uptime: Show the bot's uptime.

users: Show users I'm connected to.
```

### Tracking
#### Module for all user stats (20 Commands)

```yaml
activity: Show the most active server users.

avatars: Show a user's past avatars.

botusage: Show the top bot users.

characters: Show character usage.

commandcount: Count the commands run by a user.

commandstats: Bot commands listed by popularity.

invited: See who invited a user.

invites: Count the invites of a user.

messagecount: Count the messages a user sent.

messagestats: Show the top message senders.

nicknames: Show a user's past nicknames.

platform: Show a user's discord platform.

seen: Check when a user was last seen.

spammers: Show all recorded spammers.

status: Show a user's discord status.

statusinfo: Status info and online time stats.

user: Show information on a user.

usernames: Show a user's past usernames.

word: Usage for a specific word.

words: Most used words from a user.
```

### Mod
#### Keep your server under control. (20 Commands)

```yaml
ban: Ban users from the server.

blind: Hide a channel from a user.

block: Restrict users from sending messages.

cleanup: Clean up bot command usage.

hackban: Hackban multiple users.

kick: Kick users from the server.

lock: Lock a channel

mute: Mute users for a duration.

purge: Remove any type of content.

slowmode: Set the slowmode for a channel

softban: Softban users from the server.

tempban: Temporarily ban users.

unban: Unban a previously banned user.

unblind: Reallow users see a channel.

unblock: Reallow users to send messages.

unlock: Unlock a channel.

unmute: Unmute muted users.

vckick: Kick users from a voice channel.

vcmove: Move a user from a voice channel.

vcpurge: Kick all users from a voice channel.
```