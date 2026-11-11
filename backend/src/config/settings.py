import os
DATABASE_URL=os.environ.get("DATABASE_URL","postgresql+psycopg://metric:metric@db/metric")
REDIS_URL=os.environ.get("REDIS_URL","redis://redis:6379/0")
JWT_SECRET=os.environ.get("JWT_SECRET","local-metric-ledger-change-this-key")
SEED_DEMO=os.environ.get("SEED_DEMO","true").lower()=="true"
ARTIFACT_DIR=os.environ.get("ARTIFACT_DIR","/artifacts")
# 运行租约秒数：超过该时长仍停留在 running 的任务视为进程中断，下一轮恢复
RUN_LEASE_SECONDS=int(os.environ.get("RUN_LEASE_SECONDS","120"))
# 入队失败时的即时重试次数与间隔（之后由 worker 对账循环兜底）
ENQUEUE_RETRY=int(os.environ.get("ENQUEUE_RETRY","3"))
ENQUEUE_RETRY_DELAY=float(os.environ.get("ENQUEUE_RETRY_DELAY","0.5"))
JOB_QUEUE_KEY="metric:jobs"
