from datetime import datetime as dt
import uuid

from sqlalchemy.orm import mapped_column, Mapped
from sqlalchemy import ForeignKey, DateTime, Boolean, String

from src.exceptions import JSRError
from src.utils import hash_token

from .base import Base


class RefreshToken(Base):
  __tablename__ = 'refresh_tokens'

  id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
  user_uid: Mapped[str] = mapped_column(String(6), ForeignKey('users.uid'), nullable=False)
  token: Mapped[str] = mapped_column(String(64), nullable=False)
  expires_at: Mapped[dt] = mapped_column(DateTime, nullable=False)
  revoked: Mapped[bool] = mapped_column(Boolean, default=False)

  def __init__(self, user_uid, token, expires_at, **kwargs) -> None:
    self.user_uid = user_uid
    self.token = hash_token(token)
    self.expires_at = expires_at

  @property
  def json(self):
    return dict(id=self.id, user_uid=self.user_uid, expires_at=self.expires_at, revoked=self.revoked)

  @classmethod
  async def by_raw(cls, session, refresh_token: str):
    if not refresh_token:
      return None
    return await cls.first(session, token=hash_token(refresh_token))

  @classmethod
  async def exists(cls, session, refresh_token: str) -> bool:
    return bool(await cls.by_raw(session, refresh_token))

  @classmethod
  async def revoke(cls, session, refresh_token, **kwargs):
    if not refresh_token:
      raise JSRError('invalid_payload')
    token = await cls.by_raw(session, refresh_token)
    if not token:
      raise JSRError('unauthorized')
    if not token.revoked:
      token.revoked = True
      await session.commit()
    return dict(revoked=True)
