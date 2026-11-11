"""手工报表入队失败重试：队列故障时保留原编号，恢复后对账补推并正常完成。"""
from src.config.settings import JOB_QUEUE_KEY
from src.constants.status import RunStatus
from src.models import ReportRun
from src.services.queue_service import queue,enqueue
from src.services.report_service import create_run
from src.services.worker_service import recover_pending
class _User:
    email="analyst@hengchi.demo";name="宋予"
class _Data:
    name="手工核对报表";dimensions=["channel","month"]
def test_manual_enqueue_retried_after_queue_outage(seed_data,monkeypatch):
    # 1. 模拟队列完全故障：即时重试耗尽后仍返回 202，报表保留 queued 与原编号
    calls={"n":0}
    def broken_rpush(*a,**k):
        calls["n"]+=1;raise ConnectionError("redis down")
    monkeypatch.setattr(queue,"rpush",broken_rpush)
    saved=create_run(seed_data,_Data(),_User())
    assert saved["status"]==RunStatus.QUEUED
    run_id=saved["id"]
    assert calls["n"]==3  # 初次 + 2 次重试
    assert queue.llen(JOB_QUEUE_KEY)==0
    # 队列恢复：撤销故障注入，worker 对账循环把丢失的 queued 任务补推回原队列
    monkeypatch.undo()
    recover_pending(seed_data)
    assert queue.lrange(JOB_QUEUE_KEY,0,-1)==[str(run_id)]
    # 3. 编号不变，状态仍是同一份报表
    assert seed_data.get(ReportRun,run_id).id==run_id
def test_scheduler_enqueue_failure_keeps_run_and_next_plan(seed_data):
    """定时交付入队失败：本期报表不丢、编号不变、下一期计划照常推进，恢复后补推。"""
    from datetime import datetime,timedelta,timezone
    from src.models import DeliverySchedule
    from src.services.scheduler_service import schedule_due
    now=datetime.now(timezone.utc)
    sch=DeliverySchedule(name="分钟校对计划",dimensions=["channel","month"],interval_minutes=1,
                         next_run_at=(now-timedelta(seconds=5)).isoformat(),active=True,owner="admin")
    seed_data.add(sch);seed_data.commit()
    original_next=(now-timedelta(seconds=5)).isoformat()
    import src.services.scheduler_service as sched_mod
    real_enqueue=sched_mod.enqueue
    def failing_enqueue(run_id):raise ConnectionError("redis down")
    sched_mod.enqueue=failing_enqueue
    try:
        schedule_due(seed_data)
    finally:
        sched_mod.enqueue=real_enqueue
    seed_data.expire_all()
    sch=seed_data.get(DeliverySchedule,sch.id)
    # 下一期时间已推进，不受队列故障影响
    assert sch.next_run_at>original_next
    runs=seed_data.query(ReportRun).filter_by(schedule_id=sch.id).all()
    assert len(runs)==1
    run=runs[0]
    assert run.status==RunStatus.QUEUED  # 本期报表保留排队，未丢失
    run_id=run.id
    # 再次扫描到期时间之前不应重复建行
    schedule_due(seed_data)
    assert seed_data.query(ReportRun).filter_by(schedule_id=sch.id).count()==1
    # 队列恢复：对账补推，编号不变
    recover_pending(seed_data)
    assert queue.lrange(JOB_QUEUE_KEY,0,-1)==[str(run_id)]
    assert seed_data.get(ReportRun,run_id).id==run_id
def test_enqueue_helper_retries_then_succeeds(monkeypatch):
    state={"n":0}
    real=queue.rpush
    def flaky(key,val):
        state["n"]+=1
        if state["n"]<2:raise ConnectionError("blip")
        return real(key,val)
    monkeypatch.setattr(queue,"rpush",flaky)
    enqueue(99)
    assert queue.lrange(JOB_QUEUE_KEY,0,-1)==["99"]
