from datetime import datetime as dt
import uuid

from sqlalchemy import Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Device(Base):
  __tablename__ = 'devices'

  id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
  user_uid: Mapped[str] = mapped_column(String(6), ForeignKey('users.uid'), nullable=False, index=True)
  device_id: Mapped[str] = mapped_column(String(128), nullable=False)
  name: Mapped[str | None] = mapped_column(String(255), nullable=True)
  is_master: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
  revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
  last_seen: Mapped[dt] = mapped_column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

  @property
  def json(self):
    return dict(id=self.device_id, name=self.name, is_master=self.is_master, revoked=self.revoked)
