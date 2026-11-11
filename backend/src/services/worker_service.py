import json,logging
from datetime import datetime,timedelta,timezone
from pathlib import Path
from sqlalchemy import update
from sqlalchemy.exc import IntegrityError
from ..config.settings import ARTIFACT_DIR,RUN_LEASE_SECONDS,JOB_QUEUE_KEY
from ..models import ReportRun,SourceRow,Metric,Delivery
from ..constants.status import RunStatus
from .pivot_service import build_report
from .queue_service import queue,enqueue
from .audit_service import log
def _now_iso():return datetime.now(timezone.utc).isoformat()
def recover_pending(db):
    """对账：补推队列里丢失的 queued 任务，回收租约过期的 running 任务（进程中断恢复）。"""
    queued=db.query(ReportRun).filter_by(status=RunStatus.QUEUED).all()
    queued_ids=[run.id for run in queued]
    if queued_ids:
        missing=set(queued_ids)
        try:
            pending=set(int(x) for x in queue.lrange(JOB_QUEUE_KEY,0,-1))
            missing=missing-pending
        except Exception as exc:
            logging.warning("读取队列失败，跳过本轮对账: %s",exc)
        for rid in sorted(missing):
            try:
                enqueue(rid);logging.info("对账补推报表 %s",rid)
            except Exception as exc:
                logging.error("对账补推报表 %s 失败: %s",rid,exc)
    lease_deadline=(datetime.now(timezone.utc)-timedelta(seconds=RUN_LEASE_SECONDS)).isoformat()
    # started_at 为空的 running 是升级前遗留或异常中断行，同样按中断回收
    stale=db.query(ReportRun).filter(
        ReportRun.status==RunStatus.RUNNING,
        (ReportRun.started_at.is_(None))|(ReportRun.started_at<=lease_deadline),
    ).all()
    for run in stale:
        run.status=RunStatus.QUEUED;run.started_at=None;run.error=""
        log(db,"worker","report.recover",run.id)
        logging.info("回收中断报表 %s（租约过期），保留原编号重新排队",run.id)
    if stale:db.commit()
    for run in stale:
        try:enqueue(run.id)
        except Exception as exc:logging.error("中断报表 %s 重新入队失败: %s",run.id,exc)
def claim_run(db,run_id):
    """条件更新原子领取：仅 queued 任务可被领取，并发领取同一期只有一个赢家。"""
    started=_now_iso()
    result=db.execute(update(ReportRun).where(ReportRun.id==run_id,ReportRun.status==RunStatus.QUEUED).values(status=RunStatus.RUNNING,started_at=started)).rowcount
    db.commit()
    if result:return db.get(ReportRun,run_id)
    return None
def complete_run(db,run):
    """执行计算并落盘；定时报表的交付记录按 run_id 幂等，重复投递只产生一条。"""
    run.result=build_report(db.query(SourceRow).order_by(SourceRow.id).all(),db.query(Metric).order_by(Metric.id).all(),run.dimensions)
    run.status=RunStatus.COMPLETED;run.error="";run.started_at=None
    Path(ARTIFACT_DIR).mkdir(parents=True,exist_ok=True)
    Path(f"{ARTIFACT_DIR}/report-{run.id}.json").write_text(json.dumps(run.result,ensure_ascii=False))
    if run.schedule_id:
        try:
            with db.begin_nested():
                db.add(Delivery(schedule_id=run.schedule_id,run_id=run.id,title=run.name))
        except IntegrityError:
            # 同一 run 已存在交付（重复投递/并发领取）：跳过，绝不产生第二条
            logging.info("报表 %s 的交付记录已存在，跳过重复投递",run.id)
    log(db,"worker","report.delivered" if run.schedule_id else "report.completed",run.id)
    db.commit()
def fail_run(db,run_id,exc):
    db.rollback()
    run=db.get(ReportRun,run_id)
    if run and run.status==RunStatus.RUNNING:
        run.status=RunStatus.FAILED;run.error=str(exc);run.started_at=None;db.commit()
def process_job(db,job_id):
    run=db.get(ReportRun,int(job_id))
    if not run or run.status not in (RunStatus.QUEUED,RunStatus.RUNNING):return
    run=claim_run(db,run.id)
    if not run:return
    try:
        complete_run(db,run)
    except Exception as exc:
        logging.exception("报表 %s 计算失败",run.id)
        fail_run(db,run.id,exc)
