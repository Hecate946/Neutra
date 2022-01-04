
CREATE TABLE IF NOT EXISTS spotify_auth (
    user_id BIGINT PRIMARY KEY,
    token_info JSONB DEFAULT '{}'::JSONB
);


CREATE TABLE IF NOT EXISTS discord_auth (
    user_id BIGINT PRIMARY KEY,
    token_info JSONB DEFAULT '{}'::JSONB
);