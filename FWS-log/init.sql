CREATE TABLE IF NOT EXISTS logs (
    id          BIGSERIAL PRIMARY KEY,
    timestamp   TIMESTAMPTZ NOT NULL DEFAULT now(),
    level       VARCHAR(10)  NOT NULL,
    module      VARCHAR(50),
    event       VARCHAR(50),
    message     TEXT         NOT NULL,
    vm_name     VARCHAR(50),
    server_ip   VARCHAR(20)
);

CREATE INDEX idx_logs_timestamp ON logs (timestamp DESC);
CREATE INDEX idx_logs_event     ON logs (event);
CREATE INDEX idx_logs_vm_name   ON logs (vm_name);
CREATE INDEX idx_logs_level     ON logs (level);
