CREATE TABLE IF NOT EXISTS useravatars (
    user_id BIGINT PRIMARY KEY,
    avatars TEXT
);

CREATE TABLE IF NOT EXISTS nicknames (
    serveruser VARCHAR(50) PRIMARY KEY,
    user_id BIGINT,
    server_id BIGINT,
    nicknames TEXT
);

CREATE TABLE IF NOT EXISTS usernames (
    user_id BIGINT PRIMARY KEY,
    usernames TEXT
);

CREATE TABLE IF NOT EXISTS userroles (
    serveruser VARCHAR(50) PRIMARY KEY,
    user_id BIGINT,
    server_id BIGINT,
    roles TEXT
);

