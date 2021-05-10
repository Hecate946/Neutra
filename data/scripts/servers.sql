CREATE TABLE IF NOT EXISTS servers (
    server_id bigint PRIMARY KEY,
    server_name VARCHAR(100),
    owner_id bigint,
    prefix VARCHAR(5) DEFAULT '-',
    muterole BIGINT,
    profanities TEXT,
    autoroles TEXT,
    disabled_commands TEXT,
    admin_allow BOOLEAN DEFAULT True,
    react BOOLEAN DEFAULT True,
    reassign BOOLEAN DEFAULT True,
    antiinvite BOOLEAN DEFAULT False
);

CREATE TABLE IF NOT EXISTS prefixes (
    server_id BIGINT,
    prefix VARCHAR(30),
    UNIQUE (server_id, prefix)
);

CREATE TABLE IF NOT EXISTS logging (
    server_id BIGINT PRIMARY KEY,
    message_edits BOOLEAN DEFAULT True,
    message_deletions BOOLEAN DEFAULT True,
    role_changes BOOLEAN DEFAULT True,
    channel_updates BOOLEAN DEFAULT True,
    name_updates BOOLEAN DEFAULT True,
    voice_state_updates BOOLEAN DEFAULT True,
    avatar_changes BOOLEAN DEFAULT True,
    bans BOOLEAN DEFAULT True,
    leaves BOOLEAN DEFAULT True,
    joins BOOLEAN DEFAULT True,
    ignored_channels TEXT,
    logchannel BIGINT,
    logging_webhook_id VARCHAR(100)
);

CREATE TABLE IF NOT EXISTS ignored (
    server_id BIGINT,
    user_id BIGINT,
    author_id BIGINT,
    react BOOLEAN,
    timestamp TIMESTAMP
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

CREATE TABLE IF NOT EXISTS tasks (
    id BIGSERIAL PRIMARY KEY,
    expires TIMESTAMP,
    created TIMESTAMP DEFAULT (NOW() AT TIME ZONE 'UTC'),
    event TEXT,
    extra jsonb DEFAULT '{}'::jsonb 
);

CREATE TABLE IF NOT EXISTS invites (
    invitee BIGINT,
    inviter BIGINT,
    server_id BIGINT
);