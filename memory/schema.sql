CREATE TABLE IF NOT EXISTS facts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subject TEXT NOT NULL,
    fact TEXT NOT NULL,
    valid_from TEXT NOT NULL,
    valid_to TEXT,
    observed_at TEXT NOT NULL,
    embedding BLOB
);

CREATE INDEX IF NOT EXISTS facts_subject_open ON facts(subject, valid_to);
CREATE VIRTUAL TABLE IF NOT EXISTS facts_fts USING fts5(fact, subject);
