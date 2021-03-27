CREATE TABLE IF NOT EXISTS servers (
    server_id bigint PRIMARY KEY,
    server_name varchar(100),
    owner_id bigint,
    prefix VARCHAR(5) DEFAULT '-',
    logchannel BIGINT,
    muterole BIGINT,
    antiinvite BOOLEAN DEFAULT False,
    filter_bool BOOLEAN DEFAULT False
);
