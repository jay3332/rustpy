CREATE TABLE IF NOT EXISTS settings (
    user_id BIGINT NOT NULL PRIMARY KEY,
    preferred_rust_edition SMALLINT NOT NULL DEFAULT 1,
    preferred_rust_channel SMALLINT NOT NULL DEFAULT 2,
    preferred_rust_mode SMALLINT NOT NULL DEFAULT 0
);
