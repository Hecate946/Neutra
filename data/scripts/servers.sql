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

CREATE TABLE IF NOT EXISTS logs (
    server_id BIGINT PRIMARY KEY,
    avatars BOOLEAN DEFAULT True,
    channels BOOLEAN DEFAULT True,
    emojis BOOLEAN DEFAULT True,
    invites BOOLEAN DEFAULT True,
    joins BOOLEAN DEFAULT True,
    leaves BOOLEAN DEFAULT True,
    messages BOOLEAN DEFAULT True,
    moderation BOOLEAN DEFAULT True,
    nicknames BOOLEAN DEFAULT True,
    usernames BOOLEAN DEFAULT True,
    roles BOOLEAN DEFAULT True,
    server BOOLEAN DEFAULT True,
    voice BOOLEAN DEFAULT True
);

CREATE TABLE IF NOT EXISTS log_data (
    server_id BIGINT PRIMARY KEY,
    channel_id BIGINT,
    webhook_id BIGINT,
    webhook_token TEXT,
    entities BIGINT[] DEFAULT '{}'
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

CREATE TABLE IF NOT EXISTS warns (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT,
    server_id BIGINT,
    reason TEXT,
    insertion TIMESTAMP DEFAULT (NOW() AT TIME ZONE 'UTC')
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