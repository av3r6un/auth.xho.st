import inspect

from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
from aiohttp.web_exceptions import HTTPNotFound
from aiohttp.web import json_response, middleware, StreamResponse, HTTPException, Request

from src.exceptions import JSRError


@middleware
async def db_middleware(req: Request, handler, *args, **kwargs):
  session_factory: async_sessionmaker[AsyncSession] = req.app['db_sessionmaker']
  async with session_factory() as session:
    try:
      req['session'] = session
      response = await handler(req, *args, **kwargs)
      if getattr(response, 'status', 200) >= 400:
        await session.rollback()
      else:
        await session.commit()
      return response
    except JSRError as jsr:
      await session.rollback()
      return json_response(**jsr.json)
    except HTTPNotFound:
      await session.rollback()
      return json_response(**JSRError('not_found').json)
    except Exception as e:
      await session.rollback()
      return json_response(**JSRError('internal', message=str(e)).json)


@middleware
async def jsr_middleware(req: Request, handler, *args, **kwargs):
  try:
    call_kwargs = {}
    try:
      sig = inspect.signature(handler)
      params = sig.parameters
      if 'session' in params or any(p.kind == p.VAR_KEYWORD for p in params.values()):
        call_kwargs['session'] = req.get('session')
    except (TypeError, ValueError):
      pass

    result = await handler(req, *args, **call_kwargs, **kwargs)
    if isinstance(result, StreamResponse):
      return result
    if isinstance(result, tuple):
      body, message = result
      return json_response(dict(status='success', body=body, message=message))
    return json_response(dict(status='success', body=result))
  except JSRError as e:
    return json_response(**e.json)
  except HTTPException:
    raise
  except Exception as e:
    return json_response(dict(status='error', message=str(e)), status=500)


middlewares = [db_middleware, jsr_middleware]
