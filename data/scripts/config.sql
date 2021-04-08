CREATE TABLE IF NOT EXISTS blacklist (
    user_id BIGINT PRIMARY KEY,
    author_id BIGINT, -- OK this will only be the owner but ¯\＿( ͡° ͜ʖ ͡°)＿/¯
    reason TEXT,
    react BOOLEAN,
    timestamp TIMESTAMP
);

CREATE TABLE IF NOT EXISTS serverblacklist (
    server_id BIGINT PRIMARY KEY,
    reason TEXT,
    timestamp TIMESTAMP,
    executor TEXT,
    react BOOLEAN
);

CREATE TABLE IF NOT EXISTS settings (
    disabled_commands TEXT,
    react BOOLEAN DEFAULT True,
    admin_allow BOOLEAN DEFAULT True
);