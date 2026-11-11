from sqlalchemy.orm import Mapped,mapped_column
from ..config.database import Base
class Metric(Base):
    __tablename__="metrics"
    id: Mapped[int]=mapped_column(primary_key=True)
    key: Mapped[str]=mapped_column(unique=True)
    name: Mapped[str]
    expression: Mapped[str]
    unit: Mapped[str]
    description: Mapped[str]
    owner: Mapped[str]
