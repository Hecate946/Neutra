CREATE TABLE IF NOT EXISTS config (
    client_id BIGINT PRIMARY KEY,
    avatar_saver_webhook_id BIGINT,
    avatar_saver_webhook_token TEXT,
    presence TEXT,
    activity TEXT,
    status TEXT,
    version REAL DEFAULT 5, --Implemented automatic verions in 5.0
    ownerlocked BOOLEAN DEFAULT False,
    reboot_invoker TEXT,
    reboot_message_id BIGINT,
    reboot_channel_id BIGINT,
    runtime DOUBLE PRECISION DEFAULT 0.0 NOT NULL,
    starttime DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()),
    last_run DOUBLE PRECISION
);