DROP TABLE IF EXISTS tips;

CREATE TABLE tips (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  subject TEXT NOT NULL,
  body TEXT NOT NULL,
  contact_method TEXT,          -- 'email', 'phone', 'signal', or NULL for anonymous
  contact_value TEXT,           -- the address/number, or NULL for anonymous
  status TEXT NOT NULL DEFAULT 'new'  -- 'new', 'triaged', 'escalated', 'closed'
);
