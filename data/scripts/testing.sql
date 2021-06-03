CREATE TABLE IF NOT EXISTS testavs (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT,
    avatar BIGINT,
    insertion TIMESTAMP DEFAULT (NOW() AT TIME ZONE 'UTC')
);
CREATE INDEX IF NOT EXISTS testavs_idx ON testavs(user_id, avatar);