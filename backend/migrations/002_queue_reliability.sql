-- 002: 队列可靠性 —— 运行租约与单期唯一约束。
-- 新部署由 SQLAlchemy metadata 直接建表；本脚本用于升级已存在的部署（PostgreSQL）。
ALTER TABLE report_runs ADD COLUMN IF NOT EXISTS started_at VARCHAR;

-- 同一交付计划至多存在一份未结束（queued/running）的运行，重复领取同一期复用原编号。
CREATE UNIQUE INDEX IF NOT EXISTS uq_report_run_open_per_schedule
    ON report_runs (schedule_id)
    WHERE status IN ('queued','running');

-- 租约回收扫描索引：worker 定期查找中断在 running 的任务。
CREATE INDEX IF NOT EXISTS report_runs_status_started_idx
    ON report_runs (status, started_at);
