DROP TABLE IF EXISTS agent_log;
DROP TABLE IF EXISTS triage;
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

-- Day 2: the triage agent's assessment of a tip (at most one row per tip)
CREATE TABLE triage (
  tip_id INTEGER PRIMARY KEY REFERENCES tips(id),
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  desk TEXT NOT NULL,           -- 'politics', 'business', 'environment', 'health', 'local', 'none'
  urgency TEXT NOT NULL,        -- 'high', 'normal', 'low'
  duplicate_of INTEGER REFERENCES tips(id),  -- earlier tip about the same story, or NULL
  summary TEXT NOT NULL,        -- short summary for the editor
  model TEXT                    -- which model made the assessment
);

-- Day 2: everything the triage agent does, one row per event
CREATE TABLE agent_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  run_id TEXT NOT NULL,         -- groups the events of one agent run
  tip_id INTEGER,               -- the tip being triaged, if any
  event TEXT NOT NULL,          -- 'model_call', 'tool_call', 'error'
  name TEXT,                    -- tool name, for tool calls
  detail TEXT                   -- JSON: arguments, result, token usage, error message
);
