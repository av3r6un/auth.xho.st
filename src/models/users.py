from datetime import timedelta as delta
from datetime import timezone
from datetime import datetime as dt
import os

from sqlalchemy.orm import mapped_column, Mapped
from sqlalchemy import func, DateTime, Boolean, String, JSON

from src.exceptions import JSRError
from src.utils import hash_password, decode_token, create_token, hash_token, check_pw

from .base import Base


class User(Base):
  __tablename__ = 'users'

  uid: Mapped[str] = mapped_column(String(6), primary_key=True)
  email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
  password: Mapped[str] = mapped_column(String(255), nullable=False)
  is_active: Mapped[str] = mapped_column(Boolean, default=True)
  is_blocked: Mapped[str] = mapped_column(Boolean, default=False)
  roles: Mapped[dict | list] = mapped_column(JSON, nullable=True, default=list)
  scopes: Mapped[dict | list] = mapped_column(JSON, nullable=True, default=list)
  updated: Mapped[dt] = mapped_column(DateTime, default=func.now(), onupdate=func.now())

  def __init__(self, uid, email: str, password, **kwargs):
    self.uid = uid
    self.email = email.lower()
    self.password = hash_password(password)
    self.scopes = ['auth']
    self.roles = ['user']

  @property
  def json(self):
    active_dict = dict()
    active_dict.update({'is_active': self.is_active} if not self.is_blocked else {'is_blocked': self.is_blocked})
    return dict(uid=self.uid, email=self.email, roles=self.roles, scopes=self.scopes, updated=int(self.updated.timestamp()), **active_dict)

  @property
  def claims(self):
    return dict(roles=self.roles, scopes=self.scopes)

  async def login(self, session, email, password, **kwargs) -> dict:
    if not email or not password:
      raise JSRError('invalid_payload')

    if not check_pw(password, self.password):
      raise JSRError('unauthorized')

    if self.is_blocked or not self.is_active:
      raise JSRError('forbidden')

    tokens = await self._create_tokens(session, self.uid)
    return dict(**tokens, **self.json)

  @classmethod
  async def refresh(cls, session, refresh_token, **kwargs) -> dict:
    from .tokens import RefreshToken

    if not refresh_token:
      raise JSRError('invalid_payload')
    token = await RefreshToken.first(session, token=hash_token(refresh_token))
    if not token:
      raise JSRError('unauthorized')
    if token.revoked:
      raise JSRError('token_revoked')
    if token.expires_at < dt.now(timezone.utc).replace(tzinfo=None):
      raise JSRError('token_expired')
    try:
      payload = decode_token(refresh_token)
    except Exception:
      raise JSRError('token_decode_error')
    if payload.get('sub') != token.user_uid:
      raise JSRError('unauthorized')
    user = await cls.first(session, uid=token.user_uid)
    if not user:
      raise JSRError('unauthorized')
    if user.is_blocked or not user.is_active:
      raise JSRError('forbidden')
    await RefreshToken.revoke(session, refresh_token)
    tokens = await cls._create_tokens(session, user.uid, **user.claims)
    return dict(**tokens, **user.json)

  @staticmethod
  async def _create_tokens(session, user_uid, **claims) -> dict:
    from .tokens import RefreshToken

    access = create_token(user_uid, fresh=True, **claims)
    refresh = create_token(user_uid, fresh=False, **claims)
    refresh_ttl = int(os.getenv('JWT_REFRESH_TOKEN_EXPIRES', 2592000))
    expires_at = dt.now(timezone.utc).replace(tzinfo=None) + delta(seconds=refresh_ttl)
    token = RefreshToken(user_uid, refresh, expires_at)
    await token.save(session)
    return dict(access_token=access, refresh_token=refresh, expires_at=int(expires_at.replace(tzinfo=timezone.utc).timestamp()))
