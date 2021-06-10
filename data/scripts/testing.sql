CREATE TABLE IF NOT EXISTS testavs (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT,
    avatar BIGINT,
    insertion TIMESTAMP DEFAULT (NOW() AT TIME ZONE 'UTC')
);
CREATE INDEX IF NOT EXISTS testavs_idx ON testavs(user_id, avatar);

CREATE TABLE IF NOT EXISTS logs (
    server_id BIGINT PRIMARY KEY,
    channels BOOLEAN DEFAULT True,
    emojis BOOLEAN DEFAULT True,
    invites BOOLEAN DEFAULT True,
    joins BOOLEAN DEFAULT True,
    messages BOOLEAN DEFAULT True,
    moderation BOOLEAN DEFAULT True,
    users BOOLEAN DEFAULT True,
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

CREATE TABLE IF NOT EXISTS webhooks (
    server_id BIGINT PRIMARY KEY,
    webhook TEXT,
    channels_webhook TEXT,
    emojis_webhook TEXT,
    invites_webhook TEXT,
    joins_webhook TEXT,
    messages_webhook TEXT,
    moderation_webhook TEXT,
    users_webhook TEXT,
    roles_webhook TEXT,
    server_webhook TEXT,
    voice_webhook TEXT
);