CREATE TABLE IF NOT EXISTS queues (
    id BIGSERIAL PRIMARY KEY,
    owner_id BIGINT,
    name TEXT,
    queue JSONB DEFAULT '{}'::JSONB,
    insertion TIMESTAMP DEFAULT (NOW() AT TIME ZONE 'UTC')
);
CREATE UNIQUE INDEX IF NOT EXISTS queues_idx ON queues(owner_id, name);

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

CREATE TABLE IF NOT EXISTS voicetime (
    server_id BIGINT PRIMARY KEY,
    user_id BIGINT,
    seconds DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    lastchanged DOUBLE PRECISION NOT NULL DEFAULT EXTRACT(EPOCH FROM NOW()),
    starttime DOUBLE PRECISION NOT NULL DEFAULT EXTRACT(EPOCH FROM NOW())
);

CREATE TABLE IF NOT EXISTS spotify (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT,
    album_id TEXT,
    artist_id TEXT,
    track_id TEXT,
    insertion TIMESTAMP DEFAULT (NOW() AT TIME ZONE 'UTC')
);