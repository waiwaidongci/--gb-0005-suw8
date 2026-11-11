"""计算中断恢复：worker 进程被杀/重启后，running 任务按租约回收并以原编号重算完成。"""
import time
from datetime import datetime,timedelta,timezone
from pathlib import Path
from src.config.database import SessionLocal
from src.config.settings import ARTIFACT_DIR,JOB_QUEUE_KEY,RUN_LEASE_SECONDS
from src.constants.status import RunStatus
from src.models import ReportRun,Delivery,DeliverySchedule
from src.services.queue_service import queue
from src.services.worker_service import recover_pending,process_job
from conftest import start_worker,stop_worker,wait_for
def _schedule(db,name):
    sch=DeliverySchedule(name=name,dimensions=["channel","month"],interval_minutes=60,
                         next_run_at=(datetime.now(timezone.utc)+timedelta(days=1)).isoformat(),
                         active=True,owner="admin")
    db.add(sch);db.commit();return sch
def test_running_interrupted_then_recovered_with_same_id(seed_data):
    # 直接构造一份卡在 running、租约已过期的中断任务（模拟进程被 kill -9 后的落库状态）
    sch=_schedule(seed_data,"校对计划A")
    stale=(datetime.now(timezone.utc)-timedelta(seconds=RUN_LEASE_SECONDS+5)).isoformat()
    run=ReportRun(name="中断的定时交付",dimensions=["channel","month"],owner="scheduler",
                  schedule_id=sch.id,status=RunStatus.RUNNING,started_at=stale)
    seed_data.add(run);seed_data.commit()
    run_id=run.id
    # 对账：回收为 queued 并重新入队，编号不变
    recover_pending(seed_data)
    seed_data.expire_all()
    run=seed_data.get(ReportRun,run_id)
    assert run.status==RunStatus.QUEUED and run.started_at is None
    assert queue.lrange(JOB_QUEUE_KEY,0,-1)==[str(run_id)]
    # 重新执行后完成，原编号交付
    process_job(seed_data,str(run_id))
    seed_data.expire_all()
    run=seed_data.get(ReportRun,run_id)
    assert run.status==RunStatus.COMPLETED and run.id==run_id and run.result
    deliveries=seed_data.query(Delivery).filter_by(run_id=run_id).all()
    assert len(deliveries)==1 and deliveries[0].schedule_id==sch.id
def test_legacy_running_with_null_started_at_is_reclaimed(seed_data):
    """升级前遗留的 running 行（started_at 为空）也会被回收，不长期挂在处理中。"""
    sch=_schedule(seed_data,"校对计划遗留")
    run=ReportRun(name="遗留中断任务",dimensions=["channel","month"],owner="scheduler",
                  schedule_id=sch.id,status=RunStatus.RUNNING,started_at=None)
    seed_data.add(run);seed_data.commit();run_id=run.id
    recover_pending(seed_data)
    seed_data.expire_all()
    row=seed_data.get(ReportRun,run_id)
    assert row.status==RunStatus.QUEUED
    assert queue.lrange(JOB_QUEUE_KEY,0,-1)==[str(run_id)]
def test_fresh_running_lease_not_reclaimed(seed_data):
    sch=_schedule(seed_data,"校对计划B")
    run=ReportRun(name="正常计算中",dimensions=["channel","month"],owner="scheduler",
                  schedule_id=sch.id,status=RunStatus.RUNNING,
                  started_at=datetime.now(timezone.utc).isoformat())
    seed_data.add(run);seed_data.commit()
    recover_pending(seed_data)
    seed_data.expire_all()
    assert seed_data.get(ReportRun,run.id).status==RunStatus.RUNNING
def test_worker_restart_recovers_crashed_run_subprocess(seed_data):
    """端到端（真实 worker 二进制）：kill -9 留下的 running 行，重启后按租约恢复并交付，编号不变。"""
    sch=_schedule(seed_data,"校对计划C")
    stale=(datetime.now(timezone.utc)-timedelta(seconds=RUN_LEASE_SECONDS+5)).isoformat()
    run=ReportRun(name="端到端中断任务",dimensions=["channel","month"],owner="scheduler",
                  schedule_id=sch.id,status=RunStatus.RUNNING,started_at=stale)
    seed_data.add(run);seed_data.commit();run_id=run.id
    heartbeat=Path(ARTIFACT_DIR)/"heartbeat";heartbeat.unlink(missing_ok=True)
    proc,log=start_worker()
    try:
        assert wait_for(heartbeat.exists,timeout=15),"worker 未启动"
        def done():
            with SessionLocal() as db:
                row=db.get(ReportRun,run_id)
                return row is not None and row.status==RunStatus.COMPLETED
        assert wait_for(done,timeout=25),"重启后未恢复完成:\n"+Path(log.name).read_text()
        with SessionLocal() as db:
            row=db.get(ReportRun,run_id)
            assert row.id==run_id and row.result and not row.error
            assert db.query(Delivery).filter_by(run_id=run_id).count()==1
    finally:
        stop_worker(proc,log)
def test_worker_kill_then_restart_keeps_invariants(seed_data):
    """端到端：worker 任意时刻被硬杀并重启——无论杀在哪个阶段，最终都是同一编号、一条交付。"""
    sch=_schedule(seed_data,"校对计划D")
    run=ReportRun(name="硬杀重启任务",dimensions=["channel","month"],owner="scheduler",
                  schedule_id=sch.id,status=RunStatus.QUEUED)
    seed_data.add(run);seed_data.commit();run_id=run.id
    queue.rpush(JOB_QUEUE_KEY,run_id)
    heartbeat=Path(ARTIFACT_DIR)/"heartbeat";heartbeat.unlink(missing_ok=True)
    proc,log=start_worker()
    try:
        assert wait_for(heartbeat.exists,timeout=15),"worker 未启动"
        # 不依赖捕获毫秒级 running 窗口：直接硬杀，落库状态可能是 queued/running/completed
        time.sleep(0.05);proc.kill();proc.wait(timeout=10)
        time.sleep(RUN_LEASE_SECONDS+1)
        heartbeat.unlink(missing_ok=True)
        proc2,log2=start_worker()
        try:
            assert wait_for(heartbeat.exists,timeout=15),"新 worker 未启动"
            def done():
                with SessionLocal() as db:
                    row=db.get(ReportRun,run_id)
                    return row is not None and row.status==RunStatus.COMPLETED
            assert wait_for(done,timeout=25),"重启后未完成:\n"+Path(log2.name).read_text()
            with SessionLocal() as db:
                row=db.get(ReportRun,run_id)
                # 编号保留、结果存在、只产生一条交付、下一期计划不受影响
                assert row.id==run_id and row.result
                assert db.query(Delivery).filter_by(run_id=run_id).count()==1
                assert db.get(DeliverySchedule,sch.id).id==sch.id
        finally:
            stop_worker(proc2,log2)
    finally:
        if proc.poll() is None:stop_worker(proc,log)
        else:log.close()
def test_worker_consumes_queued_job_happy_path(seed_data):
    """端到端正常路径：真实 worker 从队列领取手工报表并完成，不产生交付（非定时）。"""
    run=ReportRun(name="手工端到端",dimensions=["channel"],owner="analyst",status=RunStatus.QUEUED)
    seed_data.add(run);seed_data.commit();run_id=run.id
    queue.rpush(JOB_QUEUE_KEY,run_id)
    heartbeat=Path(ARTIFACT_DIR)/"heartbeat";heartbeat.unlink(missing_ok=True)
    proc,log=start_worker()
    try:
        assert wait_for(heartbeat.exists,timeout=15),"worker 未启动"
        def done():
            with SessionLocal() as db:
                row=db.get(ReportRun,run_id)
                return row is not None and row.status==RunStatus.COMPLETED
        assert wait_for(done,timeout=20),"未完成:\n"+Path(log.name).read_text()
        with SessionLocal() as db:
            assert db.get(ReportRun,run_id).result
            assert db.query(Delivery).filter_by(run_id=run_id).count()==0
    finally:
        stop_worker(proc,log)
