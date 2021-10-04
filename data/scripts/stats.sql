CREATE TABLE IF NOT EXISTS emojidata (
    index BIGSERIAL PRIMARY KEY,
    server_id BIGINT,
    author_id BIGINT,
    emoji_id BIGINT,
    total BIGINT DEFAULT 0 NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS emojidata_idx ON emojidata(server_id, author_id, emoji_id);

CREATE TABLE IF NOT EXISTS messages (
    index BIGSERIAL PRIMARY KEY,
    unix REAL,
    timestamp TIMESTAMP,
    -- content TEXT, # DROPPED AND DEPRECATED FOR DISCORD VERIFICATION REQUIREMENTS.
    message_id BIGINT,
    author_id BIGINT,
    channel_id BIGINT,
    server_id BIGINT,
    deleted BOOLEAN DEFAULT False,
    edited BOOLEAN DEFAULT False
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