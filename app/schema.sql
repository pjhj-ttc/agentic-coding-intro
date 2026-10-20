DROP TABLE IF EXISTS tip_events;
DROP TABLE IF EXISTS agent_log;
DROP TABLE IF EXISTS triage;
DROP TABLE IF EXISTS sources;
DROP TABLE IF EXISTS tips;

CREATE TABLE tips (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  subject TEXT NOT NULL,
  body TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'new'  -- 'new', 'triaged', 'escalated', 'closed'
);

-- Day 3: who sent a tip. Only the editor view reads this table; the triage agent never does.
-- No row means the source is anonymous.
CREATE TABLE sources (
  tip_id INTEGER PRIMARY KEY REFERENCES tips(id),
  contact_method TEXT NOT NULL, -- 'email', 'phone', 'signal'
  contact_value TEXT NOT NULL   -- the address/number
);

-- Day 2: the triage agent's assessment of a tip (at most one row per tip)
CREATE TABLE triage (
  tip_id INTEGER PRIMARY KEY REFERENCES tips(id),
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  desk TEXT NOT NULL,           -- 'politics', 'business', 'environment', 'health', 'local', 'none'
  urgency TEXT NOT NULL,        -- 'high', 'normal', 'low'
  duplicate_of INTEGER REFERENCES tips(id),  -- earlier tip about the same story, or NULL
  summary TEXT NOT NULL,        -- short summary for the editor
  model TEXT,                   -- which model made the assessment
  suggest_escalation INTEGER NOT NULL DEFAULT 0  -- Day 3: 1 = the agent suggests escalating; an editor decides
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

-- Day 3: the chain of custody of each tip, one row per event. Never holds contact details.
CREATE TABLE tip_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  tip_id INTEGER NOT NULL REFERENCES tips(id),
  event TEXT NOT NULL,          -- 'received', 'flagged', 'triaged', 'triage_failed', 'escalated'
  actor TEXT NOT NULL,          -- 'source', 'system', 'agent', or the editor's name
  detail TEXT                   -- JSON: run id, decision, ...
);
