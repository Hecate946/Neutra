CREATE TABLE IF NOT EXISTS emojistats (
    serveremoji VARCHAR(50) PRIMARY KEY,
    server_id BIGINT,
    emoji_id BIGINT,
    total BIGINT DEFAULT 0 NOT NULL
);

CREATE TABLE IF NOT EXISTS messages (
    index BIGSERIAL PRIMARY KEY,
    unix REAL,
    timestamp TIMESTAMP,
    content TEXT,
    message_id BIGINT,
    author_id BIGINT,
    channel_id BIGINT,
    server_id BIGINT,
    deleted BOOLEAN DEFAULT False
);

CREATE TABLE IF NOT EXISTS commands (
    index BIGSERIAL PRIMARY KEY,
    server_id BIGINT,
    channel_id BIGINT,
    author_id BIGINT,
    timestamp TIMESTAMP,
    prefix TEXT,
    command TEXT,
    failed BOOLEAN
);