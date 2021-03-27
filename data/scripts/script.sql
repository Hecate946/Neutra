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

CREATE TABLE IF NOT EXISTS mutes (
    muted_user bigint,
    server_id bigint,
    role_ids text,
    endtime timestamp
);

CREATE TABLE IF NOT EXISTS lockedchannels (
    channel_id bigint PRIMARY KEY,
    server_id bigint,
    command_executor bigint,
    everyone_perms text
);

CREATE TABLE IF NOT EXISTS warn (
    user_id bigint,
    server_id bigint,
    warnings smallint
);


CREATE TABLE IF NOT EXISTS blacklist (
    user_id BIGINT PRIMARY KEY,
    author_id BIGINT, -- OK this will only be the owner but ¯\＿( ͡° ͜ʖ ͡°)＿/¯
    reason TEXT,
    react BOOLEAN,
    timestamp TIMESTAMP
);

CREATE TABLE IF NOT EXISTS serverblacklist (
    server_id BIGINT PRIMARY KEY,
    reason TEXT,
    timestamp TIMESTAMP,
    executor TEXT,
    react BOOLEAN
);

CREATE TABLE IF NOT EXISTS ignored (
    server_id BIGINT,
    user_id BIGINT,
    author_id BIGINT,
    reason TEXT,
    react BOOLEAN,
    timestamp TIMESTAMP
);

CREATE TABLE IF NOT EXISTS profanity (
    server_id bigint PRIMARY KEY,
    words text
);

CREATE TABLE IF NOT EXISTS roleconfig (
    server_id BIGINT PRIMARY KEY,
    autoroles TEXT,
    reassign BOOLEAN DEFAULT true
);

CREATE TABLE IF NOT EXISTS moderation (
    server_id BIGINT PRIMARY KEY,
    anti_invite BOOLEAN,
    mute_role BIGINT
);

CREATE TABLE IF NOT EXISTS tracker (
    user_id BIGINT PRIMARY KEY,
    unix BIGINT
);