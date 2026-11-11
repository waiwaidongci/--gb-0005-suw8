"""重复投递与并发领取：每份报表只产生一条交付记录，同一计划同一期只有一个运行编号。"""
from datetime import datetime,timedelta,timezone
import pytest
from sqlalchemy.exc import IntegrityError
from src.constants.status import RunStatus
from src.models import ReportRun,Delivery,DeliverySchedule
from src.services.worker_service import claim_run,complete_run,process_job
from src.config.settings import JOB_QUEUE_KEY
from src.services.queue_service import queue
def _schedule(db,name="并发校对计划"):
    sch=DeliverySchedule(name=name,dimensions=["channel","month"],interval_minutes=60,
                         next_run_at=(datetime.now(timezone.utc)+timedelta(days=1)).isoformat(),
                         active=True,owner="admin")
    db.add(sch);db.commit();return sch
def test_concurrent_claim_single_winner(seed_data):
    sch=_schedule(seed_data)
    run=ReportRun(name="并发领取任务",dimensions=["channel","month"],owner="scheduler",
                  schedule_id=sch.id,status=RunStatus.QUEUED)
    seed_data.add(run);seed_data.commit();run_id=run.id
    # 两个独立会话同时领取（模拟两个 worker / 重复 BLPOP 同一消息）
    from src.config.database import SessionLocal
    with SessionLocal() as db_a,SessionLocal() as db_b:
        winner_a=claim_run(db_a,run_id)
        winner_b=claim_run(db_b,run_id)
    outcomes=[bool(winner_a),bool(winner_b)]
    assert outcomes.count(True)==1
    with SessionLocal() as db:
        assert db.get(ReportRun,run_id).status==RunStatus.RUNNING
def test_duplicated_queue_message_completes_once(seed_data):
    """同一报表编号被投递两次（at-least-once）：只完成一次、只产生一条交付。"""
    sch=_schedule(seed_data,"重复投递计划")
    run=ReportRun(name="重复消息任务",dimensions=["channel","month"],owner="scheduler",
                  schedule_id=sch.id,status=RunStatus.QUEUED)
    seed_data.add(run);seed_data.commit();run_id=run.id
    queue.rpush(JOB_QUEUE_KEY,run_id)
    queue.rpush(JOB_QUEUE_KEY,run_id)
    process_job(seed_data,str(run_id))
    # 第二条重复消息：已完成，直接跳过，不报错也不重复交付
    process_job(seed_data,str(run_id))
    assert seed_data.query(Delivery).filter_by(run_id=run_id).count()==1
def test_duplicate_delivery_insert_is_idempotent(seed_data):
    """complete_run 重放（如重复领取后两边都走到交付）：唯一约束兜底，仍只有一条交付。"""
    sch=_schedule(seed_data,"幂等交付计划")
    run=ReportRun(name="幂等交付任务",dimensions=["channel","month"],owner="scheduler",
                  schedule_id=sch.id,status=RunStatus.QUEUED)
    seed_data.add(run);seed_data.commit();run_id=run.id
    run=claim_run(seed_data,run_id)
    complete_run(seed_data,run)
    seed_data.expire_all()
    # 人为再插一条同 run_id 交付必须被唯一约束拒绝
    with pytest.raises(IntegrityError):
        seed_data.add(Delivery(schedule_id=sch.id,run_id=run_id,title="重复"))
        seed_data.flush()
    seed_data.rollback()
    assert seed_data.query(Delivery).filter_by(run_id=run_id).count()==1
def test_one_open_run_per_schedule_partial_index(seed_data):
    """同一计划不允许两份 queued/running 运行；completed 之后可以开启下一期。"""
    sch=_schedule(seed_data,"唯一开放运行计划")
    first=ReportRun(name="第一期",dimensions=["channel","month"],owner="scheduler",
                    schedule_id=sch.id,status=RunStatus.QUEUED)
    seed_data.add(first);seed_data.commit()
    dup=ReportRun(name="重复一期",dimensions=["channel","month"],owner="scheduler",
                  schedule_id=sch.id,status=RunStatus.RUNNING)
    seed_data.add(dup)
    with pytest.raises(IntegrityError):
        seed_data.flush()
    seed_data.rollback()
    # 第一期完成后，下一期可以正常创建
    first.status=RunStatus.COMPLETED;first.started_at=None;seed_data.commit()
    nxt=ReportRun(name="第二期",dimensions=["channel","month"],owner="scheduler",
                  schedule_id=sch.id,status=RunStatus.QUEUED)
    seed_data.add(nxt);seed_data.commit()
    assert nxt.id!=first.id
    # 手工报表（schedule_id 为空）不受部分唯一索引限制，可并行多份
    m1=ReportRun(name="手工A",dimensions=["channel"],owner="analyst",status=RunStatus.QUEUED)
    m2=ReportRun(name="手工B",dimensions=["channel"],owner="analyst",status=RunStatus.QUEUED)
    seed_data.add_all([m1,m2]);seed_data.commit()
def test_scheduler_dedup_same_period_single_run(seed_data):
    """计划到期被重复扫描（队列故障/多轮恢复）时，同一期只复用同一报表编号。"""
    from src.services.scheduler_service import schedule_due
    sch=_schedule(seed_data,"重复扫描计划")
    sch.next_run_at=(datetime.now(timezone.utc)-timedelta(seconds=10)).isoformat()
    seed_data.commit()
    schedule_due(seed_data)
    first_id=seed_data.query(ReportRun).filter_by(schedule_id=sch.id).one().id
    # 立刻再扫描（本期未结束前不会到期，模拟反复对账）
    schedule_due(seed_data)
    runs=seed_data.query(ReportRun).filter_by(schedule_id=sch.id).all()
    assert len(runs)==1 and runs[0].id==first_id
