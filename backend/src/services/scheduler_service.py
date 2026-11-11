import logging
from datetime import datetime,timedelta,timezone
from sqlalchemy.exc import IntegrityError
from ..models import DeliverySchedule,ReportRun
from ..constants.status import RunStatus
from .queue_service import enqueue
from .audit_service import log
_OPEN_STATES=(RunStatus.QUEUED,RunStatus.RUNNING)
def schedule_due(db):
    now=datetime.now(timezone.utc)
    due=db.query(DeliverySchedule).filter(DeliverySchedule.active.is_(True),DeliverySchedule.next_run_at<=now.isoformat()).all()
    for schedule in due:
        # 同一计划已有未结束运行时复用它：同一期只有一个报表编号，绝不重复建行/重复投递
        run=db.query(ReportRun).filter(ReportRun.schedule_id.is_(schedule.id),ReportRun.status.in_(_OPEN_STATES)).first()
        created=False
        if run is None:
            run=ReportRun(name=schedule.name+" · 定时交付",dimensions=schedule.dimensions,owner="scheduler",schedule_id=schedule.id)
            db.add(run)
            try:
                db.flush();created=True
            except IntegrityError:
                # 并发调度器已先创建本期运行：回滚后等下一轮对账，不重复建行、不推进计划
                db.rollback();continue
        schedule.next_run_at=(now+timedelta(minutes=schedule.interval_minutes)).isoformat()
        log(db,"scheduler","schedule.due",schedule.id);db.commit()
        # 仅新建的运行需要入队；已存在的开放运行由 worker 对账循环保证在队列里
        if not created:continue
        # 队列故障不回滚计划：运行保留 queued 与原编号，由 worker 对账循环补推
        try:
            enqueue(run.id)
        except Exception as exc:
            logging.error("计划 %s 的报表 %s 入队失败，等待对账补推: %s",schedule.id,run.id,exc)
