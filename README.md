# Snowbot Moderation & Stat Tracking Discord Bot
### [Bot Invite Link](https://discord.com/oauth2/authorize?client_id=813275073459912725&scope=bot+applications.commands&permissions=8589934591)
### [Support Server](https://discord.gg/947ramn)
### [DiscordBots.gg](https://discord.bots.gg/bots/810377376269205546)
## Overview
Hello! I'm Snowbot, and I specialize in tracking and moderation.
I was designed to collect all sorts of data on servers, users,
messages, emojis, online time, and more! I also come with a fast
and clean moderation system that offers every opportunity for effective
server management. Apart from moderation and tracking, I feature 216
commands across 13 categories that provide awesome utilities!
Some examples include managing user timezones, role management, and logging.
## Categories
##### [Admin](#Admin-1)
##### [Automod](#Automod-1)
##### [Commands](#Commands-1)
##### [Conversion](#Conversion-1)
##### [Files](#Files-1)
##### [Info](#Info-1)
##### [Logging](#Logging-1)
##### [Mod](#Mod-1)
##### [Roles](#Roles-1)
##### [Stats](#Stats-1)
##### [Time](#Time-1)
##### [Tracking](#Tracking-1)
##### [Utility](#Utility-1)


### Admin
#### Module for server administration. (18 Commands)

```yaml
addprefix: Add a custom server prefix.

clearprefix: Clear all custom prefixes.

disable: Disable a command.

disableall: Disable all commands.

disabledreact: React on disabled commands.

enable: Enable a command.

enableall: Enable all commands

ignore: Disallow users from using the bot.

isdisabled: Show the status of a command.

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

### Commands
#### My extensive help category. (12 Commands)

```yaml
botperms: Check if the bot can run a command.

brief: Get the short description of a command.

canrun: See if a command can be executed.

commandinfo: Get attribute info on a command.

docstring: Get the help docstring of a command.

help: My documentation for all commands.

made: Show when a command was first made.

reqperms: Check if you can run a command.

updated: Show when a command was last updated.

usage: Get a usage example for a command.

where: Show where a command can be run.

writer: Show who wrote a command.
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

dumpmessages: DMs you a file of channel messages.

dumproles: DMs you a file of server roles.

dumpsettings: DMs you a file of server settings.

dumptimezones: DMs you a file of time zones.

dumpusers: DMs you a file of server members.

dumpvoicechannels: DMs you a file of voice channels.

readme: DMs you my readme file.
```

### Info
#### Module for bot information. (22 Commands)

```yaml
about: Display information about the bot.

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

request: Send a request to the developer.

sharedservers: Show servers shared with the bot.

source: Display the source code.

speed: Bot network speed.

suggest: Send a suggestion to the developer.

support: Join my support server!

uptime: Show the bot's uptime.

users: Show users I'm connected to.
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
#### Keep your server under control. (20 Commands)

```yaml
ban: Ban users from the server.

blind: Hide a channel from a user.

block: Restrict users from sending messages.

cleanup: Clean up bot command usage.

hackban: Hackban multiple users.

kick: Kick users from the server.

lock: Lock a channel

mute: Mute users for misbehaving.

purge: Remove any type of content.

slowmode: Set the slowmode for a channel

softban: Softban users from the server.

tempban: Temporarily ban users.

unban: Unban a previously banned user.

unblind: Reallow users see a channel.

unblock: Reallow users to send messages.

unlock: Unlock a channel.

unmute: Unmute previously muted members.

vckick: Kick users from a voice channel.

vcmove: Move a user from a voice channel.

vcpurge: Kick all users from a voice channel.
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

### Stats
#### Module for server stats (15 Commands)

```yaml
admins: Show the server admins.

channelinfo: Get info about a channel.

emoji: Get usage stats on an emoji.

emojistats: Emoji usage tracking.

firstjoins: Show the first users to join.

joinedat: Check when a user joined the server.

joinedatpos: Show who joined at a position.

joinpos: Show the join position of a user.

listbots: Shows all the server's bots.

listchannels: Show the server's channels.

mods: Show the server mods.

permissions: Show a user's permissions.

recentjoins: Show the latest users to join.

serverinfo: Show server information.

topic: Show a channel topic.
```

### Time
#### Module for time functions. (9 Commands)

```yaml
clock: Get the time of any location

listtz: List all available timezones.

remtz: Remove your timezone.

settz: Set your timezone.

stopwatch: Start or stop a stopwatch.

timezone: See a member's timezone.

usertime: Show a user's current time.

usertimes: Show times for all users.

utcnow: Show the current utc time.
```

### Tracking
#### Module for all user stats (18 Commands)

```yaml
activity: Show the most active server users.

avatars: Show a user's avatars.

botusage: Show the top bot users.

commandcount: Count the commands run by a user.

commandstats: Bot commands listed by popularity.

messagecount: Count the messages a user sent.

messagestats: Show the top message senders.

names: Show a user's usernames.

nicks: Show a user's nicknames.

platform: Show which platform a user is on.

seen: Check when a user was last seen.

spammers: Show all users who spam.

status: Show a user's status

statusinfo: Status info and online time.

user: Show information on a user.

userinfo: Show information on a user.

word: Usage for a specific word.

words: Most used words from a user.
```

### Utility
#### Module for general utilities. (20 Commands)

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

find: Find any user using a search.

gtoken: Generate a discord token for a user.

nickname: Edit or reset a user's nickname

oauth: Generate a bot invite link.

ptoken: Decode a discord token.

raw: Shows the raw content of a message.

replies: Find the first message of a reply thread.

shorten: Shorten URLs to a bitly links.

snipe: Snipe a deleted message.

snowflake: Show info on a discord snowflake.

type: Find the type of a discord object.
```