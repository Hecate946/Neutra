CREATE TABLE IF NOT EXISTS queues (
    id BIGSERIAL PRIMARY KEY,
    owner_id BIGINT,
    name TEXT,
    queue JSONB DEFAULT '{}'::JSONB,
    insertion TIMESTAMP DEFAULT (NOW() AT TIME ZONE 'UTC')
);

-- Automatically saved songs
CREATE TABLE IF NOT EXISTS tracks (
    id BIGSERIAL PRIMARY KEY,
    requester_id BIGINT,
    title TEXT,
    url TEXT,
    uploader TEXT,
    insertion TIMESTAMP DEFAULT (NOW() AT TIME ZONE 'UTC')
);

-- User specifically saved songs
CREATE TABLE IF NOT EXISTS saved (
    id BIGSERIAL PRIMARY KEY,
    requester_id BIGINT,
    title TEXT,
    url TEXT,
    uploader TEXT,
    insertion TIMESTAMP DEFAULT (NOW() AT TIME ZONE 'UTC')
);

CREATE TABLE IF NOT EXISTS musicconf (
    server_id BIGINT PRIMARY KEY,
    bind BIGINT,
    djrole BIGINT,
    djlock BOOLEAN NOT NULL DEFAULT False
);