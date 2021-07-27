CREATE TABLE IF NOT EXISTS servers (
    server_id BIGINT PRIMARY KEY,
    muterole BIGINT,
    antiinvite BOOLEAN DEFAULT False,
    reassign BOOLEAN DEFAULT True,
    autoroles BIGINT[] DEFAULT '{}',
    profanities TEXT[] DEFAULT '{}'
);

-- CREATE TABLE IF NOT EXISTS autoroles (
--     server_id BIGINT PRIMARY KEY,
--     autorole BIGINT
-- );

-- CREATE TABLE IF NOT EXISTS profanities (
--     server_id BIGINT PRIMARY KEY,
--     profanities TEXT[] DEFAULT '{}',
--     languages TEXT[] DEFAULT '{en}'
--     default BOOLEAN DEFAULT False,
-- );

-- CREATE TABLE IF NOT EXISTS languages (
--     server_id BIGINT PRIMARY KEY,
--     belarusian BOOLEAN DEFAULT False,
--     bulgarian BOOLEAN DEFAULT False,
--     catalan BOOLEAN DEFAULT False,
--     czech BOOLEAN DEFAULT False,
--     welsh BOOLEAN DEFAULT False,
--     danish BOOLEAN DEFAULT False,
--     german BOOLEAN DEFAULT False,
--     greek BOOLEAN DEFAULT False,
--     english BOOLEAN DEFAULT True,
--     spanish BOOLEAN DEFAULT False,
--     estonian BOOLEAN DEFAULT False,
--     basque BOOLEAN DEFAULT False,
--     farsi BOOLEAN DEFAULT False,
--     finnish BOOLEAN DEFAULT False,
--     french BOOLEAN DEFAULT False,
--     gaelic BOOLEAN DEFAULT False,
--     galician BOOLEAN DEFAULT False,
--     hindi BOOLEAN DEFAULT False,
--     croatian BOOLEAN DEFAULT False,
--     hungarian BOOLEAN DEFAULT False,
--     armenian BOOLEAN DEFAULT False,
--     indonesian BOOLEAN DEFAULT False,
--     icelandic BOOLEAN DEFAULT False,
--     italian BOOLEAN DEFAULT False,
--     japanese BOOLEAN DEFAULT False,
--     kannada BOOLEAN DEFAULT False,
--     korean BOOLEAN DEFAULT False,
--     kannada BOOLEAN DEFAULT False,
--     latin BOOLEAN DEFAULT False,
--     lithuanian BOOLEAN DEFAULT False,
--     latvian BOOLEAN DEFAULT False,
--     macedonian BOOLEAN DEFAULT False,
--     malayalam BOOLEAN DEFAULT False,
--     mongolian BOOLEAN DEFAULT False,
--     marathi BOOLEAN DEFAULT False,
--     malay BOOLEAN DEFAULT False,
--     maltese BOOLEAN DEFAULT False,
--     burmese BOOLEAN DEFAULT False,
--     dutch BOOLEAN DEFAULT False,
--     polish BOOLEAN DEFAULT False,
--     portuguese BOOLEAN DEFAULT False,
--     romanian BOOLEAN DEFAULT False,
--     russian BOOLEAN DEFAULT False,
--     slovak BOOLEAN DEFAULT False,
--     slovenian BOOLEAN DEFAULT False,
--     albanian BOOLEAN DEFAULT False,
--     serbian BOOLEAN DEFAULT False,
--     swedish BOOLEAN DEFAULT False,
--     telugu BOOLEAN DEFAULT False,
--     thai BOOLEAN DEFAULT False,
--     turkish BOOLEAN DEFAULT False,
--     ukrainian BOOLEAN DEFAULT False,
--     uzbek BOOLEAN DEFAULT False,
--     vietnamese BOOLEAN DEFAULT False,
--     zulu BOOLEAN DEFAULT False
-- );

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