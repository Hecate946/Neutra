CREATE TABLE IF NOT EXISTS nicknames (
    user_id BIGINT,
    server_id BIGINT,
    nicknames TEXT,
    UNIQUE(user_id, server_id)
);

CREATE TABLE IF NOT EXISTS usernames (
    user_id BIGINT PRIMARY KEY,
    usernames TEXT
);

CREATE TABLE IF NOT EXISTS userroles (
    user_id BIGINT,
    server_id BIGINT,
    roles TEXT,
    UNIQUE(user_id, server_id)
);

CREATE TABLE IF NOT EXISTS usertime (
    user_id BIGINT PRIMARY KEY,
    timezone VARCHAR(100)
);

CREATE TABLE IF NOT EXISTS tracker (
    user_id BIGINT PRIMARY KEY,
    unix BIGINT
);

CREATE TABLE IF NOT EXISTS spammers (
    user_id BIGINT,
    server_id BIGINT,
    spamcount BIGINT,
    UNIQUE(user_id, server_id)
);

-- This table has been dropped and is no longer used.
-- CREATE TABLE IF NOT EXISTS useravatars (
--     user_id BIGINT PRIMARY KEY,
--     avatars TEXT
-- );