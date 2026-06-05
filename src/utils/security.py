import hashlib
import hmac

import bcrypt


def hash_password(password: str) -> str:
  return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def check_pw(password: str, hash: str) -> bool:
  return bcrypt.checkpw(password.encode(), hash.encode())


def hash_token(token: str) -> str:
  return hashlib.sha256(token.encode()).hexdigest()


def check_token(token: str, token_hash: str) -> bool:
  return hmac.compare_digest(hash_token(token), token_hash)
