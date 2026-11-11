from sqlalchemy.orm import Mapped, mapped_column
from ..config.database import Base
class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(unique=True)
    name: Mapped[str]
    role: Mapped[str]
    password_hash: Mapped[str]
