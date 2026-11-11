-- Initial tables are defined by SQLAlchemy metadata; reviewed migrations required for upgrades.
CREATE INDEX IF NOT EXISTS source_dimensions_idx ON source_rows (channel,day);
CREATE INDEX IF NOT EXISTS schedules_due_idx ON delivery_schedules (active,next_run_at);
