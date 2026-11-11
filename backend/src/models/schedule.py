from sqlalchemy import JSON
from sqlalchemy.orm import Mapped,mapped_column
from ..config.database import Base
class DeliverySchedule(Base):
    __tablename__="delivery_schedules"
    id: Mapped[int]=mapped_column(primary_key=True)
    name: Mapped[str]=mapped_column(unique=True)
    dimensions: Mapped[list]=mapped_column(JSON)
    interval_minutes: Mapped[int]
    next_run_at: Mapped[str]
    active: Mapped[bool]=mapped_column(default=True)
    owner: Mapped[str]
