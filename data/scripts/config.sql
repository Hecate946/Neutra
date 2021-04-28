CREATE TABLE IF NOT EXISTS settings (
    disabled_commands TEXT,
    react BOOLEAN DEFAULT True,
    admin_allow BOOLEAN DEFAULT True
);

CREATE TABLE IF NOT EXISTS botstats (
    runtime BIGINT,
    startdate TIMESTAMP
);