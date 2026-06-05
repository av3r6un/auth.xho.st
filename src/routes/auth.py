from pathlib import Path
import os

from sqlalchemy.ext.asyncio import AsyncSession
from aiohttp.web import json_response, RouteTableDef, FileResponse, Request
from sqlalchemy import select

from src.exceptions import JSRError
from src.models import RefreshToken, User
from src.utils import generate_jwks, decode_token

auth = RouteTableDef()


async def require_user(req: Request, session: AsyncSession) -> tuple[dict, User]:
  header = req.headers.get('Authorization', '')
  scheme, _, token = header.partition(' ')
  if scheme.lower() != 'bearer' or not token:
    raise JSRError('unauthorized', message='Bearer token required.')

  try:
    payload = decode_token(
        token,
        issuer=os.getenv('AUTHORITY'),
        options={'require': ['exp', 'iat', 'iss', 'sub']},
    )
  except Exception as exc:
    raise JSRError('unauthorized', message=str(exc))

  user = await User.first(session, uid=payload.get('sub'))
  if not user:
    raise JSRError('unauthorized')
  if user.is_blocked or not user.is_active:
    raise JSRError('forbidden')
  return payload, user


@auth.get('/health')
async def health(req: Request, session: AsyncSession):
  await session.execute(select(1))
  return dict(ok=True)


@auth.get('/test')
async def test(req: Request, session: AsyncSession):
  return dict(ok=True)


@auth.post('/')
async def login(req: Request, session: AsyncSession):
  data = (await req.json()).get('data', {})
  try:
    user = await User.first(session, email=data.get('email'))
    if not user:
      raise JSRError('unauthorized')
    body = await user.login(session, **data)
    return body, 'You are successfully logged in.'
  except JSRError:
    raise
  except Exception as e:
    return json_response(**JSRError('internal', message=str(e)).json)


@auth.post('/register')
async def register(req: Request, session: AsyncSession):
  data = (await req.json()).get('data', {})
  try:
    already_exists = await User.first(session, email=data.get('email'))
    if already_exists:
      return json_response(**JSRError('conflict', message='Account already registered!', status=409).json)
    uid = await User.create_uid(session)
    user = User(uid, **data)
    await user.save(session)
    return True, 'Your account successfully created!'
  except Exception as e:
    return json_response(**JSRError('bad_request', message=str(e)).json)


@auth.post('/refresh')
async def refresh(req: Request, session: AsyncSession):
  data = (await req.json()).get('data', {})
  try:
    body = await User.refresh(session, **data)
    return body, 'Tokens successfully refreshed.'
  except JSRError:
    raise
  except Exception as e:
    return json_response(**JSRError('internal', message=str(e)).json)


@auth.post('/revoke')
async def revoke(req: Request, session: AsyncSession):
  data = (await req.json()).get('data', {})
  try:
    body = await RefreshToken.revoke(session, **data)
    return body, 'Token revoked.'
  except JSRError:
    raise
  except Exception as e:
    return json_response(**JSRError('internal', message=str(e)).json)


@auth.get('/.well-known/jwks.json')
async def jwks(req: Request, session: AsyncSession):
  path = Path(os.getenv('JWKS_PATH')).resolve()
  if not os.path.exists(path):
    jwks = generate_jwks()
    return json_response(jwks)
  return FileResponse(path, headers={'Cache-Control': 'public, max-age=3600'})


@auth.get('/me')
async def me(req: Request, session: AsyncSession):
  payload, user = await require_user(req, session)
  return dict(user=user.json, claims=payload)
