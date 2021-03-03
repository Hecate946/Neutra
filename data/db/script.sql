
CREATE TABLE IF NOT EXISTS servers (
    server_id bigint PRIMARY KEY,
    server_name varchar(50),
    server_owner_id bigint,
    server_owner_name varchar(50),
    server_join_position serial,
    prefix VARCHAR(5) DEFAULT '-',
    message_count bigint,
    command_count bigint
);

CREATE TABLE IF NOT EXISTS logging (
    server_id bigint PRIMARY KEY, 
    message_edits boolean, 
    message_deletions boolean,
    role_changes boolean, 
    channel_updates boolean,
    name_updates boolean, 
    voice_state_updates boolean,
    avatar_changes boolean, 
    bans boolean, 
    leaves boolean,
    joins boolean,
    ignored_channels text,
    logchannel bigint,
    logging_webhook_id varchar(100)
);

CREATE TABLE IF NOT EXISTS users (
    id bigint, 
    roles text, 
    server_id bigint, 
    nicknames text, 
    messagecount bigint DEFAULT 0 NOT NULL, 
    eyecount bigint DEFAULT 0 NOT NULL, 
    commandcount bigint DEFAULT 0 NOT NULL,
    location text
);

CREATE TABLE IF NOT EXISTS mutes (
    muted_user bigint,
    server_id bigint,
    endtime timestamp
);

CREATE TABLE IF NOT EXISTS lockedchannels (
    channel_id bigint PRIMARY KEY,
    server_id bigint,
    command_executor bigint,
    everyone_perms text
);

CREATE TABLE IF NOT EXISTS warn (
    id bigint,
    server_id bigint,
    warnings smallint
);

CREATE TABLE IF NOT EXISTS last_seen (
    id bigint PRIMARY KEY,
    timestamp timestamp
);

CREATE TABLE IF NOT EXISTS messages (
    unix real, 
    timestamp timestamp, 
    content text, 
    msg_id bigint, 
    author_id bigint, 
    channel_id bigint, 
    server_id bigint
);

CREATE TABLE IF NOT EXISTS commands (
    timestamp timestamp,
    command varchar(20),
    content text,
    executor varchar(50),
    executor_id bigint,
    channel_id bigint,
    server_id bigint
);

CREATE TABLE IF NOT EXISTS blacklist (
    id bigint PRIMARY KEY,
    username text,
    reason text,
    timestamp timestamp,
    executor text,
    react boolean
);

CREATE TABLE IF NOT EXISTS serverblacklist (
    server_id bigint PRIMARY KEY,
    server_name text,
    reason text,
    timestamp timestamp,
    executor text,
    react boolean
);

CREATE TABLE IF NOT EXISTS ignored (
    server_id bigint,
    servername text,
    id bigint,
    username text,
    reason text,
    timestamp timestamp,
    executor text,
    react boolean
);

CREATE TABLE IF NOT EXISTS snipe (
    channel_id bigint PRIMARY KEY,
    server_id bigint,
    author_id bigint,
    message_id bigint, 
    content text,
    timestamp timestamp
);

CREATE TABLE IF NOT EXISTS profanity (
    server_id bigint PRIMARY KEY,
    words text
);

CREATE TABLE IF NOT EXISTS roleconfig (
    server_id bigint PRIMARY KEY,
    whitelist text,
    autoroles text,
    reassign boolean DEFAULT true
);

CREATE TABLE IF NOT EXISTS moderation (
    server_id bigint PRIMARY KEY,
    anti_invite boolean,
    mod_role bigint
);