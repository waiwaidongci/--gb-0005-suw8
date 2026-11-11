from sqlalchemy.orm import Mapped, mapped_column
from ..config.database import Base
from ..utils.clock import now
class Audit(Base):
    __tablename__ = "audits"
    id: Mapped[int] = mapped_column(primary_key=True)
    actor: Mapped[str]
    action: Mapped[str]
    target: Mapped[str]
    created_at: Mapped[str] = mapped_column(default=now)
