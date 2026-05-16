CREATE TABLE IF NOT EXISTS user_dashboards (
    user_id INTEGER PRIMARY KEY,
    kanban_data TEXT,
    activity_data TEXT,
    stats_data TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);
