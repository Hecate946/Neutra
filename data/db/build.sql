
CREATE TABLE IF NOT EXISTS guilds (
	GuildID integer PRIMARY KEY,
	GuildName text,
	GuildOwnerID integer,
	GuildOwner text,
	Prefix text DEFAULT "-",
	MuteRole integer,
	RemoveInviteLinks text,
	LoggerWebhookID integer
);

CREATE TABLE IF NOT EXISTS logging (
	server text, 
	message_edit boolean, 
	message_deletion boolean,
	role_changes boolean, 
	name_update boolean, 
	member_movement boolean,
    avatar_changes boolean, 
	bans boolean, 
	ignored_channels text
);

CREATE TABLE IF NOT EXISTS users (
	roles text, 
	server int, 
	location text,
	id int, 
	nicknames text, 
	messagecount int, 
	eyecount int, 
	commandcount int
);


CREATE TABLE IF NOT EXISTS mutes(
	UserID integer PRIMARY KEY,
	RoleIDs text,
	Endtime text
);


CREATE TABLE IF NOT EXISTS lockedchannels (
	ChannelID integer PRIMARY KEY,
	ChannelName text,
	GuildID integer,
	GuildName text,
	CommandExecutorID integer,
	CommandExecutorName text,
	EveryonePermissions text
);

CREATE TABLE IF NOT EXISTS warn (
	UserID integer,
	GuildID integer,
	Warnings integer
);

CREATE TABLE IF NOT EXISTS last_seen (
	UserID integer PRIMARY KEY,
	Username text,
	LastSeen text
);

CREATE TABLE IF NOT EXISTS messages (
	unix real, 
	timestamp timestamp, 
	content text, 
	id text, 
	author text, 
	channel text, 
	server text
);

CREATE TABLE IF NOT EXISTS blacklist (
	user int PRIMARY KEY,
	username text,
	reason text,
	timestamp timestamp,
	executor text,
	react boolean
);

CREATE TABLE IF NOT EXISTS serverblacklist (
	server int PRIMARY KEY,
	servername text,
	reason text,
	timestamp timestamp,
	executor text,
	react boolean
);

CREATE TABLE IF NOT EXISTS ignored (
	server int,
	servername text,
	user int,
	username text,
	reason text,
	timestamp timestamp,
	executor text,
	react boolean
);

CREATE TABLE IF NOT EXISTS snipe (
	channel int PRIMARY KEY,
	server int,
	author int,
	message_id int, 
	content text,
	timestamp timestamp
);

CREATE TABLE IF NOT EXISTS profanity (
	server int PRIMARY KEY,
	word text
);