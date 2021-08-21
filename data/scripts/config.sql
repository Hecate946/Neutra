CREATE TABLE IF NOT EXISTS config (
    client_id BIGINT PRIMARY KEY,
    presence TEXT NOT NULL DEFAULT '',
    activity TEXT NOT NULL DEFAULT '',
    status TEXT,
    version REAL DEFAULT 1,
    ownerlocked BOOLEAN DEFAULT False,
    reboot_invoker TEXT,
    reboot_message_id BIGINT,
    reboot_channel_id BIGINT,
    reboot_count BIGINT NOT NULL DEFAULT 0,
    load_count BIGINT NOT NULL DEFAULT 0,
    unload_count BIGINT NOT NULL DEFAULT 0,
    reload_count BIGINT NOT NULL DEFAULT 0,
    runtime DOUBLE PRECISION DEFAULT 0.0 NOT NULL,
    starttime DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()),
    last_run DOUBLE PRECISION
);