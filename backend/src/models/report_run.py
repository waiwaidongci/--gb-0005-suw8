from sqlalchemy import JSON,ForeignKey
from sqlalchemy.orm import Mapped,mapped_column
from ..config.database import Base
from ..utils.clock import now
class ReportRun(Base):
    __tablename__="report_runs"
    id: Mapped[int]=mapped_column(primary_key=True)
    name: Mapped[str]
    dimensions: Mapped[list]=mapped_column(JSON)
    status: Mapped[str]=mapped_column(default="queued")
    result: Mapped[dict]=mapped_column(JSON,default=dict)
    error: Mapped[str]=mapped_column(default="")
    created_at: Mapped[str]=mapped_column(default=now)
    owner: Mapped[str]
    schedule_id: Mapped[int|None]=mapped_column(ForeignKey("delivery_schedules.id"),nullable=True)
