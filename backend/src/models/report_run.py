from sqlalchemy import JSON,ForeignKey,Index,String,text
from sqlalchemy.orm import Mapped,mapped_column
from ..config.database import Base
from ..utils.clock import now
_OPEN_RUN_CLAUSE="status IN ('queued','running')"
class ReportRun(Base):
    __tablename__="report_runs"
    __table_args__=(
        # 同一计划至多保留一份未结束（排队/计算中）的运行，重复领取同一期时复用原报表编号
        Index("uq_report_run_open_per_schedule","schedule_id",unique=True,
              postgresql_where=text(_OPEN_RUN_CLAUSE),sqlite_where=text(_OPEN_RUN_CLAUSE)),
        Index("report_runs_status_started_idx","status","started_at"),
    )
    id: Mapped[int]=mapped_column(primary_key=True)
    name: Mapped[str]
    dimensions: Mapped[list]=mapped_column(JSON)
    status: Mapped[str]=mapped_column(default="queued")
    result: Mapped[dict]=mapped_column(JSON,default=dict)
    error: Mapped[str]=mapped_column(default="")
    created_at: Mapped[str]=mapped_column(default=now)
    # 进入 running 的时间（ISO 字符串），配合租约判断进程是否中断
    started_at: Mapped[str|None]=mapped_column(String,nullable=True)
    owner: Mapped[str]
    schedule_id: Mapped[int|None]=mapped_column(ForeignKey("delivery_schedules.id"),nullable=True)
