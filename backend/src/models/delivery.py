from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped,mapped_column
from ..config.database import Base
from ..utils.clock import now
class Delivery(Base):
    __tablename__="deliveries"
    id: Mapped[int]=mapped_column(primary_key=True)
    schedule_id: Mapped[int]=mapped_column(ForeignKey("delivery_schedules.id"))
    run_id: Mapped[int]=mapped_column(ForeignKey("report_runs.id"),unique=True)
    title: Mapped[str]
    created_at: Mapped[str]=mapped_column(default=now)
