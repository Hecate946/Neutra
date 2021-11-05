CREATE TABLE IF NOT EXISTS usernames (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT,
    username TEXT,
    insertion TIMESTAMP DEFAULT (NOW() AT TIME ZONE 'UTC')
);
CREATE INDEX IF NOT EXISTS usernames_idx ON usernames(user_id, username);

-- Deprecated
-- CREATE TABLE IF NOT EXISTS activities (
--     id BIGSERIAL PRIMARY KEY,
--     user_id BIGINT,
--     activity TEXT,
--     insertion TIMESTAMP DEFAULT (NOW() AT TIME ZONE 'UTC')
-- );
-- CREATE INDEX IF NOT EXISTS activities_idx ON activities(user_id, activity);


CREATE TABLE IF NOT EXISTS usernicks (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT,
    server_id BIGINT,
    nickname TEXT,
    insertion TIMESTAMP DEFAULT (NOW() AT TIME ZONE 'UTC')
);
CREATE INDEX IF NOT EXISTS usernicks_idx ON usernicks(user_id, nickname);


CREATE TABLE IF NOT EXISTS userroles (
    user_id BIGINT,
    server_id BIGINT,
    roles TEXT,
    UNIQUE(user_id, server_id)
);

CREATE TABLE IF NOT EXISTS tracker (
    user_id BIGINT PRIMARY KEY,
    unix NUMERIC,
    action TEXT
);

CREATE TABLE IF NOT EXISTS userstatus (
    user_id BIGINT PRIMARY KEY,
    online DOUBLE PRECISION DEFAULT 0 NOT NULL,
    idle DOUBLE PRECISION DEFAULT 0 NOT NULL,
    dnd DOUBLE PRECISION DEFAULT 0 NOT NULL,
    last_changed DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()),
    starttime DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW())
);

CREATE TABLE IF NOT EXISTS avatars (
    hash TEXT PRIMARY KEY,
    url TEXT,
    msgid BIGINT,
    id bigint,
    size bigint,
    height bigint,
    width bigint,
    insertion TIMESTAMP DEFAULT (NOW() AT TIME ZONE 'UTC')
);

CREATE TABLE IF NOT EXISTS useravatars (
    user_id BIGINT,
    avatar TEXT,
    first_seen TIMESTAMP
);


CREATE TABLE IF NOT EXISTS voice (
    server_id BIGINT,
    user_id BIGINT,
    connected BOOLEAN,
    first_seen TIMESTAMP DEFAULT (NOW() AT TIME ZONE 'UTC')
);

CREATE TABLE IF NOT EXISTS statuses (
    user_id BIGINT,
    status TEXT,
    first_seen TIMESTAMP DEFAULT (NOW() AT TIME ZONE 'UTC')
);

CREATE TABLE IF NOT EXISTS whitelist (
    user_id BIGINT PRIMARY KEY
);