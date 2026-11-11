from sqlalchemy.orm import Mapped,mapped_column
from ..config.database import Base
class SourceRow(Base):
    __tablename__="source_rows"
    id: Mapped[int]=mapped_column(primary_key=True)
    source_key: Mapped[str]=mapped_column(unique=True)
    day: Mapped[str]
    channel: Mapped[str]
    region: Mapped[str]
    revenue: Mapped[float]
    cost: Mapped[float]
    refunds: Mapped[float]
    orders: Mapped[int]
    reference_net: Mapped[float]
