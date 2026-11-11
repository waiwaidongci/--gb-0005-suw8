import logging,time,traceback
from pathlib import Path
from .config.database import SessionLocal,engine,Base
from .config.settings import ARTIFACT_DIR,JOB_QUEUE_KEY,RUN_LEASE_SECONDS
from .services.queue_service import queue
from .services.scheduler_service import schedule_due
from .services.worker_service import recover_pending,process_job
logging.basicConfig(level=logging.INFO,format="%(asctime)s %(levelname)s %(name)s %(message)s")
Base.metadata.create_all(engine);Path(ARTIFACT_DIR).mkdir(parents=True,exist_ok=True)
logging.info("worker 启动：租约=%ss 队列=%s",RUN_LEASE_SECONDS,JOB_QUEUE_KEY)
while True:
    Path(f"{ARTIFACT_DIR}/heartbeat").write_text(str(time.time()))
    try:
        with SessionLocal() as db:
            # 先对账：恢复中断任务、补推丢失的排队任务，再处理计划到期
            recover_pending(db)
            schedule_due(db)
        job=queue.blpop(JOB_QUEUE_KEY,timeout=2)
        if not job:continue
        with SessionLocal() as db:
            process_job(db,job[1])
    except Exception:
        traceback.print_exc();time.sleep(2)
