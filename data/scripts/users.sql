CREATE TABLE IF NOT EXISTS usernicks (
    user_id BIGINT,
    server_id BIGINT,
    nickname TEXT,
    changed_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS usernames (
    user_id BIGINT,
    name TEXT,
    changed_at TIMESTAMP
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
    unix NUMERIC,
    action TEXT
);

CREATE TABLE IF NOT EXISTS spammers (
    user_id BIGINT,
    server_id BIGINT,
    spamcount BIGINT,
    UNIQUE(user_id, server_id)
);

CREATE TABLE IF NOT EXISTS useravatars (
    user_id BIGINT,
    avatar_id BIGINT,
    unix REAL
);

CREATE TABLE IF NOT EXISTS userstatus (
    user_id BIGINT PRIMARY KEY,
    online DOUBLE PRECISION DEFAULT 0 NOT NULL,
    idle DOUBLE PRECISION DEFAULT 0 NOT NULL,
    dnd DOUBLE PRECISION DEFAULT 0 NOT NULL,
    last_changed DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()),
    starttime DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW())
);