from datetime import timedelta as delta
from datetime import datetime as dt
from pathlib import Path
import base64
import json
import os

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
import pytz
import jwt

ALG = 'RS256'


def _load_key(value: str | None):
  if not value:
    return None
  path = Path(value)
  if path.exists():
    return path.read_text(encoding='utf-8')
  return value


def _get_private_key():
  key = _load_key(os.getenv('JWT_PRIVATE_KEY'))
  if not key:
    raise RuntimeError('JWT_PRIVATE_KEY variable not found!')
  return key


def _get_public_key():
  key = _load_key(os.getenv('JWT_PUBLIC_KEY'))
  if not key:
    raise RuntimeError('JWT_PUBLIC_KEY variable not found!')
  return key


def _create_token(user_uid: str, expired_delta: delta = delta(hours=1), **claims):
  payload = dict(
      sub=user_uid,
      exp=dt.now(tz=pytz.timezone('UTC')) + expired_delta,
      iat=dt.now(tz=pytz.timezone('UTC')),
      iss=os.getenv('AUTHORITY'),
      **claims,
  )
  return jwt.encode(payload, _get_private_key(), algorithm=ALG, headers=dict(kid=os.getenv('KID')))


def decode_token(token: str, **kwargs):
  return jwt.decode(token, _get_public_key(), algorithms=[ALG], **kwargs)


def create_token(user_uid: str, fresh: bool = True, **claims):
  access_ttl = int(os.getenv('JWT_ACCESS_TOKEN_EXPIRES', 86400))
  refresh_ttl = int(os.getenv('JWT_REFRESH_TOKEN_EXPIRES', 2592000))
  ttl = access_ttl if fresh else refresh_ttl
  return _create_token(user_uid, delta(seconds=ttl), **claims)


def _b64url_uint(val: int) -> str:
  b = val.to_bytes((val.bit_length() + 7) // 8, "big")
  return base64.urlsafe_b64encode(b).rstrip(b"=").decode("ascii")


def generate_jwks() -> dict:
  with open(os.getenv('JWT_PUBLIC_KEY'), 'rb') as f:
    pub = serialization.load_pem_public_key(f.read(), backend=default_backend())

  nums = pub.public_numbers()
  n = _b64url_uint(nums.n)
  e = _b64url_uint(nums.e)

  jwks = {
      'keys': [
          {
              'kty': 'RSA',
              'use': 'sig',
              'alg': 'RS256',
              'kid': os.getenv("KID"),
              'n': n,
              'e': e,
          },
      ]
  }
  with open(os.getenv('JWKS_PATH'), 'w', encoding='utf-8') as f:
    json.dump(jwks, f, indent=2, ensure_ascii=False)

  return jwks
