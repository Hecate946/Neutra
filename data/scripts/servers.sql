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
    discord_invites BOOLEAN DEFAULT True,
    server_updates BOOLEAN DEFAULT True,
    emojis BOOLEAN DEFAULT True,
    ignored_channels TEXT,
    logchannel BIGINT,
    logging_webhook_id VARCHAR(100)
);

CREATE TABLE IF NOT EXISTS command_config (
  id BIGSERIAL PRIMARY KEY,
  server_id BIGINT,
  entity_id BIGINT,
  command TEXT,
  insertion TIMESTAMP DEFAULT (NOW() AT TIME ZONE 'UTC')
);
CREATE UNIQUE INDEX IF NOT EXISTS command_config_idx ON command_config(entity_id, command);

CREATE TABLE IF NOT EXISTS plonks (
    id BIGSERIAL PRIMARY KEY,
    server_id BIGINT,
    entity_id BIGINT,
    insertion TIMESTAMP DEFAULT (NOW() AT TIME ZONE 'UTC')
);
CREATE UNIQUE INDEX IF NOT EXISTS permissions_idx ON plonks(server_id, entity_id);

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